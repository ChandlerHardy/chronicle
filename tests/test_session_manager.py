"""Tests for session_manager.py"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, AIInteraction
from backend.services.session_manager import SessionManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session, db_path

    session.close()
    os.unlink(db_path)


@pytest.fixture
def session_manager(temp_db, tmp_path):
    """Create SessionManager with temp database and directory."""
    db_session, db_path = temp_db
    manager = SessionManager(db_session)

    # Override session_dir to use temp directory
    manager.session_dir = tmp_path / "sessions"
    manager.session_dir.mkdir(parents=True, exist_ok=True)

    return manager


class TestSessionManager:
    """Test SessionManager class."""

    def test_init_creates_session_directory(self, temp_db, tmp_path):
        """SessionManager creates session directory on init."""
        db_session, _ = temp_db

        # Override Path.home() to use temp directory
        with patch('backend.services.session_manager.Path.home', return_value=tmp_path):
            manager = SessionManager(db_session)

            assert manager.session_dir.exists()
            assert manager.session_dir.is_dir()
            assert manager.session_dir == tmp_path / ".ai-session" / "sessions"

    def test_save_and_load_metadata(self, session_manager):
        """Metadata can be saved and loaded."""
        metadata = {
            "session_id": 42,
            "tool": "claude",
            "command": "claude",
            "start_time": "2025-10-28T10:00:00"
        }

        session_manager._save_metadata(42, metadata)
        loaded = session_manager._load_metadata(42)

        assert loaded == metadata

    def test_load_metadata_nonexistent_file_returns_empty_dict(self, session_manager):
        """Loading metadata for nonexistent session returns empty dict."""
        result = session_manager._load_metadata(999)
        assert result == {}

    def test_read_transcript_success(self, session_manager, tmp_path):
        """Reading transcript from existing file succeeds."""
        transcript_file = tmp_path / "test_transcript.log"
        transcript_file.write_text("User: Hello\nAssistant: Hi!")

        result = session_manager._read_transcript(transcript_file)

        assert result == "User: Hello\nAssistant: Hi!"

    def test_read_transcript_nonexistent_file_returns_empty_string(self, session_manager, tmp_path):
        """Reading nonexistent transcript file returns empty string."""
        result = session_manager._read_transcript(tmp_path / "nonexistent.log")
        assert result == ""

    def test_read_transcript_handles_encoding_errors(self, session_manager, tmp_path):
        """Reading transcript with encoding errors succeeds with errors='ignore'."""
        transcript_file = tmp_path / "bad_encoding.log"
        # Write binary data that's not valid UTF-8
        transcript_file.write_bytes(b"Valid text \xff\xfe Invalid bytes \x00")

        result = session_manager._read_transcript(transcript_file)

        # Should read successfully, ignoring invalid bytes
        assert "Valid text" in result

    def test_find_git_root_in_git_repo(self, session_manager, tmp_path):
        """_find_git_root returns repo root when in git repository."""
        # Create fake git repo structure
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        subdir = repo_root / "src" / "components"
        subdir.mkdir(parents=True)

        result = session_manager._find_git_root(str(subdir))

        assert result == str(repo_root)

    def test_find_git_root_not_in_git_repo_returns_none(self, session_manager, tmp_path):
        """_find_git_root returns None when not in git repository."""
        result = session_manager._find_git_root(str(tmp_path))
        assert result is None

    def test_get_active_sessions_returns_sessions_without_duration(self, session_manager, temp_db):
        """get_active_sessions returns sessions that are still in progress."""
        db_session, _ = temp_db

        # Create active session (no duration)
        active = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Active session",
            is_session=True,
            session_transcript=None,
            duration_ms=None
        )
        db_session.add(active)

        # Create completed session
        completed = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Completed session",
            is_session=True,
            session_transcript="Done",
            duration_ms=60000
        )
        db_session.add(completed)
        db_session.commit()

        active_sessions = session_manager.get_active_sessions()

        # Should only return the active session
        assert len(active_sessions) == 1
        assert active_sessions[0].id == active.id

    def test_get_session_transcript_for_session(self, session_manager, temp_db):
        """get_session_transcript returns transcript for valid session."""
        db_session, _ = temp_db

        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test",
            is_session=True,
            session_transcript="Transcript content"
        )
        db_session.add(session)
        db_session.commit()

        result = session_manager.get_session_transcript(session.id)

        assert result == "Transcript content"

    def test_get_session_transcript_for_nonexistent_session_returns_none(self, session_manager):
        """get_session_transcript returns None for nonexistent session."""
        result = session_manager.get_session_transcript(999)
        assert result is None

    def test_get_session_transcript_for_non_session_returns_none(self, session_manager, temp_db):
        """get_session_transcript returns None for non-session interaction."""
        db_session, _ = temp_db

        # Create non-session interaction
        interaction = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude",
            prompt="Quick question",
            is_session=False
        )
        db_session.add(interaction)
        db_session.commit()

        result = session_manager.get_session_transcript(interaction.id)

        assert result is None

    def test_needs_summary_returns_true_for_unsummarized_session(self, session_manager, temp_db):
        """needs_summary returns True for session without summary."""
        db_session, _ = temp_db

        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test",
            is_session=True,
            session_transcript="Content",
            summary_generated=False
        )
        db_session.add(session)
        db_session.commit()

        result = session_manager.needs_summary(session.id)

        assert result is True

    def test_needs_summary_returns_false_for_summarized_session(self, session_manager, temp_db):
        """needs_summary returns False for already-summarized session."""
        db_session, _ = temp_db

        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test",
            is_session=True,
            session_transcript="Content",
            summary_generated=True
        )
        db_session.add(session)
        db_session.commit()

        result = session_manager.needs_summary(session.id)

        assert result is False

    def test_needs_summary_returns_false_for_session_without_transcript(self, session_manager, temp_db):
        """needs_summary returns False for session with no transcript."""
        db_session, _ = temp_db

        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test",
            is_session=True,
            session_transcript=None,
            summary_generated=False
        )
        db_session.add(session)
        db_session.commit()

        result = session_manager.needs_summary(session.id)

        assert result is False

    def test_needs_summary_returns_false_for_nonexistent_session(self, session_manager):
        """needs_summary returns False for nonexistent session."""
        result = session_manager.needs_summary(999)
        assert result is False

    @patch('backend.services.session_manager.subprocess.run')
    @patch('backend.services.session_manager.print_chronicle_banner')
    def test_start_session_creates_database_record(self, mock_banner, mock_subprocess, session_manager, temp_db):
        """start_session creates AIInteraction record in database."""
        db_session, _ = temp_db

        # Mock subprocess to return immediately
        mock_subprocess.return_value = Mock(returncode=0)

        # Mock _finalize_session to prevent background process spawn
        with patch.object(session_manager, '_finalize_session'):
            session_id = session_manager.start_session('claude')

        # Verify database record was created
        session = db_session.query(AIInteraction).filter_by(id=session_id).first()

        assert session is not None
        assert session.ai_tool == "claude-session"
        assert session.is_session == 1  # SQLite stores booleans as integers
        assert session.summary_generated == 0

    @patch('backend.services.session_manager.subprocess.run')
    @patch('backend.services.session_manager.print_chronicle_banner')
    def test_start_session_saves_metadata_file(self, mock_banner, mock_subprocess, session_manager):
        """start_session creates metadata file."""
        mock_subprocess.return_value = Mock(returncode=0)

        with patch.object(session_manager, '_finalize_session'):
            session_id = session_manager.start_session('claude')

        # Check metadata file exists
        metadata_file = session_manager.session_dir / f"session_{session_id}.meta"
        assert metadata_file.exists()

        # Verify metadata content
        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["session_id"] == session_id
        assert metadata["tool"] == "claude"
        assert metadata["command"] == "claude"
        assert "start_time" in metadata

    @patch('backend.services.session_manager.subprocess.run')
    @patch('backend.services.session_manager.print_chronicle_banner')
    def test_start_session_with_custom_command(self, mock_banner, mock_subprocess, session_manager):
        """start_session accepts custom tool command."""
        mock_subprocess.return_value = Mock(returncode=0)

        with patch.object(session_manager, '_finalize_session'):
            session_id = session_manager.start_session('python', tool_command='python3 -i')

        # Verify metadata has custom command
        metadata = session_manager._load_metadata(session_id)
        assert metadata["command"] == "python3 -i"

    @patch('backend.services.session_manager.subprocess.Popen')
    @patch('backend.services.session_manager.print_quit_banner')
    @patch('backend.services.session_manager.clean_transcript')
    def test_finalize_session_creates_cleaned_file(self, mock_clean, mock_quit_banner, mock_popen, session_manager, temp_db, tmp_path):
        """_finalize_session creates .cleaned transcript file."""
        db_session, _ = temp_db

        # Create session in database
        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Starting...",
            is_session=True,
            session_transcript=None
        )
        db_session.add(session)
        db_session.commit()

        # Create metadata
        metadata = {
            "session_id": session.id,
            "tool": "claude",
            "start_time": datetime.now().isoformat()
        }
        session_manager._save_metadata(session.id, metadata)

        # Create raw transcript
        transcript_file = tmp_path / f"session_{session.id}.log"
        transcript_file.write_text("Raw transcript with \x1b[31mANSI codes\x1b[0m")

        # Mock clean_transcript to return cleaned version
        mock_clean.return_value = "Cleaned transcript"

        # Finalize session
        session_manager._finalize_session(session.id, transcript_file, exit_code=0)

        # Verify .cleaned file was created
        cleaned_file = transcript_file.with_suffix('.cleaned')
        assert cleaned_file.exists()
        assert cleaned_file.read_text() == "Cleaned transcript"

    @patch('backend.services.session_manager.subprocess.Popen')
    @patch('backend.services.session_manager.print_quit_banner')
    @patch('backend.services.session_manager.clean_transcript')
    def test_finalize_session_updates_database_record(self, mock_clean, mock_quit_banner, mock_popen, session_manager, temp_db, tmp_path):
        """_finalize_session updates AIInteraction with duration."""
        db_session, _ = temp_db

        # Create session
        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Starting...",
            is_session=True,
            session_transcript=None
        )
        db_session.add(session)
        db_session.commit()

        # Create metadata (simulate 5-minute session)
        from datetime import timedelta
        start_time = datetime.now() - timedelta(minutes=5)
        metadata = {
            "session_id": session.id,
            "tool": "claude",
            "start_time": start_time.isoformat()
        }
        session_manager._save_metadata(session.id, metadata)

        # Create transcript
        transcript_file = tmp_path / f"session_{session.id}.log"
        transcript_file.write_text("Transcript")
        mock_clean.return_value = "Cleaned"

        # Finalize
        session_manager._finalize_session(session.id, transcript_file, exit_code=0)

        # Verify database was updated
        db_session.refresh(session)
        assert session.duration_ms is not None
        assert session.duration_ms > 0  # Should be ~5 minutes in milliseconds
        assert "5." in session.prompt  # Should show "5.0m" or similar
        assert session.session_transcript is None  # Should NOT store in database

    @patch('backend.services.session_manager.subprocess.Popen')
    @patch('backend.services.session_manager.print_quit_banner')
    @patch('backend.services.session_manager.clean_transcript')
    def test_finalize_session_spawns_background_summarization(self, mock_clean, mock_quit_banner, mock_popen, session_manager, temp_db, tmp_path):
        """_finalize_session spawns background process for summarization."""
        db_session, _ = temp_db

        # Create session
        session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test",
            is_session=True
        )
        db_session.add(session)
        db_session.commit()

        metadata = {"session_id": session.id, "tool": "claude", "start_time": datetime.now().isoformat()}
        session_manager._save_metadata(session.id, metadata)

        transcript_file = tmp_path / f"session_{session.id}.log"
        transcript_file.write_text("Transcript")
        mock_clean.return_value = "Cleaned"

        # Finalize
        session_manager._finalize_session(session.id, transcript_file, exit_code=0)

        # Verify Popen was called for background summarization
        assert mock_popen.called
        call_args = mock_popen.call_args

        # Check that it's running the summarize-chunked command
        assert "backend.main" in call_args[0][0]
        assert "summarize-chunked" in call_args[0][0]
        assert str(session.id) in call_args[0][0]
