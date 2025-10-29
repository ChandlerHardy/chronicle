"""Tests for CLI commands in backend/cli/commands.py"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, AIInteraction, Commit
from backend.main import cli


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
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestShowCommand:
    """Tests for 'chronicle show' command."""

    def test_show_today_with_commits(self, temp_db, runner):
        """Test 'chronicle show today' displays today's commits."""
        session, db_path = temp_db

        # Add a commit from today
        commit = Commit(
            timestamp=datetime.now(),
            sha="abc123",
            message="Add feature X",
            branch="main",
            author="Test User",
            repo_path="/test/repo",
            files_changed=json.dumps(["file1.py", "file2.py"])
        )
        session.add(commit)
        session.commit()
        session.close()

        # Run command - set env var so it uses our test DB
        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['show', 'today'])

        assert result.exit_code == 0
        assert "Add feature X" in result.output or "abc123" in result.output or "test/repo" in result.output

    def test_show_today_with_no_commits(self, temp_db, runner):
        """Test 'chronicle show today' with no commits."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['show', 'today'])

        assert result.exit_code == 0
        assert "No commits" in result.output or "0 commits" in result.output.lower()

    def test_show_yesterday(self, temp_db, runner):
        """Test 'chronicle show yesterday' displays yesterday's commits."""
        session, db_path = temp_db

        # Add a commit from yesterday
        yesterday = datetime.now() - timedelta(days=1)
        commit = Commit(
            timestamp=yesterday,
            sha="def456",
            message="Fix bug Y",
            branch="main",
            author="Test User",
            repo_path="/test/repo"
        )
        session.add(commit)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['show', 'yesterday'])

        assert result.exit_code == 0
        assert "Fix bug Y" in result.output

    def test_show_week(self, temp_db, runner):
        """Test 'chronicle show week' displays last 7 days of commits."""
        session, db_path = temp_db

        # Add commits from various days
        for i in range(7):
            commit = Commit(
                timestamp=datetime.now() - timedelta(days=i),
                sha=f"sha{i}",
                message=f"Commit {i}",
                branch="main",
                author="Test User",
                repo_path="/test/repo"
            )
            session.add(commit)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['show', 'week'])

        assert result.exit_code == 0
        # Should show multiple commits
        assert "Commit 0" in result.output
        assert "Commit 6" in result.output


class TestSessionsCommand:
    """Tests for 'chronicle sessions' command."""

    def test_sessions_lists_all_sessions(self, temp_db, runner):
        """Test 'chronicle sessions' lists all recorded sessions."""
        session, db_path = temp_db

        # Add multiple sessions
        for i in range(3):
            ai_session = AIInteraction(
                timestamp=datetime.now() - timedelta(hours=i),
                ai_tool="claude-session",
                prompt=f"Session {i}",
                is_session=True,
                duration_ms=60000 * (i + 1),
                title=f"Test Session {i}"
            )
            session.add(ai_session)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['sessions'])

        assert result.exit_code == 0
        assert "Test Session 0" in result.output
        assert "Test Session 1" in result.output
        assert "Test Session 2" in result.output

    def test_sessions_with_no_sessions(self, temp_db, runner):
        """Test 'chronicle sessions' with no recorded sessions."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['sessions'])

        assert result.exit_code == 0
        assert "No sessions" in result.output.lower() or "0 sessions" in result.output

    def test_sessions_shows_duration(self, temp_db, runner):
        """Test 'chronicle sessions' displays session durations."""
        session, db_path = temp_db

        ai_session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Long session",
            is_session=True,
            duration_ms=3600000  # 60 minutes
        )
        session.add(ai_session)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['sessions'])

        assert result.exit_code == 0
        # Should show duration in some form (minutes or hours)
        assert "60" in result.output or "1.0" in result.output


class TestSessionCommand:
    """Tests for 'chronicle session <id>' command."""

    def test_session_displays_session_details(self, temp_db, runner):
        """Test 'chronicle session <id>' shows session details."""
        session, db_path = temp_db

        # Create a session with details
        ai_session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Test session",
            is_session=True,
            duration_ms=120000,
            title="Detailed Session",
            tags="test,cli",
            keywords=json.dumps(["testing", "cli", "chronicle"]),
            response_summary="This is a test summary",
            summary_generated=True,
            session_transcript="User: Hello\nAssistant: Hi!"
        )
        session.add(ai_session)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['session', str(ai_session.id)])

        assert result.exit_code == 0
        assert "Detailed Session" in result.output
        assert "This is a test summary" in result.output

    def test_session_nonexistent_id(self, temp_db, runner):
        """Test 'chronicle session <id>' with invalid ID."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['session', '999'])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_session_triggers_summary_generation(self, temp_db, runner):
        """Test viewing session without summary triggers summarization."""
        session, db_path = temp_db

        # Create session without summary
        ai_session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Unsummarized",
            is_session=True,
            session_transcript="Short transcript",
            summary_generated=False
        )
        session.add(ai_session)
        session.commit()

        # Mock summarizer to avoid actual API calls
        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            with patch('backend.cli.commands.Summarizer') as mock_summarizer:
                mock_instance = Mock()
                mock_instance.summarize_session.return_value = "Generated summary"
                mock_summarizer.return_value = mock_instance

                result = runner.invoke(cli, ['session', str(ai_session.id)])

        assert result.exit_code == 0
        # Should have attempted to generate summary
        mock_instance.summarize_session.assert_called_once()


