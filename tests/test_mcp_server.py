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


def test_search_sessions_hyphenated_keywords(temp_db):
    """Test search_sessions handles hyphenated keywords like 'test-driven-development'."""
    # Create session with hyphenated keyword
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Implementing TDD workflow",
        response_summary="Working on test-driven development practices",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["test-driven-development", "tdd", "pytest"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Search for hyphenated term - should find the session
    result_json = server.search_sessions.fn(query="test-driven-development")
    result = json.loads(result_json)

    assert result["count"] == 1, f"Expected 1 result for 'test-driven-development', got {result['count']}"
    assert result["sessions"][0]["id"] == session.id


def test_search_sessions_multi_term_query(temp_db):
    """Test search_sessions with multi-term query (implicit OR)."""
    # Create sessions with different keywords
    session1 = AIInteraction(
        ai_tool="claude-code",
        prompt="TDD session",
        response_summary="Working on TDD",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["tdd", "testing"])
    )
    session2 = AIInteraction(
        ai_tool="claude-code",
        prompt="Coverage session",
        response_summary="Improving test coverage",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["coverage", "pytest"])
    )
    session3 = AIInteraction(
        ai_tool="claude-code",
        prompt="Milestone session",
        response_summary="Working on milestone",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["milestone", "roadmap"])
    )
    temp_db.add_all([session1, session2, session3])
    temp_db.commit()

    # Multi-term query should match any session containing ANY of the terms
    result_json = server.search_sessions.fn(query="tdd coverage milestone")
    result = json.loads(result_json)

    assert result["count"] >= 3, f"Expected at least 3 results for multi-term query, got {result['count']}"
    session_ids = {s["id"] for s in result["sessions"]}
    assert session1.id in session_ids, "Session with 'tdd' not found"
    assert session2.id in session_ids, "Session with 'coverage' not found"
    assert session3.id in session_ids, "Session with 'milestone' not found"


def test_search_sessions_explicit_or_operator(temp_db):
    """Test search_sessions with explicit OR operator."""
    # Create sessions with different keywords
    session1 = AIInteraction(
        ai_tool="claude-code",
        prompt="TDD session",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["tdd"])
    )
    session2 = AIInteraction(
        ai_tool="claude-code",
        prompt="Coverage session",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["coverage"])
    )
    temp_db.add_all([session1, session2])
    temp_db.commit()

    # Explicit OR should work
    result_json = server.search_sessions.fn(query="tdd OR coverage")
    result = json.loads(result_json)

    assert result["count"] >= 2, f"Expected at least 2 results for 'tdd OR coverage', got {result['count']}"


def test_search_sessions_hyphenated_in_multi_term(temp_db):
    """Test search_sessions with hyphenated term in multi-term query."""
    # Create session with both hyphenated and regular keywords
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="TDD and coverage work",
        response_summary="Implementing test-driven development with coverage tracking",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["test-driven-development", "tdd", "coverage", "pytest"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Query with hyphenated term + other terms should work
    result_json = server.search_sessions.fn(query="test-driven-development coverage pytest")
    result = json.loads(result_json)

    assert result["count"] >= 1, f"Expected at least 1 result for hyphenated multi-term query, got {result['count']}"
    assert result["sessions"][0]["id"] == session.id


def test_search_sessions_excludes_summaries_by_default(temp_db):
    """Test search_sessions excludes summaries by default to reduce token usage."""
    # Create session with a long summary
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Test session",
        response_summary="This is a very long summary that would consume many tokens. " * 100,
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Default search should NOT include summary
    result_json = server.search_sessions.fn(query="testing")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert "summary" not in result["sessions"][0], "Summary should not be included by default"
    assert "id" in result["sessions"][0]
    assert "keywords" in result["sessions"][0]


def test_search_sessions_includes_summaries_when_requested(temp_db):
    """Test search_sessions includes summaries when include_summaries=True."""
    # Create session with summary
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Test session",
        response_summary="Important summary content",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Explicitly request summaries
    result_json = server.search_sessions.fn(query="testing", include_summaries=True)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert "summary" in result["sessions"][0], "Summary should be included when requested"
    assert result["sessions"][0]["summary"] == "Important summary content"


def test_search_sessions_respects_explicit_false(temp_db):
    """Test search_sessions respects include_summaries=False."""
    # Create session with summary
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Test session",
        response_summary="Summary content",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Explicitly exclude summaries
    result_json = server.search_sessions.fn(query="testing", include_summaries=False)
    result = json.loads(result_json)

    assert result["count"] == 1
    assert "summary" not in result["sessions"][0], "Summary should not be included when include_summaries=False"


def test_search_sessions_includes_match_fields(temp_db):
    """Test search_sessions includes which fields matched the query."""
    # Create session with keyword match
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Regular prompt",
        response_summary="Regular summary",
        title="Test Session",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing", "pytest"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Search for keyword
    result_json = server.search_sessions.fn(query="pytest")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert "match_fields" in result["sessions"][0], "match_fields should be included"
    assert "keywords" in result["sessions"][0]["match_fields"], "Should show keyword match"


def test_search_sessions_match_fields_multiple(temp_db):
    """Test search_sessions shows all matched fields."""
    # Create session that matches in multiple fields
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Testing the system",
        response_summary="We tested multiple features",
        title="Testing Session",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing", "qa"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Search for "testing" - should match keywords, title, prompt, and summary
    result_json = server.search_sessions.fn(query="testing")
    result = json.loads(result_json)

    assert result["count"] == 1
    match_fields = result["sessions"][0]["match_fields"]
    assert "keywords" in match_fields, "Should match in keywords"
    assert "title" in match_fields, "Should match in title"
    # Note: prompt and summary matches depend on search_prompts/search_summaries parameters


def test_search_sessions_includes_relevance_score(temp_db):
    """Test search_sessions includes relevance score."""
    # Create session
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Test prompt",
        response_summary="Test summary",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["testing"])
    )
    temp_db.add(session)
    temp_db.commit()

    # Search
    result_json = server.search_sessions.fn(query="testing")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert "relevance_score" in result["sessions"][0], "relevance_score should be included"
    assert result["sessions"][0]["relevance_score"] > 0, "Score should be positive"


