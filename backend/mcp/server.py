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
from sqlalchemy.orm import Session, defer

from backend.database.models import (
    init_db,
    AIInteraction,
    Commit,
    DailySummary,
    SessionSummaryChunk,
    ProjectMilestone,
    NextStep,
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
    query = db.query(AIInteraction).options(
        defer(AIInteraction.session_transcript)  # Don't load transcript (can be huge)
    ).filter(AIInteraction.is_session == 1)

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
    session = db.query(AIInteraction).options(
        defer(AIInteraction.session_transcript)  # Don't load transcript (can be huge)
    ).filter(AIInteraction.id == session_id).first()

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
    sessions = db.query(AIInteraction).options(
        defer(AIInteraction.session_transcript)  # Don't load transcript
    ).filter(
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
    session_query = db.query(AIInteraction).options(
        defer(AIInteraction.session_transcript)  # Don't load transcript
    ).filter(
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
    sessions = db.query(AIInteraction).options(
        defer(AIInteraction.session_transcript)  # Don't load transcript
    ).filter(
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


# ============================================================================
# PROJECT TRACKING MCP TOOLS (Milestones & Next Steps)
# ============================================================================

def format_milestone_dict(milestone: ProjectMilestone) -> Dict[str, Any]:
    """Convert ProjectMilestone to a clean dictionary for MCP responses."""
    return {
        "id": milestone.id,
        "title": milestone.title,
        "description": milestone.description,
        "status": milestone.status,
        "type": milestone.milestone_type,
        "priority": milestone.priority,
        "created_at": milestone.created_at.isoformat(),
        "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None,
        "tags": milestone.tags_list,
        "related_sessions": milestone.sessions_list,
        "related_commits": milestone.commits_list,
    }


def format_next_step_dict(step: NextStep) -> Dict[str, Any]:
    """Convert NextStep to a clean dictionary for MCP responses."""
    return {
        "id": step.id,
        "description": step.description,
        "priority": step.priority,
        "estimated_effort": step.estimated_effort,
        "category": step.category,
        "created_by": step.created_by,
        "completed": bool(step.completed),
        "created_at": step.created_at.isoformat(),
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        "related_milestone_id": step.related_milestone_id,
    }


@mcp.tool()
def get_milestones(
    status: Optional[str] = None,
    milestone_type: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Get project milestones.

    Args:
        status: Filter by status (planned, in_progress, completed, archived)
        milestone_type: Filter by type (feature, bugfix, optimization, documentation)
        limit: Maximum number of milestones to return (default: 20, max: 100)

    Returns:
        JSON string with list of milestones
    """
    db = get_db()
    query = db.query(ProjectMilestone)

    if status:
        query = query.filter(ProjectMilestone.status == status)

    if milestone_type:
        query = query.filter(ProjectMilestone.milestone_type == milestone_type)

    limit = min(limit, 100)
    milestones = query.order_by(
        ProjectMilestone.completed_at.desc().nullsfirst(),
        desc(ProjectMilestone.priority),
        ProjectMilestone.created_at.desc()
    ).limit(limit).all()

    result = {
        "count": len(milestones),
        "milestones": [format_milestone_dict(m) for m in milestones]
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_milestone(milestone_id: int) -> str:
    """Get detailed information about a specific milestone.

    Args:
        milestone_id: The milestone ID

    Returns:
        JSON string with milestone details including linked sessions and commits
    """
    db = get_db()
    milestone = db.query(ProjectMilestone).filter_by(id=milestone_id).first()

    if not milestone:
        return json.dumps({"error": f"Milestone #{milestone_id} not found"}, indent=2)

    # Get linked sessions
    linked_sessions = []
    if milestone.sessions_list:
        sessions = db.query(AIInteraction).options(
            defer(AIInteraction.session_transcript)  # Don't load transcript
        ).filter(
            AIInteraction.id.in_(milestone.sessions_list)
        ).all()
        linked_sessions = [format_session_dict(s) for s in sessions]

    # Get linked commits
    linked_commits = []
    if milestone.commits_list:
        commits = db.query(Commit).filter(
            Commit.sha.in_(milestone.commits_list)
        ).all()
        linked_commits = [format_commit_dict(c) for c in commits]

    result = format_milestone_dict(milestone)
    result["linked_sessions"] = linked_sessions
    result["linked_commits"] = linked_commits

    return json.dumps(result, indent=2)


@mcp.tool()
def get_next_steps(
    completed: Optional[bool] = None,
    milestone_id: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Get next steps / TODO items.

    Args:
        completed: Filter by completion status (True = completed, False = pending, None = all)
        milestone_id: Filter by related milestone ID
        limit: Maximum number of items to return (default: 20, max: 100)

    Returns:
        JSON string with list of next steps
    """
    db = get_db()
    query = db.query(NextStep)

    if completed is not None:
        query = query.filter(NextStep.completed == (1 if completed else 0))

    if milestone_id:
        query = query.filter(NextStep.related_milestone_id == milestone_id)

    limit = min(limit, 100)
    steps = query.order_by(
        NextStep.completed,
        desc(NextStep.priority),
        NextStep.created_at.desc()
    ).limit(limit).all()

    result = {
        "count": len(steps),
        "next_steps": [format_next_step_dict(s) for s in steps]
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_roadmap(days: int = 7) -> str:
    """Get project roadmap showing current progress and planned work.

    Args:
        days: Number of days to look back for recent completions (default: 7)

    Returns:
        JSON string with roadmap summary
    """
    db = get_db()

    # In progress milestones
    in_progress = db.query(ProjectMilestone).filter_by(status='in_progress').all()

    # Recent completions
    cutoff = datetime.now() - timedelta(days=days)
    completed = db.query(ProjectMilestone).filter(
        ProjectMilestone.status == 'completed',
        ProjectMilestone.completed_at >= cutoff
    ).order_by(ProjectMilestone.completed_at.desc()).limit(10).all()

    # Planned (high priority)
    planned = db.query(ProjectMilestone).filter_by(status='planned').order_by(
        ProjectMilestone.priority
    ).limit(10).all()

    # Pending next steps
    pending_steps = db.query(NextStep).filter_by(completed=0).order_by(
        NextStep.priority
    ).limit(10).all()

    # Stats
    total_milestones = db.query(ProjectMilestone).count()
    total_completed = db.query(ProjectMilestone).filter_by(status='completed').count()
    total_steps = db.query(NextStep).count()
    completed_steps = db.query(NextStep).filter_by(completed=1).count()

    result = {
        "summary": {
            "total_milestones": total_milestones,
            "completed_milestones": total_completed,
            "total_next_steps": total_steps,
            "completed_next_steps": completed_steps,
        },
        "in_progress": [format_milestone_dict(m) for m in in_progress],
        "recently_completed": [format_milestone_dict(m) for m in completed],
        "planned_high_priority": [format_milestone_dict(m) for m in planned],
        "pending_next_steps": [format_next_step_dict(s) for s in pending_steps],
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def update_milestone_status(milestone_id: int, new_status: str) -> str:
    """Update the status of a milestone.

    Args:
        milestone_id: The milestone ID
        new_status: New status (planned, in_progress, completed, archived)

    Returns:
        JSON string with update result
    """
    db = get_db()
    milestone = db.query(ProjectMilestone).filter_by(id=milestone_id).first()

    if not milestone:
        return json.dumps({"error": f"Milestone #{milestone_id} not found"}, indent=2)

    valid_statuses = ['planned', 'in_progress', 'completed', 'archived']
    if new_status not in valid_statuses:
        return json.dumps({
            "error": f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
        }, indent=2)

    old_status = milestone.status
    milestone.status = new_status

    if new_status == 'completed' and not milestone.completed_at:
        milestone.completed_at = datetime.now()

    db.commit()

    result = {
        "success": True,
        "milestone_id": milestone_id,
        "title": milestone.title,
        "old_status": old_status,
        "new_status": new_status,
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def complete_next_step(step_id: int) -> str:
    """Mark a next step as completed.

    Args:
        step_id: The next step ID

    Returns:
        JSON string with update result
    """
    db = get_db()
    step = db.query(NextStep).filter_by(id=step_id).first()

    if not step:
        return json.dumps({"error": f"Next step #{step_id} not found"}, indent=2)

    step.completed = 1
    step.completed_at = datetime.now()
    db.commit()

    result = {
        "success": True,
        "step_id": step_id,
        "description": step.description,
        "completed_at": step.completed_at.isoformat(),
    }

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
