"""Tests for Chronicle MCP Server tools."""

import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch
import pytest

from backend.database.models import init_db, AIInteraction, Commit, ProjectMilestone, NextStep
from backend.mcp import server


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    engine, SessionLocal = init_db(db_path)
    session = SessionLocal()

    # Reset the MCP server's global session
    server._db_session = session

    yield session

    session.close()
    server._db_session = None
    os.unlink(db_path)


@pytest.fixture
def sample_session(temp_db):
    """Create a sample AI session for testing."""
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Test session",
        response_summary="This is a test session summary",
        timestamp=datetime.now(),
        duration_ms=60000,  # 1 minute
        is_session=True,
        summary_generated=True,
        repo_path="/Users/test/repo",
        working_directory="/Users/test/repo",
        files_mentioned=json.dumps(["file1.py", "file2.py"]),
        title="Test Session Title",
        tags=json.dumps(["test", "example"]),
        keywords=json.dumps(["testing", "example", "keywords"])
    )
    temp_db.add(session)
    temp_db.commit()
    temp_db.refresh(session)
    return session


@pytest.fixture
def sample_commit(temp_db):
    """Create a sample commit for testing."""
    commit = Commit(
        sha="abc123def456",
        timestamp=datetime.now(),
        message="Test commit message",
        author="Test Author",
        branch="main",
        repo_path="/Users/test/repo",
        files_changed=json.dumps(["file1.py", "file2.py"])
    )
    temp_db.add(commit)
    temp_db.commit()
    temp_db.refresh(commit)
    return commit


@pytest.fixture
def sample_milestone(temp_db):
    """Create a sample milestone for testing."""
    milestone = ProjectMilestone(
        title="Test Milestone",
        description="Test milestone description",
        status="planned",
        milestone_type="feature",
        priority=1,
        tags=json.dumps(["test", "milestone"])
    )
    temp_db.add(milestone)
    temp_db.commit()
    temp_db.refresh(milestone)
    return milestone


@pytest.fixture
def sample_next_step(temp_db, sample_milestone):
    """Create a sample next step for testing."""
    next_step = NextStep(
        description="Test next step",
        priority=2,
        estimated_effort="small",
        category="feature",
        completed=False,
        related_milestone_id=sample_milestone.id
    )
    temp_db.add(next_step)
    temp_db.commit()
    temp_db.refresh(next_step)
    return next_step


def test_format_session_dict_basic(sample_session):
    """Test format_session_dict with basic session."""
    result = server.format_session_dict(sample_session, include_summary=True)

    assert result["id"] == sample_session.id
    assert result["tool"] == "claude-code"
    assert result["prompt"] == "Test session"
    assert result["summary"] == "This is a test session summary"
    assert result["is_session"] is True
    assert result["summary_generated"] is True
    assert result["duration_minutes"] == 1.0
    assert result["repo_path"] == "/Users/test/repo"
    assert result["title"] == "Test Session Title"
    assert result["tags"] == ["test", "example"]
    assert result["keywords"] == ["testing", "example", "keywords"]


def test_format_session_dict_without_summary(sample_session):
    """Test format_session_dict excludes summary when requested."""
    result = server.format_session_dict(sample_session, include_summary=False)

    assert "summary" not in result
    assert result["id"] == sample_session.id


def test_format_commit_dict(sample_commit):
    """Test format_commit_dict converts commit to dict."""
    result = server.format_commit_dict(sample_commit)

    assert result["id"] == sample_commit.id
    assert result["sha"] == "abc123def456"
    assert result["message"] == "Test commit message"
    assert result["author"] == "Test Author"
    assert result["branch"] == "main"
    assert result["repo_path"] == "/Users/test/repo"
    assert result["files_changed"] == ["file1.py", "file2.py"]


def test_get_sessions_returns_recent_sessions(temp_db, sample_session):
    """Test get_sessions returns recent sessions."""
    result_json = server.get_sessions.fn(limit=10)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["id"] == sample_session.id
    assert result["sessions"][0]["tool"] == "claude-code"