class TestAddRepoCommand:
    """Tests for 'chronicle add-repo' command."""

    def test_add_repo_valid_git_repository(self, temp_db, runner, tmp_path):
        """Test adding a valid git repository."""
        _, db_path = tmp_path

        # Create a fake git repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            # Mock get_session to avoid actual DB interaction
            with patch('backend.cli.commands.get_session'):
                with patch('backend.services.git_monitor.GitMonitor.add_tracked_repo') as mock_add:
                    result = runner.invoke(cli, ['add-repo', str(repo_path)])

        assert result.exit_code == 0
        assert "added" in result.output.lower() or "tracking" in result.output.lower()

    def test_add_repo_nonexistent_path(self, temp_db, runner):
        """Test adding nonexistent repository path."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['add-repo', '/nonexistent/path'])

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()


class TestSyncCommand:
    """Tests for 'chronicle sync' command."""

    def test_sync_scans_tracked_repos(self, temp_db, runner):
        """Test 'chronicle sync' scans tracked repositories."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            with patch('backend.cli.commands.get_session'):
                with patch('backend.services.git_monitor.GitMonitor.get_tracked_repos', return_value=[]):
                    result = runner.invoke(cli, ['sync'])

        assert result.exit_code == 0
        # Should indicate syncing occurred
        assert "sync" in result.output.lower() or "scan" in result.output.lower()


class TestTimelineCommand:
    """Tests for 'chronicle timeline' command."""

    def test_timeline_shows_commits_and_sessions(self, temp_db, runner):
        """Test 'chronicle timeline' displays both commits and AI sessions."""
        session, db_path = temp_db

        # Add a commit
        commit = Commit(
            timestamp=datetime.now(),
            sha="abc123",
            message="Add feature",
            branch="main",
            author="Test User",
            repo_path="/test/repo"
        )
        session.add(commit)

        # Add an AI session
        ai_session = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Code session",
            is_session=True,
            title="Coding Session"
        )
        session.add(ai_session)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['timeline', 'today'])

        assert result.exit_code == 0
        assert "Add feature" in result.output
        assert "Coding Session" in result.output or "Code session" in result.output

    def test_timeline_today_empty(self, temp_db, runner):
        """Test 'chronicle timeline today' with no data."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['timeline', 'today'])

        assert result.exit_code == 0
        # Should handle empty timeline gracefully


class TestSearchCommand:
    """Tests for 'chronicle search' command."""

    def test_search_finds_matching_commits(self, temp_db, runner):
        """Test 'chronicle search' finds commits by keyword."""
        session, db_path = temp_db

        # Add commits with different messages
        commit1 = Commit(
            timestamp=datetime.now(),
            sha="abc123",
            message="Fix authentication bug",
            branch="main",
            author="Test User",
            repo_path="/test/repo"
        )
        commit2 = Commit(
            timestamp=datetime.now(),
            sha="def456",
            message="Add logging feature",
            branch="main",
            author="Test User",
            repo_path="/test/repo"
        )
        session.add(commit1)
        session.add(commit2)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['search', 'authentication'])

        assert result.exit_code == 0
        assert "Fix authentication bug" in result.output
        assert "Add logging feature" not in result.output

    def test_search_no_results(self, temp_db, runner):
        """Test 'chronicle search' with no matching results."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['search', 'nonexistent'])

        assert result.exit_code == 0
        assert "no" in result.output.lower() or "0" in result.output


