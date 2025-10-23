"""Chronicle MCP Server - Provides AI tools access to Chronicle database.

This server implements the Model Context Protocol (MCP) to allow AI assistants
to query Chronicle's database of development sessions, commits, and summaries.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastmcp import FastMCP
from sqlalchemy import desc, or_, and_
from sqlalchemy.orm import Session

from backend.database.models import (
    init_db,
    AIInteraction,
    Commit,
    DailySummary,
    SessionSummaryChunk,
)

# Initialize FastMCP server
mcp = FastMCP(name="chronicle")

# Database session (will be initialized on first use)
_db_session: Optional[Session] = None


def get_db() -> Session:
    """Get or create database session."""
    global _db_session
    if _db_session is None:
        _, SessionLocal = init_db()
        _db_session = SessionLocal()
    return _db_session


def format_session_dict(session: AIInteraction) -> Dict[str, Any]:
    """Convert AIInteraction to a clean dictionary for MCP responses."""
    return {
        "id": session.id,
        "tool": session.ai_tool,
        "timestamp": session.timestamp.isoformat(),
        "is_session": bool(session.is_session),
        "duration_minutes": round(session.duration_ms / 60000, 1) if session.duration_ms else None,
        "prompt": session.prompt,
        "summary": session.response_summary,
        "summary_generated": bool(session.summary_generated),
        "repo_path": session.repo_path,
        "working_directory": session.working_directory,
        "files_mentioned": session.files_list,
        "related_commit_id": session.related_commit_id,
    }


def format_commit_dict(commit: Commit) -> Dict[str, Any]:
    """Convert Commit to a clean dictionary for MCP responses."""
    return {
        "id": commit.id,
        "sha": commit.sha,
        "timestamp": commit.timestamp.isoformat(),
        "message": commit.message,
        "author": commit.author,
        "branch": commit.branch,
        "repo_path": commit.repo_path,
        "files_changed": commit.files_list,
    }


@mcp.tool()
def get_sessions(
    limit: int = 10,
    tool: Optional[str] = None,
    repo_path: Optional[str] = None,
    days: Optional[int] = None,
) -> str:
    """Get recent Chronicle sessions.

    Args:
        limit: Maximum number of sessions to return (default: 10, max: 100)
        tool: Filter by AI tool (claude-code, gemini-cli, qwen-cli)
        repo_path: Filter by repository path
        days: Only show sessions from last N days

    Returns:
        JSON string with list of sessions
    """
    db = get_db()
    query = db.query(AIInteraction).filter(AIInteraction.is_session == 1)

    if tool:
        query = query.filter(AIInteraction.ai_tool == tool)

    if repo_path:
        query = query.filter(AIInteraction.repo_path.like(f"%{repo_path}%"))

    if days:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(AIInteraction.timestamp >= cutoff)

    limit = min(limit, 100)  # Cap at 100
    sessions = query.order_by(desc(AIInteraction.timestamp)).limit(limit).all()

    result = {
        "count": len(sessions),
        "sessions": [format_session_dict(s) for s in sessions]
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_session_summary(session_id: int) -> str:
    """Get detailed summary of a specific Chronicle session.

    Args:
        session_id: The session ID to retrieve

    Returns:
        JSON string with session details and full summary
    """
    db = get_db()
    session = db.query(AIInteraction).filter(AIInteraction.id == session_id).first()

    if not session:
        return json.dumps({"error": f"Session {session_id} not found"})

    result = format_session_dict(session)

    # Add transcript path if available
    if session.session_transcript:
        home = os.path.expanduser("~")
        transcript_path = os.path.join(home, ".ai-session", "sessions", session.session_transcript)
        result["transcript_path"] = transcript_path
        result["transcript_exists"] = os.path.exists(transcript_path)

    # Add chunked summaries if available
    chunks = db.query(SessionSummaryChunk).filter(
        SessionSummaryChunk.session_id == session_id
    ).order_by(SessionSummaryChunk.chunk_number).all()

    if chunks:
        result["chunked_summaries"] = [
            {
                "chunk_number": c.chunk_number,
                "lines": f"{c.chunk_start_line}-{c.chunk_end_line}",
                "summary": c.chunk_summary,
            }
            for c in chunks
        ]

    return json.dumps(result, indent=2)


@mcp.tool()
def search_sessions(
    query: str,
    limit: int = 10,
    search_summaries: bool = True,
    search_prompts: bool = True,
) -> str:
    """Search Chronicle sessions by keywords.

    Args:
        query: Search query (searches summaries and prompts)
        limit: Maximum number of results (default: 10, max: 50)
        search_summaries: Search in AI-generated summaries (default: True)
        search_prompts: Search in session prompts/descriptions (default: True)

    Returns:
        JSON string with matching sessions
    """
    db = get_db()

    filters = []
    if search_summaries:
        filters.append(AIInteraction.response_summary.like(f"%{query}%"))
    if search_prompts:
        filters.append(AIInteraction.prompt.like(f"%{query}%"))

    if not filters:
        return json.dumps({"error": "Must search summaries or prompts"})

    limit = min(limit, 50)
    sessions = db.query(AIInteraction).filter(
        and_(
            AIInteraction.is_session == 1,
            or_(*filters)
        )
    ).order_by(desc(AIInteraction.timestamp)).limit(limit).all()

    result = {
        "query": query,
        "count": len(sessions),
        "sessions": [format_session_dict(s) for s in sessions]
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_commits(
    limit: int = 20,
    repo_path: Optional[str] = None,
    author: Optional[str] = None,
    days: Optional[int] = None,
) -> str:
    """Get recent git commits tracked by Chronicle.

    Args:
        limit: Maximum number of commits (default: 20, max: 100)
        repo_path: Filter by repository path
        author: Filter by commit author
        days: Only show commits from last N days

    Returns:
        JSON string with list of commits
    """
    db = get_db()
    query = db.query(Commit)

    if repo_path:
        query = query.filter(Commit.repo_path.like(f"%{repo_path}%"))

    if author:
        query = query.filter(Commit.author.like(f"%{author}%"))

    if days:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(Commit.timestamp >= cutoff)

    limit = min(limit, 100)
    commits = query.order_by(desc(Commit.timestamp)).limit(limit).all()

    result = {
        "count": len(commits),
        "commits": [format_commit_dict(c) for c in commits]
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_timeline(
    days: int = 1,
    repo_path: Optional[str] = None,
) -> str:
    """Get combined timeline of commits and sessions.

    Args:
        days: Number of days to show (default: 1 = today)
        repo_path: Filter by repository path

    Returns:
        JSON string with timeline of commits and sessions
    """
    db = get_db()
    cutoff = datetime.now() - timedelta(days=days)

    # Get commits
    commit_query = db.query(Commit).filter(Commit.timestamp >= cutoff)
    if repo_path:
        commit_query = commit_query.filter(Commit.repo_path.like(f"%{repo_path}%"))
    commits = commit_query.order_by(desc(Commit.timestamp)).all()

    # Get sessions
    session_query = db.query(AIInteraction).filter(
        and_(
            AIInteraction.is_session == 1,
            AIInteraction.timestamp >= cutoff
        )
    )
    if repo_path:
        session_query = session_query.filter(AIInteraction.repo_path.like(f"%{repo_path}%"))
    sessions = session_query.order_by(desc(AIInteraction.timestamp)).all()

    # Combine and sort by timestamp
    timeline = []

    for commit in commits:
        timeline.append({
            "type": "commit",
            "timestamp": commit.timestamp.isoformat(),
            "data": format_commit_dict(commit)
        })

    for session in sessions:
        timeline.append({
            "type": "session",
            "timestamp": session.timestamp.isoformat(),
            "data": format_session_dict(session)
        })

    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    result = {
        "days": days,
        "repo_path": repo_path,
        "total_items": len(timeline),
        "commits_count": len(commits),
        "sessions_count": len(sessions),
        "timeline": timeline
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_stats(days: int = 7) -> str:
    """Get Chronicle usage statistics.

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        JSON string with usage statistics
    """
    db = get_db()
    cutoff = datetime.now() - timedelta(days=days)

    # Session stats
    sessions = db.query(AIInteraction).filter(
        and_(
            AIInteraction.is_session == 1,
            AIInteraction.timestamp >= cutoff
        )
    ).all()

    # Commit stats
    commits = db.query(Commit).filter(Commit.timestamp >= cutoff).all()

    # Calculate stats
    total_sessions = len(sessions)
    total_duration_minutes = sum(
        (s.duration_ms or 0) / 60000 for s in sessions
    )

    sessions_by_tool = {}
    for session in sessions:
        tool = session.ai_tool
        sessions_by_tool[tool] = sessions_by_tool.get(tool, 0) + 1

    repos = set()
    for session in sessions:
        if session.repo_path:
            repos.add(session.repo_path)
    for commit in commits:
        if commit.repo_path:
            repos.add(commit.repo_path)

    result = {
        "period_days": days,
        "total_sessions": total_sessions,
        "total_commits": len(commits),
        "total_duration_minutes": round(total_duration_minutes, 1),
        "sessions_by_tool": sessions_by_tool,
        "unique_repositories": len(repos),
        "repositories": list(repos),
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def search_commits(query: str, limit: int = 20) -> str:
    """Search git commits by commit message.

    Args:
        query: Search query (searches commit messages)
        limit: Maximum number of results (default: 20, max: 100)

    Returns:
        JSON string with matching commits
    """
    db = get_db()

    limit = min(limit, 100)
    commits = db.query(Commit).filter(
        Commit.message.like(f"%{query}%")
    ).order_by(desc(Commit.timestamp)).limit(limit).all()

    result = {
        "query": query,
        "count": len(commits),
        "commits": [format_commit_dict(c) for c in commits]
    }

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