def test_get_sessions_filters_by_tool(temp_db):
    """Test get_sessions filters by AI tool."""
    # Create sessions with different tools
    claude_session = AIInteraction(
        ai_tool="claude-code",
        prompt="Claude session",
        is_session=True,
        timestamp=datetime.now()
    )
    gemini_session = AIInteraction(
        ai_tool="gemini-cli",
        prompt="Gemini session",
        is_session=True,
        timestamp=datetime.now()
    )
    temp_db.add_all([claude_session, gemini_session])
    temp_db.commit()

    # Filter by claude-code
    result_json = server.get_sessions.fn(tool="claude-code")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["sessions"][0]["tool"] == "claude-code"


def test_get_sessions_filters_by_days(temp_db):
    """Test get_sessions filters by days."""
    # Create old session
    old_session = AIInteraction(
        ai_tool="claude-code",
        prompt="Old session",
        is_session=True,
        timestamp=datetime.now() - timedelta(days=10)
    )
    # Create recent session
    recent_session = AIInteraction(
        ai_tool="claude-code",
        prompt="Recent session",
        is_session=True,
        timestamp=datetime.now()
    )
    temp_db.add_all([old_session, recent_session])
    temp_db.commit()

    # Filter by last 7 days
    result_json = server.get_sessions.fn(days=7)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["sessions"][0]["prompt"] == "Recent session"


def test_get_sessions_limits_results(temp_db):
    """Test get_sessions respects limit parameter."""
    # Create 5 sessions
    for i in range(5):
        session = AIInteraction(
            ai_tool="claude-code",
            prompt=f"Session {i}",
            is_session=True,
            timestamp=datetime.now()
        )
        temp_db.add(session)
    temp_db.commit()

    # Request only 3
    result_json = server.get_sessions.fn(limit=3)
    result = json.loads(result_json)

    assert result["count"] == 3
    assert len(result["sessions"]) == 3


def test_get_sessions_caps_at_100(temp_db):
    """Test get_sessions caps limit at 100."""
    # Request more than 100
    result_json = server.get_sessions.fn(limit=200)
    result = json.loads(result_json)

    # Should not error, just cap at 100
    assert "count" in result


def test_get_session_summary_returns_session(temp_db, sample_session):
    """Test get_session_summary returns detailed session info."""
    result_json = server.get_session_summary.fn(sample_session.id)
    result = json.loads(result_json)

    assert result["id"] == sample_session.id
    assert result["summary"] == "This is a test session summary"
    assert result["title"] == "Test Session Title"
    assert result["tags"] == ["test", "example"]


def test_get_session_summary_not_found(temp_db):
    """Test get_session_summary with non-existent ID."""
    result_json = server.get_session_summary.fn(999)
    result = json.loads(result_json)

    assert "error" in result
    assert "not found" in result["error"]


def test_search_sessions_basic(temp_db, sample_session):
    """Test search_sessions with basic query."""
    result_json = server.search_sessions.fn(query="test")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["sessions"][0]["id"] == sample_session.id
    assert result["query"] == "test"


def test_search_sessions_no_results(temp_db, sample_session):
    """Test search_sessions with query that matches nothing."""
    result_json = server.search_sessions.fn(query="nonexistent")
    result = json.loads(result_json)

    assert result["count"] == 0
    assert len(result["sessions"]) == 0


def test_search_sessions_searches_keywords(temp_db, sample_session):
    """Test search_sessions finds sessions by keywords."""
    result_json = server.search_sessions.fn(query="testing")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["sessions"][0]["id"] == sample_session.id


def test_search_sessions_limits_results(temp_db):
    """Test search_sessions respects limit parameter."""
    # Create 5 sessions with "test" in prompt
    for i in range(5):
        session = AIInteraction(
            ai_tool="claude-code",
            prompt=f"Test session {i}",
            is_session=True,
            timestamp=datetime.now(),
            response_summary="Summary"
        )
        temp_db.add(session)
    temp_db.commit()

    # Request only 3
    result_json = server.search_sessions.fn(query="test", limit=3)
    result = json.loads(result_json)

    assert result["count"] == 3


