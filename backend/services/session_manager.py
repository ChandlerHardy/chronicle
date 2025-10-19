"""Interactive session recording and management."""

import os
import sys
import subprocess
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from sqlalchemy.orm import Session

from backend.database.models import AIInteraction


class SessionManager:
    """Manage interactive CLI sessions with recording."""

    def __init__(self, db_session: Session):
        """Initialize session manager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.session_dir = Path.home() / ".ai-session" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, tool: str, tool_command: Optional[str] = None) -> int:
        """Start an interactive session with a CLI tool.

        Args:
            tool: Name of the tool ('claude', 'vim', etc.)
            tool_command: Optional custom command to run (defaults to tool name)

        Returns:
            Session ID (AIInteraction.id)
        """
        if tool_command is None:
            tool_command = tool

        # Create session record immediately
        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool=f"{tool}-session",
            prompt=f"Interactive {tool} session started",
            response_summary=None,
            is_session=1,
            summary_generated=0,
            session_transcript=None,
        )
        self.db.add(session)
        self.db.commit()

        session_id = session.id

        # Create transcript file
        transcript_file = self.session_dir / f"session_{session_id}.log"

        # Save session metadata
        metadata = {
            "session_id": session_id,
            "tool": tool,
            "command": tool_command,
            "transcript_file": str(transcript_file),
            "start_time": datetime.now().isoformat(),
        }
        self._save_metadata(session_id, metadata)

        print(f"🎯 Chronicle session #{session_id} started - tracking all activity")
        print(f"Launching {tool}...")
        print()

        # Launch the tool with script to capture output
        # Using -q for quiet (no start/stop messages)
        # Using -F for flush output immediately
        try:
            # Run the tool inside script to capture all I/O
            result = subprocess.run(
                ["script", "-q", "-F", str(transcript_file), tool_command],
                shell=False,
            )
            exit_code = result.returncode
        except KeyboardInterrupt:
            exit_code = 130  # Standard SIGINT exit code
        except Exception as e:
            print(f"\n❌ Error running {tool}: {e}")
            exit_code = 1

        # Session ended, update the record
        self._finalize_session(session_id, transcript_file, exit_code)

        return session_id

    def _finalize_session(self, session_id: int, transcript_file: Path, exit_code: int):
        """Finalize a session after the tool exits.

        Args:
            session_id: Session ID
            transcript_file: Path to transcript file
            exit_code: Exit code from the tool
        """
        # Load metadata
        metadata = self._load_metadata(session_id)
        start_time = datetime.fromisoformat(metadata["start_time"])
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Read transcript
        transcript = self._read_transcript(transcript_file)

        # Clean up ANSI codes for storage
        clean_transcript = self._clean_ansi(transcript)

        # Update session record
        session = self.db.query(AIInteraction).filter_by(id=session_id).first()
        if session:
            session.duration_ms = duration_ms
            session.session_transcript = clean_transcript
            # Prompt is the first line or "Session"
            session.prompt = f"Interactive session ({duration_ms / 1000 / 60:.1f}m)"
            self.db.commit()

        print()
        print(f"📊 Session #{session_id} complete! Duration: {duration_ms / 1000 / 60:.1f} minutes")
        print(f"💾 Full transcript saved ({len(clean_transcript)} chars)")
        print(f"✨ Use 'chronicle ai today' to view (summary generated on first view)")

    def _read_transcript(self, transcript_file: Path) -> str:
        """Read transcript file.

        Args:
            transcript_file: Path to transcript file

        Returns:
            Transcript content
        """
        if not transcript_file.exists():
            return ""

        try:
            with open(transcript_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read transcript: {e}")
            return ""

    def _clean_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text.

        Args:
            text: Text with ANSI codes

        Returns:
            Clean text
        """
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _save_metadata(self, session_id: int, metadata: Dict):
        """Save session metadata to file.

        Args:
            session_id: Session ID
            metadata: Metadata dictionary
        """
        import json

        metadata_file = self.session_dir / f"session_{session_id}.meta"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, session_id: int) -> Dict:
        """Load session metadata from file.

        Args:
            session_id: Session ID

        Returns:
            Metadata dictionary
        """
        import json

        metadata_file = self.session_dir / f"session_{session_id}.meta"
        if not metadata_file.exists():
            return {}

        with open(metadata_file, "r") as f:
            return json.load(f)

    def get_active_sessions(self) -> list:
        """Get list of active sessions.

        Returns:
            List of active session metadata
        """
        # Check for session files that exist but have no end time in DB
        sessions = (
            self.db.query(AIInteraction)
            .filter_by(is_session=1)
            .filter(AIInteraction.session_transcript == None)  # noqa: E711
            .all()
        )
        return sessions

    def get_session_transcript(self, session_id: int) -> Optional[str]:
        """Get full transcript for a session.

        Args:
            session_id: Session ID

        Returns:
            Transcript text or None
        """
        session = self.db.query(AIInteraction).filter_by(id=session_id).first()
        if session and session.is_session:
            return session.session_transcript
        return None

    def needs_summary(self, session_id: int) -> bool:
        """Check if session needs summarization.

        Args:
            session_id: Session ID

        Returns:
            True if needs summary
        """
        session = self.db.query(AIInteraction).filter_by(id=session_id).first()
        if not session or not session.is_session:
            return False

        return session.summary_generated == 0 and session.session_transcript is not None
