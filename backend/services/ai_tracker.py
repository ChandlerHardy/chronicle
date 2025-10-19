"""AI interaction tracking service."""

import os
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.database.models import AIInteraction, Commit


class AITracker:
    """Track AI tool interactions and link to commits."""

    def __init__(self, db_session: Session):
        """Initialize AI tracker.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def log_interaction(
        self,
        ai_tool: str,
        prompt: str,
        response: str = None,
        duration_ms: int = None,
        files_mentioned: List[str] = None,
    ) -> AIInteraction:
        """Log an AI interaction.

        Args:
            ai_tool: Name of AI tool ('claude-code', 'gemini-cli', 'qwen-cli')
            prompt: The user's prompt/question
            response: The AI's response (optional)
            duration_ms: Duration in milliseconds (optional)
            files_mentioned: List of files mentioned in interaction (optional)

        Returns:
            Created AIInteraction object
        """
        # Create response summary (first 500 chars)
        response_summary = None
        if response:
            response_summary = response[:500] if len(response) > 500 else response

        # Create interaction record
        interaction = AIInteraction(
            timestamp=datetime.now(),
            ai_tool=ai_tool,
            prompt=prompt,
            response_summary=response_summary,
            files_mentioned=None,
            duration_ms=duration_ms,
            related_commit_id=None,
        )

        if files_mentioned:
            interaction.files_list = files_mentioned

        self.db.add(interaction)
        self.db.commit()

        # Try to link to recent commit
        self._link_to_commit(interaction)

        return interaction

    def _link_to_commit(self, interaction: AIInteraction, window_minutes: int = 30):
        """Link an AI interaction to a recent commit if one exists.

        Args:
            interaction: AIInteraction to link
            window_minutes: Time window to search for commits (default: 30 minutes)
        """
        # Look for commits within the time window after the interaction
        start_time = interaction.timestamp
        end_time = start_time + timedelta(minutes=window_minutes)

        recent_commit = (
            self.db.query(Commit)
            .filter(Commit.timestamp >= start_time)
            .filter(Commit.timestamp <= end_time)
            .order_by(Commit.timestamp.asc())
            .first()
        )

        if recent_commit:
            interaction.related_commit_id = recent_commit.id
            self.db.commit()

    def get_interactions_today(self, ai_tool: str = None) -> List[AIInteraction]:
        """Get all AI interactions from today.

        Args:
            ai_tool: Optional filter by AI tool

        Returns:
            List of AIInteraction objects from today
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = self.db.query(AIInteraction).filter(AIInteraction.timestamp >= today_start)

        if ai_tool:
            query = query.filter_by(ai_tool=ai_tool)

        return query.order_by(AIInteraction.timestamp.desc()).all()

    def get_interactions_by_date(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        ai_tool: Optional[str] = None,
    ) -> List[AIInteraction]:
        """Get AI interactions within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (defaults to now)
            ai_tool: Optional filter by AI tool

        Returns:
            List of AIInteraction objects
        """
        query = self.db.query(AIInteraction).filter(AIInteraction.timestamp >= start_date)

        if end_date:
            query = query.filter(AIInteraction.timestamp <= end_date)

        if ai_tool:
            query = query.filter_by(ai_tool=ai_tool)

        return query.order_by(AIInteraction.timestamp.desc()).all()

    def search_interactions(self, search_term: str) -> List[AIInteraction]:
        """Search AI interactions by prompt content.

        Args:
            search_term: Term to search for in prompts

        Returns:
            List of matching AIInteraction objects
        """
        return (
            self.db.query(AIInteraction)
            .filter(AIInteraction.prompt.contains(search_term))
            .order_by(AIInteraction.timestamp.desc())
            .all()
        )

    def get_ai_tool_stats(self, days: int = 30) -> dict:
        """Get statistics on AI tool usage.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            Dictionary with usage stats per AI tool
        """
        start_date = datetime.now() - timedelta(days=days)
        interactions = self.get_interactions_by_date(start_date)

        # Count by tool
        stats = {}
        for interaction in interactions:
            tool = interaction.ai_tool
            if tool not in stats:
                stats[tool] = {"count": 0, "total_duration_ms": 0}

            stats[tool]["count"] += 1
            if interaction.duration_ms:
                stats[tool]["total_duration_ms"] += interaction.duration_ms

        return stats

    def get_interaction_with_commit(self, interaction_id: int) -> tuple:
        """Get an AI interaction and its related commit if any.

        Args:
            interaction_id: ID of the interaction

        Returns:
            Tuple of (AIInteraction, Commit or None)
        """
        interaction = self.db.query(AIInteraction).filter_by(id=interaction_id).first()

        if not interaction:
            return None, None

        commit = None
        if interaction.related_commit_id:
            commit = self.db.query(Commit).filter_by(id=interaction.related_commit_id).first()

        return interaction, commit