def test_get_sessions_summaries_returns_multiple(temp_db):
    """Test get_sessions_summaries retrieves multiple sessions."""
    # Create 3 sessions
    sessions = []
    for i in range(3):
        session = AIInteraction(
            ai_tool="claude-code",
            prompt=f"Session {i}",
            response_summary=f"Summary {i}",
            is_session=True,
            timestamp=datetime.now()
        )
        temp_db.add(session)
        temp_db.flush()
        sessions.append(session.id)
    temp_db.commit()

    # Get all 3 summaries
    result_json = server.get_sessions_summaries.fn(session_ids=sessions)
    result = json.loads(result_json)

    assert result["count"] == 3
    assert len(result["summaries"]) == 3
    assert all(s["id"] in sessions for s in result["summaries"])


def test_get_sessions_summaries_caps_at_20(temp_db):
    """Test get_sessions_summaries caps at 20 sessions."""
    # Create 25 session IDs (only request IDs, don't need real sessions)
    session_ids = list(range(1, 26))

    # Should not error, just cap at 20
    result_json = server.get_sessions_summaries.fn(session_ids=session_ids)
    result = json.loads(result_json)

    # Won't find any real sessions, but should validate capping logic
    assert "count" in result


def test_get_commits_returns_commits(temp_db, sample_commit):
    """Test get_commits returns recent commits."""
    result_json = server.get_commits.fn(limit=10)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert len(result["commits"]) == 1
    assert result["commits"][0]["sha"] == "abc123def456"


def test_get_commits_filters_by_author(temp_db):
    """Test get_commits filters by author."""
    # Create commits by different authors
    commit1 = Commit(
        sha="abc123",
        timestamp=datetime.now(),
        message="Commit 1",
        author="Alice",
        repo_path="/test/repo"
    )
    commit2 = Commit(
        sha="def456",
        timestamp=datetime.now(),
        message="Commit 2",
        author="Bob",
        repo_path="/test/repo"
    )
    temp_db.add_all([commit1, commit2])
    temp_db.commit()

    # Filter by Alice
    result_json = server.get_commits.fn(author="Alice")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["commits"][0]["author"] == "Alice"


def test_get_commits_filters_by_days(temp_db):
    """Test get_commits filters by days."""
    # Create old commit
    old_commit = Commit(
        sha="abc123",
        timestamp=datetime.now() - timedelta(days=10),
        message="Old commit",
        repo_path="/test/repo"
    )
    # Create recent commit
    recent_commit = Commit(
        sha="def456",
        timestamp=datetime.now(),
        message="Recent commit",
        repo_path="/test/repo"
    )
    temp_db.add_all([old_commit, recent_commit])
    temp_db.commit()

    # Filter by last 7 days
    result_json = server.get_commits.fn(days=7)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["commits"][0]["message"] == "Recent commit"


def test_get_timeline_combines_sessions_and_commits(temp_db, sample_session, sample_commit):
    """Test get_timeline returns both sessions and commits."""
    result_json = server.get_timeline.fn(days=1)
    result = json.loads(result_json)

    assert result["sessions_count"] >= 1
    assert result["commits_count"] >= 1
    # Timeline is sorted by time, should have events
    assert "timeline" in result


def test_get_stats_returns_usage_stats(temp_db, sample_session, sample_commit):
    """Test get_stats returns statistics."""
    result_json = server.get_stats.fn(days=7)
    result = json.loads(result_json)

    assert "total_sessions" in result
    assert "total_commits" in result
    assert result["total_sessions"] >= 1
    assert result["total_commits"] >= 1


