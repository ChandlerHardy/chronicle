"""Tests for AI interaction tracking service."""

import os
import tempfile
from datetime import datetime, timedelta
import pytest

from backend.database.models import init_db, AIInteraction, Commit
from backend.services.ai_tracker import AITracker


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    engine, SessionLocal = init_db(db_path)
    session = SessionLocal()

    yield session

    session.close()
    os.unlink(db_path)


def test_log_interaction(temp_db):
    """Test logging an AI interaction."""
    tracker = AITracker(temp_db)

    interaction = tracker.log_interaction(
        ai_tool="gemini-cli",
        prompt="What is Python?",
        response="Python is a programming language...",
        duration_ms=1500
    )

    assert interaction.id is not None
    assert interaction.ai_tool == "gemini-cli"
    assert interaction.prompt == "What is Python?"
    assert "Python is a programming language" in interaction.response_summary
    assert interaction.duration_ms == 1500


def test_response_truncation(temp_db):
    """Test that long responses are truncated to 500 chars."""
    tracker = AITracker(temp_db)

    long_response = "A" * 1000

    interaction = tracker.log_interaction(
        ai_tool="qwen-cli",
        prompt="Tell me about something",
        response=long_response
    )

    assert len(interaction.response_summary) == 500
    assert interaction.response_summary == "A" * 500


def test_get_interactions_today(temp_db):
    """Test getting today's interactions."""
    tracker = AITracker(temp_db)

    # Log some interactions
    tracker.log_interaction("gemini-cli", "Question 1")
    tracker.log_interaction("qwen-cli", "Question 2")
    tracker.log_interaction("gemini-cli", "Question 3")

    # Get all today
    interactions = tracker.get_interactions_today()
    assert len(interactions) == 3

    # Filter by tool
    gemini_interactions = tracker.get_interactions_today(ai_tool="gemini-cli")
    assert len(gemini_interactions) == 2
    assert all(i.ai_tool == "gemini-cli" for i in gemini_interactions)


def test_search_interactions(temp_db):
    """Test searching interactions by prompt content."""
    tracker = AITracker(temp_db)

    tracker.log_interaction("gemini-cli", "How to use Python async/await?")
    tracker.log_interaction("qwen-cli", "Explain JavaScript promises")
    tracker.log_interaction("gemini-cli", "Python list comprehension examples")

    # Search for Python
    results = tracker.search_interactions("Python")
    assert len(results) == 2
    assert all("Python" in r.prompt for r in results)

    # Search for JavaScript
    results = tracker.search_interactions("JavaScript")
    assert len(results) == 1
    assert "JavaScript" in results[0].prompt


def test_link_to_commit(temp_db):
    """Test linking AI interaction to a commit."""
    tracker = AITracker(temp_db)

    # Create an AI interaction
    interaction = tracker.log_interaction(
        "gemini-cli",
        "Add authentication feature"
    )

    # Initially no commit linked
    assert interaction.related_commit_id is None

    # Create a commit shortly after
    commit = Commit(
        timestamp=datetime.now() + timedelta(minutes=5),
        sha="abc123",
        message="Add user authentication",
        branch="main",
        author="Test User",
        repo_path="/test/repo"
    )
    temp_db.add(commit)
    temp_db.commit()

    # Manually trigger linking
    tracker._link_to_commit(interaction)

    # Now should be linked
    temp_db.refresh(interaction)
    assert interaction.related_commit_id == commit.id


def test_ai_tool_stats(temp_db):
    """Test AI tool usage statistics."""
    tracker = AITracker(temp_db)

    # Log interactions with different tools
    tracker.log_interaction("gemini-cli", "Q1", duration_ms=1000)
    tracker.log_interaction("gemini-cli", "Q2", duration_ms=2000)
    tracker.log_interaction("qwen-cli", "Q3", duration_ms=1500)

    stats = tracker.get_ai_tool_stats(days=30)

    assert "gemini-cli" in stats
    assert stats["gemini-cli"]["count"] == 2
    assert stats["gemini-cli"]["total_duration_ms"] == 3000

    assert "qwen-cli" in stats
    assert stats["qwen-cli"]["count"] == 1
    assert stats["qwen-cli"]["total_duration_ms"] == 1500


