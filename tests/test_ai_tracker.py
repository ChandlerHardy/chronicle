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