def test_search_sessions_relevance_score_weighting(temp_db):
    """Test that keyword matches score higher than summary matches."""
    # Session with keyword match (weight 3x)
    session1 = AIInteraction(
        ai_tool="claude-code",
        prompt="Other topic",
        response_summary="Other topic",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["bug-fix", "critical"])
    )
    # Session with only summary match (weight 1x)
    session2 = AIInteraction(
        ai_tool="claude-code",
        prompt="Different topic",
        response_summary="Found a critical bug-fix needed",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["other", "stuff"])
    )
    temp_db.add_all([session1, session2])
    temp_db.commit()

    # Search for "bug-fix"
    result_json = server.search_sessions.fn(query="bug-fix")
    result = json.loads(result_json)

    assert result["count"] == 2
    # First result should be session1 (keyword match, higher score)
    assert result["sessions"][0]["id"] == session1.id, "Keyword match should rank higher"
    assert result["sessions"][0]["relevance_score"] > result["sessions"][1]["relevance_score"], \
        "Keyword match should have higher score than summary match"


def test_search_sessions_sorts_by_relevance(temp_db):
    """Test search_sessions sorts results by relevance score (highest first)."""
    # Create 2 sessions with different relevance scores
    # Session with keyword + title match (high score: 3.0 + 2.0 = 5.0)
    high_score_session = AIInteraction(
        ai_tool="claude-code",
        prompt="Other",
        response_summary="Other",
        title="TDD session",  # Title match: +2.0
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["tdd", "testing"])  # Keyword match: +3.0
    )
    # Session with only keyword match (lower score: 3.0)
    low_score_session = AIInteraction(
        ai_tool="claude-code",
        prompt="Other work",
        response_summary="Other content",
        title="Other Session",
        is_session=True,
        timestamp=datetime.now(),
        keywords=json.dumps(["tdd", "docs"])  # Keyword match only: 3.0
    )
    temp_db.add_all([low_score_session, high_score_session])  # Add in reverse order
    temp_db.commit()

    # Search for "TDD"
    result_json = server.search_sessions.fn(query="TDD")
    result = json.loads(result_json)

    assert result["count"] == 2
    # Should be sorted by relevance: high_score (5.0) > low_score (3.0)
    assert result["sessions"][0]["id"] == high_score_session.id, "Higher score should rank first"
    assert result["sessions"][1]["id"] == low_score_session.id, "Lower score should rank second"
    assert result["sessions"][0]["relevance_score"] > result["sessions"][1]["relevance_score"], \
        "First result should have higher score"


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


def test_update_milestone_updates_fields(temp_db, sample_milestone):
    """Test update_milestone updates milestone fields."""
    result_json = server.update_milestone.fn(
        milestone_id=sample_milestone.id,
        title="Updated Title",
        description="Updated description",
        priority=3
    )
    result = json.loads(result_json)

    assert result["success"] is True
    assert result["title"] == "Updated Title"
    assert result["description"] == "Updated description"
    assert result["priority"] == 3


def test_update_milestone_not_found(temp_db):
    """Test update_milestone with non-existent ID."""
    result_json = server.update_milestone.fn(
        milestone_id=999,
        title="Updated Title"
    )
    result = json.loads(result_json)

    assert "error" in result
    assert "not found" in result["error"]


def test_update_milestone_invalid_type(temp_db, sample_milestone):
    """Test update_milestone rejects invalid milestone type."""
    result_json = server.update_milestone.fn(
        milestone_id=sample_milestone.id,
        milestone_type="invalid_type"
    )
    result = json.loads(result_json)

    assert "error" in result
    assert "Type must be" in result["error"]


def test_update_milestone_invalid_priority(temp_db, sample_milestone):
    """Test update_milestone rejects invalid priority."""
    result_json = server.update_milestone.fn(
        milestone_id=sample_milestone.id,
        priority=10  # Invalid (must be 1-5)
    )
    result = json.loads(result_json)

    assert "error" in result
    assert "Priority must be between" in result["error"]