def test_get_interaction_with_commit(temp_db):
    """Test getting interaction with its related commit."""
    tracker = AITracker(temp_db)

    # Create commit first
    commit = Commit(
        timestamp=datetime.now(),
        sha="def456",
        message="Fix bug",
        branch="main",
        author="Test User",
        repo_path="/test/repo"
    )
    temp_db.add(commit)
    temp_db.commit()

    # Create interaction and manually link it
    interaction = tracker.log_interaction("gemini-cli", "Debug the issue")
    interaction.related_commit_id = commit.id
    temp_db.commit()

    # Get with commit
    retrieved_interaction, retrieved_commit = tracker.get_interaction_with_commit(interaction.id)

    assert retrieved_interaction.id == interaction.id
    assert retrieved_commit.id == commit.id
    assert retrieved_commit.sha == "def456"


def test_files_mentioned(temp_db):
    """Test storing files mentioned in interaction."""
    tracker = AITracker(temp_db)

    interaction = tracker.log_interaction(
        "gemini-cli",
        "Review auth.py and middleware.py",
        files_mentioned=["auth.py", "middleware.py", "tests/test_auth.py"]
    )

    assert len(interaction.files_list) == 3
    assert "auth.py" in interaction.files_list
    assert "middleware.py" in interaction.files_list
    assert "tests/test_auth.py" in interaction.files_list


def test_get_active_session_returns_session_with_no_duration(temp_db):
    """Test that get_active_session returns a session that has no duration (still running)."""
    tracker = AITracker(temp_db)

    # Create an active session (no duration)
    active_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now(),
        prompt="Test session",
        is_session=True,
        duration_ms=None  # Active session has no duration
    )
    temp_db.add(active_session)
    temp_db.commit()

    # Create a completed session (has duration)
    completed_session = AIInteraction(
        ai_tool="gemini-cli",
        timestamp=datetime.now() - timedelta(hours=1),
        prompt="Completed session",
        is_session=True,
        duration_ms=3600000  # 1 hour
    )
    temp_db.add(completed_session)
    temp_db.commit()

    # Get active session
    result = tracker.get_active_session()

    assert result is not None
    assert result.id == active_session.id
    assert result.duration_ms is None


def test_get_active_session_returns_none_when_no_active(temp_db):
    """Test that get_active_session returns None when all sessions are completed."""
    tracker = AITracker(temp_db)

    # Create only completed sessions
    completed_session1 = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now() - timedelta(hours=2),
        prompt="Completed 1",
        is_session=True,
        duration_ms=7200000
    )
    completed_session2 = AIInteraction(
        ai_tool="gemini-cli",
        timestamp=datetime.now() - timedelta(hours=1),
        prompt="Completed 2",
        is_session=True,
        duration_ms=3600000
    )
    temp_db.add(completed_session1)
    temp_db.add(completed_session2)
    temp_db.commit()

    # Get active session
    result = tracker.get_active_session()

    assert result is None


def test_get_active_session_filters_by_tool(temp_db):
    """Test that get_active_session can filter by AI tool."""
    tracker = AITracker(temp_db)

    # Create active sessions for different tools
    claude_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now() - timedelta(minutes=10),
        prompt="Claude session",
        is_session=True,
        duration_ms=None
    )
    gemini_session = AIInteraction(
        ai_tool="gemini-cli",
        timestamp=datetime.now(),
        prompt="Gemini session",
        is_session=True,
        duration_ms=None
    )
    temp_db.add(claude_session)
    temp_db.add(gemini_session)
    temp_db.commit()

    # Get active Claude session
    result = tracker.get_active_session(ai_tool="claude-code")

    assert result is not None
    assert result.id == claude_session.id
    assert result.ai_tool == "claude-code"

    # Get active Gemini session
    result = tracker.get_active_session(ai_tool="gemini-cli")

    assert result is not None
    assert result.id == gemini_session.id
    assert result.ai_tool == "gemini-cli"