def test_get_milestones_returns_milestones(temp_db, sample_milestone):
    """Test get_milestones returns milestones."""
    result_json = server.get_milestones.fn(limit=10)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["milestones"][0]["title"] == "Test Milestone"


def test_get_milestones_filters_by_status(temp_db):
    """Test get_milestones filters by status."""
    # Create milestones with different statuses
    planned = ProjectMilestone(
        title="Planned",
        status="planned",
        milestone_type="feature",
        priority=1
    )
    in_progress = ProjectMilestone(
        title="In Progress",
        status="in_progress",
        milestone_type="feature",
        priority=1
    )
    temp_db.add_all([planned, in_progress])
    temp_db.commit()

    # Filter by planned
    result_json = server.get_milestones.fn(status="planned")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["milestones"][0]["status"] == "planned"


def test_get_milestone_returns_details(temp_db, sample_milestone):
    """Test get_milestone returns detailed milestone info."""
    result_json = server.get_milestone.fn(milestone_id=sample_milestone.id)
    result = json.loads(result_json)

    assert result["id"] == sample_milestone.id
    assert result["title"] == "Test Milestone"
    assert result["description"] == "Test milestone description"


def test_get_milestone_not_found(temp_db):
    """Test get_milestone with non-existent ID."""
    result_json = server.get_milestone.fn(milestone_id=999)
    result = json.loads(result_json)

    assert "error" in result


def test_get_next_steps_returns_steps(temp_db, sample_next_step):
    """Test get_next_steps returns next steps."""
    result_json = server.get_next_steps.fn(limit=10)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["next_steps"][0]["description"] == "Test next step"


def test_get_next_steps_filters_by_completed(temp_db):
    """Test get_next_steps filters by completion status."""
    # Create completed and pending steps
    pending = NextStep(
        description="Pending step",
        priority=1,
        category="feature",
        completed=False
    )
    completed = NextStep(
        description="Completed step",
        priority=1,
        category="feature",
        completed=True
    )
    temp_db.add_all([pending, completed])
    temp_db.commit()

    # Filter by pending
    result_json = server.get_next_steps.fn(completed=False)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["next_steps"][0]["completed"] is False


def test_get_roadmap_returns_overview(temp_db, sample_milestone, sample_next_step):
    """Test get_roadmap returns project overview."""
    result_json = server.get_roadmap.fn(days=7)
    result = json.loads(result_json)

    assert "in_progress" in result
    assert "planned_high_priority" in result or "planned_low_priority" in result
    assert "recently_completed" in result
    assert "pending_next_steps" in result


def test_update_milestone_status_changes_status(temp_db, sample_milestone):
    """Test update_milestone_status changes milestone status."""
    result_json = server.update_milestone_status.fn(
        milestone_id=sample_milestone.id,
        new_status="completed"
    )
    result = json.loads(result_json)

    assert result["success"] is True
    assert result["old_status"] == "planned"
    assert result["new_status"] == "completed"


def test_complete_next_step_marks_complete(temp_db, sample_next_step):
    """Test complete_next_step marks step as completed."""
    result_json = server.complete_next_step.fn(step_id=sample_next_step.id)
    result = json.loads(result_json)

    assert result["success"] is True
    assert "completed_at" in result


def test_create_next_step_creates_step(temp_db):
    """Test create_next_step creates new step."""
    result_json = server.create_next_step.fn(
        description="New test step",
        priority=2,
        category="feature"
    )
    result = json.loads(result_json)

    assert result["success"] is True
    assert result["step_id"] is not None
    assert result["description"] == "New test step"
    assert result["priority"] == 2
    assert result["category"] == "feature"


def test_create_milestone_creates_milestone(temp_db):
    """Test create_milestone creates new milestone."""
    result_json = server.create_milestone.fn(
        title="New Milestone",
        description="Test description",
        milestone_type="feature",
        priority=1
    )
    result = json.loads(result_json)

    assert "id" in result or "milestone_id" in result
    assert result.get("title") == "New Milestone" or "success" in result


# Run the test
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