class TestAiCommand:
    """Tests for 'chronicle ai' command."""

    def test_ai_today_shows_interactions(self, temp_db, runner):
        """Test 'chronicle ai today' shows AI interactions."""
        session, db_path = temp_db

        # Add AI interactions
        interaction = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude",
            prompt="How do I test this?",
            response_summary="Use pytest fixtures",
            is_session=False
        )
        session.add(interaction)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['ai', 'today'])

        assert result.exit_code == 0
        assert "How do I test this?" in result.output or "pytest" in result.output


class TestAiStatsCommand:
    """Tests for 'chronicle ai-stats' command."""

    def test_ai_stats_shows_usage_statistics(self, temp_db, runner):
        """Test 'chronicle ai-stats' displays usage statistics."""
        session, db_path = temp_db

        # Add multiple AI interactions
        for i in range(5):
            interaction = AIInteraction(
                timestamp=datetime.now() - timedelta(hours=i),
                ai_tool="claude",
                prompt=f"Question {i}",
                response_summary="Answer",
                is_session=False
            )
            session.add(interaction)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['ai-stats'])

        assert result.exit_code == 0
        # Should show some statistics
        assert "5" in result.output or "total" in result.output.lower()


class TestConfigCommand:
    """Tests for 'chronicle config' command."""

    def test_config_list_shows_settings(self, runner, tmp_path):
        """Test 'chronicle config --list' displays configuration."""
        # Mock config file
        config_path = tmp_path / "config.yaml"
        config_path.write_text("ai:\n  gemini_api_key: test_key_123\n")

        with patch('backend.core.config.Config.config_file', config_path):
            result = runner.invoke(cli, ['config', '--list'])

        assert result.exit_code == 0
        # Should mask API keys
        assert "***" in result.output or "masked" in result.output.lower()

    def test_config_get_specific_key(self, runner, tmp_path):
        """Test 'chronicle config <key>' retrieves specific value."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("ai:\n  default_model: gemini-2.0-flash\n")

        with patch('backend.core.config.Config.config_file', config_path):
            result = runner.invoke(cli, ['config', 'ai.default_model'])

        assert result.exit_code == 0
        assert "gemini-2.0-flash" in result.output

    def test_config_set_value(self, runner, tmp_path):
        """Test 'chronicle config <key> <value>' sets configuration."""
        config_path = tmp_path / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('backend.core.config.Config.config_file', config_path):
            result = runner.invoke(cli, ['config', 'ai.default_model', 'gemini-2.5-flash'])

        assert result.exit_code == 0
        assert "set" in result.output.lower() or "updated" in result.output.lower()


class TestStatusCommand:
    """Tests for 'chronicle status' command."""

    def test_status_shows_active_session(self, temp_db, runner):
        """Test 'chronicle status' shows active session info."""
        session, db_path = temp_db

        # Create active session (no duration)
        active = AIInteraction(
            timestamp=datetime.now(),
            ai_tool="claude-session",
            prompt="Active session",
            is_session=True,
            session_transcript=None,
            duration_ms=None
        )
        session.add(active)
        session.commit()

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['status'])

        assert result.exit_code == 0
        assert "active" in result.output.lower() or "session" in result.output.lower()

    def test_status_no_active_session(self, temp_db, runner):
        """Test 'chronicle status' when no active session."""
        _, db_path = temp_db

        with patch.dict(os.environ, {'CHRONICLE_DB': db_path}):
            result = runner.invoke(cli, ['status'])

        assert result.exit_code == 0
        assert "no active" in result.output.lower() or "not tracking" in result.output.lower()