def test_get_active_session_returns_most_recent(temp_db):
    """Test that get_active_session returns the most recent active session."""
    tracker = AITracker(temp_db)

    # Create multiple active sessions
    older_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now() - timedelta(hours=1),
        prompt="Older active session",
        is_session=True,
        duration_ms=None
    )
    newer_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now(),
        prompt="Newer active session",
        is_session=True,
        duration_ms=None
    )
    temp_db.add(older_session)
    temp_db.add(newer_session)
    temp_db.commit()

    # Get active session - should return the newer one
    result = tracker.get_active_session()

    assert result is not None
    assert result.id == newer_session.id


def test_get_active_session_ignores_non_sessions(temp_db):
    """Test that get_active_session ignores one-shot interactions (is_session=False)."""
    tracker = AITracker(temp_db)

    # Create a one-shot interaction (not a session)
    one_shot = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now(),
        prompt="Quick question",
        is_session=False,  # Not a session
        duration_ms=None
    )
    temp_db.add(one_shot)
    temp_db.commit()

    # Get active session
    result = tracker.get_active_session()

    assert result is None  # Should not find the one-shot interaction


def test_get_interactions_today_filters_by_repo(temp_db):
    """Test that get_interactions_today filters by repository path."""
    tracker = AITracker(temp_db)

    # Create sessions in different repos
    chronicle_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now(),
        prompt="Chronicle work",
        is_session=True,
        repo_path="/Users/test/repos/chronicle"
    )
    portfolio_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=datetime.now(),
        prompt="Portfolio work",
        is_session=True,
        repo_path="/Users/test/repos/portfolio-website"
    )
    temp_db.add(chronicle_session)
    temp_db.add(portfolio_session)
    temp_db.commit()

    # Get all sessions
    all_sessions = tracker.get_interactions_today()
    assert len(all_sessions) == 2

    # Filter by chronicle repo
    chronicle_sessions = tracker.get_interactions_today(repo_path="/Users/test/repos/chronicle")
    assert len(chronicle_sessions) == 1
    assert chronicle_sessions[0].prompt == "Chronicle work"

    # Filter by portfolio repo (partial match)
    portfolio_sessions = tracker.get_interactions_today(repo_path="portfolio")
    assert len(portfolio_sessions) == 1
    assert portfolio_sessions[0].prompt == "Portfolio work"


def test_get_interactions_by_date_filters_by_repo(temp_db):
    """Test that get_interactions_by_date filters by repository path."""
    tracker = AITracker(temp_db)

    yesterday = datetime.now() - timedelta(days=1)

    # Create sessions in different repos
    chronicle_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=yesterday,
        prompt="Chronicle work yesterday",
        is_session=True,
        repo_path="/Users/test/repos/chronicle"
    )
    portfolio_session = AIInteraction(
        ai_tool="claude-code",
        timestamp=yesterday,
        prompt="Portfolio work yesterday",
        is_session=True,
        repo_path="/Users/test/repos/portfolio-website"
    )
    temp_db.add(chronicle_session)
    temp_db.add(portfolio_session)
    temp_db.commit()

    # Get all sessions from yesterday
    all_sessions = tracker.get_interactions_by_date(yesterday)
    assert len(all_sessions) == 2

    # Filter by chronicle repo
    chronicle_sessions = tracker.get_interactions_by_date(yesterday, repo_path="chronicle")
    assert len(chronicle_sessions) == 1
    assert chronicle_sessions[0].prompt == "Chronicle work yesterday"

    # Filter by portfolio repo
    portfolio_sessions = tracker.get_interactions_by_date(yesterday, repo_path="portfolio")
    assert len(portfolio_sessions) == 1
    assert portfolio_sessions[0].prompt == "Portfolio work yesterday"
