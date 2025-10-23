"""Tests for project tracking (milestones and next steps)."""

import os
import tempfile
from datetime import datetime
import pytest

from backend.database.models import init_db, ProjectMilestone, NextStep, AIInteraction


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


def test_create_milestone(temp_db):
    """Test creating a project milestone."""
    milestone = ProjectMilestone(
        title="Test Feature",
        description="A test feature description",
        milestone_type="feature",
        priority=1,
        status="planned"
    )
    milestone.tags_list = ["test", "phase-5"]

    temp_db.add(milestone)
    temp_db.commit()

    # Verify milestone was created
    result = temp_db.query(ProjectMilestone).first()
    assert result.title == "Test Feature"
    assert result.status == "planned"
    assert result.priority == 1
    assert result.tags_list == ["test", "phase-5"]


def test_milestone_status_transition(temp_db):
    """Test transitioning milestone status."""
    milestone = ProjectMilestone(
        title="Test Feature",
        milestone_type="feature",
        status="planned"
    )

    temp_db.add(milestone)
    temp_db.commit()

    # Update to in_progress
    milestone.status = "in_progress"
    temp_db.commit()

    assert milestone.status == "in_progress"

    # Complete milestone
    milestone.status = "completed"
    milestone.completed_at = datetime.now()
    temp_db.commit()

    assert milestone.status == "completed"
    assert milestone.completed_at is not None


def test_link_session_to_milestone(temp_db):
    """Test linking a session to a milestone."""
    # Create milestone
    milestone = ProjectMilestone(
        title="Test Feature",
        milestone_type="feature",
        status="in_progress"
    )
    temp_db.add(milestone)
    temp_db.commit()

    # Create a mock session
    session = AIInteraction(
        ai_tool="claude-code",
        prompt="Working on test feature",
        is_session=1,
        timestamp=datetime.now()
    )
    temp_db.add(session)
    temp_db.commit()

    # Link session to milestone
    milestone.sessions_list = [session.id]
    temp_db.commit()

    # Verify link
    result = temp_db.query(ProjectMilestone).first()
    assert session.id in result.sessions_list


def test_create_next_step(temp_db):
    """Test creating a next step."""
    step = NextStep(
        description="Implement API endpoint",
        priority=1,
        estimated_effort="medium",
        category="feature",
        created_by="manual"
    )

    temp_db.add(step)
    temp_db.commit()

    result = temp_db.query(NextStep).first()
    assert result.description == "Implement API endpoint"
    assert result.priority == 1
    assert result.estimated_effort == "medium"
    assert result.completed == 0


def test_complete_next_step(temp_db):
    """Test marking a next step as completed."""
    step = NextStep(
        description="Write tests",
        priority=2,
        category="feature"
    )

    temp_db.add(step)
    temp_db.commit()

    # Mark as completed
    step.completed = 1
    step.completed_at = datetime.now()
    temp_db.commit()

    result = temp_db.query(NextStep).first()
    assert result.completed == 1
    assert result.completed_at is not None


def test_link_next_step_to_milestone(temp_db):
    """Test linking a next step to a milestone."""
    # Create milestone
    milestone = ProjectMilestone(
        title="Test Feature",
        milestone_type="feature"
    )
    temp_db.add(milestone)
    temp_db.commit()

    # Create next step linked to milestone
    step = NextStep(
        description="Design database schema",
        priority=1,
        related_milestone_id=milestone.id
    )
    temp_db.add(step)
    temp_db.commit()

    # Verify link
    result = temp_db.query(NextStep).first()
    assert result.related_milestone_id == milestone.id


def test_query_milestones_by_status(temp_db):
    """Test querying milestones by status."""
    # Create multiple milestones
    m1 = ProjectMilestone(title="Feature 1", status="planned", milestone_type="feature")
    m2 = ProjectMilestone(title="Feature 2", status="in_progress", milestone_type="feature")
    m3 = ProjectMilestone(title="Feature 3", status="completed", milestone_type="feature")

    temp_db.add_all([m1, m2, m3])
    temp_db.commit()

    # Query by status
    planned = temp_db.query(ProjectMilestone).filter_by(status="planned").all()
    in_progress = temp_db.query(ProjectMilestone).filter_by(status="in_progress").all()
    completed = temp_db.query(ProjectMilestone).filter_by(status="completed").all()

    assert len(planned) == 1
    assert len(in_progress) == 1
    assert len(completed) == 1


def test_query_next_steps_by_completion(temp_db):
    """Test querying next steps by completion status."""
    # Create multiple next steps
    s1 = NextStep(description="Task 1", completed=0)
    s2 = NextStep(description="Task 2", completed=0)
    s3 = NextStep(description="Task 3", completed=1, completed_at=datetime.now())

    temp_db.add_all([s1, s2, s3])
    temp_db.commit()

    # Query by completion
    pending = temp_db.query(NextStep).filter_by(completed=0).all()
    completed = temp_db.query(NextStep).filter_by(completed=1).all()

    assert len(pending) == 2
    assert len(completed) == 1


def test_milestone_with_multiple_sessions(temp_db):
    """Test milestone linked to multiple sessions."""
    # Create milestone
    milestone = ProjectMilestone(
        title="Multi-session feature",
        milestone_type="feature"
    )
    temp_db.add(milestone)
    temp_db.commit()

    # Create multiple sessions
    session1 = AIInteraction(ai_tool="claude-code", prompt="Session 1", is_session=1, timestamp=datetime.now())
    session2 = AIInteraction(ai_tool="claude-code", prompt="Session 2", is_session=1, timestamp=datetime.now())

    temp_db.add_all([session1, session2])
    temp_db.commit()

    # Link both sessions
    milestone.sessions_list = [session1.id, session2.id]
    temp_db.commit()

    # Verify
    result = temp_db.query(ProjectMilestone).first()
    assert len(result.sessions_list) == 2
    assert session1.id in result.sessions_list
    assert session2.id in result.sessions_list