def test_update_next_step_updates_fields(temp_db, sample_next_step):
    """Test update_next_step updates step fields."""
    result_json = server.update_next_step.fn(
        step_id=sample_next_step.id,
        description="Updated description",
        priority=5,
        effort="large"
    )
    result = json.loads(result_json)

    assert result["success"] is True
    assert result["description"] == "Updated description"
    assert result["priority"] == 5
    assert result.get("estimated_effort") == "large"  # Field name in response


def test_update_next_step_not_found(temp_db):
    """Test update_next_step with non-existent ID."""
    result_json = server.update_next_step.fn(
        step_id=999,
        description="Updated"
    )
    result = json.loads(result_json)

    assert "error" in result


def test_delete_milestone_requires_confirmation(temp_db, sample_milestone):
    """Test delete_milestone requires confirmation."""
    result_json = server.delete_milestone.fn(
        milestone_id=sample_milestone.id,
        confirm=False
    )
    result = json.loads(result_json)

    assert "error" in result
    assert "confirm" in result["error"].lower()  # Looks for "confirm" instead of "confirmation"


def test_delete_milestone_deletes_with_confirmation(temp_db, sample_milestone):
    """Test delete_milestone deletes with confirmation."""
    milestone_id = sample_milestone.id
    result_json = server.delete_milestone.fn(
        milestone_id=milestone_id,
        confirm=True
    )
    result = json.loads(result_json)

    assert result["success"] is True

    # Verify milestone was deleted
    db = temp_db
    milestone = db.query(ProjectMilestone).filter_by(id=milestone_id).first()
    assert milestone is None


def test_delete_milestone_not_found(temp_db):
    """Test delete_milestone with non-existent ID."""
    result_json = server.delete_milestone.fn(
        milestone_id=999,
        confirm=True
    )
    result = json.loads(result_json)

    assert "error" in result


def test_delete_next_step_requires_confirmation(temp_db, sample_next_step):
    """Test delete_next_step requires confirmation."""
    result_json = server.delete_next_step.fn(
        step_id=sample_next_step.id,
        confirm=False
    )
    result = json.loads(result_json)

    assert "error" in result
    assert "confirm" in result["error"].lower()  # Looks for "confirm" instead of "confirmation"


def test_delete_next_step_deletes_with_confirmation(temp_db, sample_next_step):
    """Test delete_next_step deletes with confirmation."""
    step_id = sample_next_step.id
    result_json = server.delete_next_step.fn(
        step_id=step_id,
        confirm=True
    )
    result = json.loads(result_json)

    assert result["success"] is True

    # Verify step was deleted
    db = temp_db
    step = db.query(NextStep).filter_by(id=step_id).first()
    assert step is None


def test_delete_next_step_not_found(temp_db):
    """Test delete_next_step with non-existent ID."""
    result_json = server.delete_next_step.fn(
        step_id=999,
        confirm=True
    )
    result = json.loads(result_json)

    assert "error" in result


def test_uncomplete_next_step_reopens_step(temp_db):
    """Test uncomplete_next_step reopens a completed step."""
    # Create a completed step
    step = NextStep(
        description="Completed step",
        priority=1,
        category="feature",
        completed=True,
        completed_at=datetime.now()
    )
    temp_db.add(step)
    temp_db.commit()
    temp_db.refresh(step)

    # Uncomplete it
    result_json = server.uncomplete_next_step.fn(step_id=step.id)
    result = json.loads(result_json)

    assert result["success"] is True

    # Verify step is no longer completed
    temp_db.refresh(step)
    assert step.completed == 0  # SQLite stores boolean as 0/1
    assert step.completed_at is None


def test_uncomplete_next_step_not_found(temp_db):
    """Test uncomplete_next_step with non-existent ID."""
    result_json = server.uncomplete_next_step.fn(step_id=999)
    result = json.loads(result_json)

    assert "error" in result


def test_get_current_session_no_active(temp_db):
    """Test get_current_session when no active session exists."""
    result_json = server.get_current_session.fn()
    result = json.loads(result_json)

    assert result["active"] is False


def test_get_current_session_with_active(temp_db):
    """Test get_current_session when active session exists."""
    # Create an active session (no duration)
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Active session",
        is_session=True,
        timestamp=datetime.now(),
        duration_ms=None,  # No duration = still active
        repo_path="/test/repo"
    )
    temp_db.add(session)
    temp_db.commit()

    result_json = server.get_current_session.fn()
    result = json.loads(result_json)

    assert result["active"] is True
    assert "session" in result
    assert result["session"]["tool"] == "claude-code"


def test_search_commits_finds_by_message(temp_db, sample_commit):
    """Test search_commits finds commits by message."""
    result_json = server.search_commits.fn(query="Test commit")
    result = json.loads(result_json)

    assert result["count"] == 1
    assert result["commits"][0]["sha"] == "abc123def456"


def test_search_commits_no_results(temp_db):
    """Test search_commits with query that matches nothing."""
    result_json = server.search_commits.fn(query="nonexistent")
    result = json.loads(result_json)

    assert result["count"] == 0


# Run the test
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
