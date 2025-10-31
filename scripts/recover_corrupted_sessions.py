#!/usr/bin/env python3
"""
Chronicle Data Recovery Script

This script helps recover from the data corruption bug where sessions have
incorrect summaries that don't match their transcript content.

The corruption occurred due to race conditions in the remote summarization
workflow, causing multiple sessions to receive the same summary while their
transcript files contain completely different content.

Usage:
    python recover_corrupted_sessions.py [--dry-run] [--sessions 2,4,5,7]

Options:
    --dry-run: Show what would be done without making changes
    --sessions: Comma-separated list of session IDs to check
    --all: Check all sessions in the database
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
DB_PATH = Path.home() / ".ai-session" / "sessions.db"
SESSIONS_DIR = Path.home() / ".ai-session" / "sessions"


def get_db_connection():
    """Get database connection."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def load_keywords_from_file(session_id: int) -> List[str]:
    """Load keywords from the keywords file if it exists."""
    keywords_file = SESSIONS_DIR / f"session_{session_id}.keywords"
    if keywords_file.exists():
        try:
            with open(keywords_file, 'r') as f:
                keywords_data = json.load(f)
                if isinstance(keywords_data, list):
                    return keywords_data
        except (json.JSONDecodeError, IOError):
            pass
    return []


def get_transcript_content(session_id: int) -> Optional[str]:
    """Get transcript content from various sources."""
    # Try cleaned file first (v6+)
    cleaned_path = SESSIONS_DIR / f"session_{session_id}.cleaned"
    if cleaned_path.exists():
        with open(cleaned_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # Fallback to log file
    log_path = SESSIONS_DIR / f"session_{session_id}.log"
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # Fallback to database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_transcript FROM ai_interactions WHERE id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    finally:
        conn.close()


def analyze_session_mismatch(session_id: int) -> Dict:
    """Analyze a session for potential data corruption."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ai_tool, prompt, response_summary, summary_generated,
                   timestamp, duration_ms, is_session
            FROM ai_interactions
            WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        if not row:
            return {"error": f"Session {session_id} not found"}

        db_summary = row[3] or ""
        db_prompt = row[2] or ""
        is_session = row[6]

        # Get transcript content
        transcript = get_transcript_content(session_id)

        # Load keywords from file
        keywords = load_keywords_from_file(session_id)

        # Analyze mismatch
        issues = []

        if not transcript:
            issues.append("No transcript found")
        elif is_session and len(transcript) < 100:
            issues.append("Very short transcript for session")

        if db_summary and len(db_summary) > 50:
            # Check if summary content matches transcript
            summary_lower = db_summary.lower()
            transcript_lower = transcript.lower() if transcript else ""

            # Look for keywords from summary in transcript
            summary_words = set(summary_lower.split())
            transcript_words = set(transcript_lower.split())

            # Calculate overlap
            common_words = summary_words.intersection(transcript_words)
            overlap_ratio = len(common_words) / len(summary_words) if summary_words else 0

            if overlap_ratio < 0.3:  # Less than 30% word overlap
                issues.append(f"Low word overlap ({overlap_ratio:.1%}) - summary may not match transcript")

        return {
            "session_id": session_id,
            "ai_tool": row[1],
            "prompt": db_prompt[:100] + "..." if len(db_prompt) > 100 else db_prompt,
            "summary": db_summary[:200] + "..." if len(db_summary) > 200 else db_summary,
            "summary_length": len(db_summary),
            "transcript_length": len(transcript) if transcript else 0,
            "transcript_preview": transcript[:200] + "..." if transcript and len(transcript) > 200 else (transcript or ""),
            "has_transcript": bool(transcript),
            "is_session": bool(is_session),
            "keywords": keywords,
            "issues": issues,
            "timestamp": row[5],
            "duration_ms": row[7]
        }
    finally:
        conn.close()


def find_duplicate_summaries() -> List[Tuple[int, List[int]]]:
    """Find sessions that have identical or nearly identical summaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, response_summary
            FROM ai_interactions
            WHERE response_summary IS NOT NULL AND length(response_summary) > 100
            ORDER BY id
        """)

        summaries = {}
        duplicates = []

        for session_id, summary in cursor.fetchall():
            summary_key = summary[:100]  # First 100 chars as key
            if summary_key in summaries:
                summaries[summary_key].append(session_id)
            else:
                summaries[summary_key] = [session_id]

        # Find groups with multiple sessions
        for sessions in summaries.values():
            if len(sessions) > 1:
                duplicates.append((sessions[0], sessions))

        return duplicates
    finally:
        conn.close()


def fix_session_summary(session_id: int, dry_run: bool = False) -> bool:
    """Attempt to fix a corrupted session by regenerating its summary."""
    try:
        from backend.services.summarizer import Summarizer
        from backend.database.models import get_session
        from datetime import datetime

        # Get transcript content
        transcript = get_transcript_content(session_id)
        if not transcript:
            print(f"❌ Session {session_id}: No transcript content to summarize")
            return False

        if dry_run:
            print(f"🔧 Would fix session {session_id} (transcript: {len(transcript)} chars)")
            return True

        # Create database session
        db_session = get_session()
        try:
            # Generate new summary
            summarizer = Summarizer()
            new_summary = summarizer.summarize_session(transcript)

            # Update database
            cursor = db_session.execute("""
                UPDATE ai_interactions
                SET response_summary = ?, summary_generated = TRUE
                WHERE id = ?
            """, (new_summary, session_id))

            db_session.commit()
            print(f"✅ Session {session_id}: Generated new summary ({len(new_summary)} chars)")
            return True
        finally:
            db_session.close()

    except ImportError as e:
        print(f"❌ Cannot fix session {session_id}: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to fix session {session_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Recover corrupted Chronicle sessions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--sessions", help="Comma-separated list of session IDs to check")
    parser.add_argument("--all", action="store_true", help="Check all sessions")
    parser.add_argument("--find-duplicates", action="store_true", help="Find sessions with duplicate summaries")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix corrupted sessions")

    args = parser.parse_args()

    if args.find_duplicates:
        print("🔍 Finding duplicate summaries...")
        duplicates = find_duplicate_summaries()
        if duplicates:
            print(f"Found {len(duplicates)} groups of duplicate summaries:")
            for main_id, session_ids in duplicates:
                print(f"  Sessions {session_ids} share similar summaries")
        else:
            print("✅ No duplicate summaries found")
        return

    # Determine which sessions to check
    session_ids = []
    if args.sessions:
        session_ids = [int(x.strip()) for x in args.sessions.split(",")]
    elif args.all:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM ai_interactions WHERE is_session = 1 ORDER BY id")
            session_ids = [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    else:
        # Default to known problematic sessions
        session_ids = [2, 4, 5, 7]

    print(f"🔍 Analyzing {len(session_ids)} sessions for corruption...")

    corrupted_sessions = []
    for session_id in session_ids:
        analysis = analyze_session_mismatch(session_id)

        print(f"\n📋 Session {session_id} ({analysis['ai_tool']}):")
        print(f"   Summary: {analysis['summary_length']} chars")
        print(f"   Transcript: {analysis['transcript_length']} chars")
        print(f"   Issues: {len(analysis['issues'])}")

        for issue in analysis['issues']:
            print(f"   ⚠️  {issue}")

        if analysis['issues']:
            corrupted_sessions.append(session_id)

        # Show preview if there are issues
        if analysis['issues'] and analysis['transcript_preview']:
            print(f"   Transcript preview: {analysis['transcript_preview'][:150]}...")

    print(f"\n📊 Summary:")
    print(f"   Total checked: {len(session_ids)}")
    print(f"   Corrupted: {len(corrupted_sessions)}")

    if corrupted_sessions:
        print(f"   Corrupted sessions: {corrupted_sessions}")

        if args.fix:
            print(f"\n🔧 Attempting to fix {len(corrupted_sessions)} corrupted sessions...")
            success_count = 0
            for session_id in corrupted_sessions:
                if fix_session_summary(session_id, dry_run=args.dry_run):
                    success_count += 1

            if not args.dry_run:
                print(f"✅ Fixed {success_count}/{len(corrupted_sessions)} sessions")
            else:
                print(f"🔧 Would fix {success_count}/{len(corrupted_sessions)} sessions")


if __name__ == "__main__":
    main()