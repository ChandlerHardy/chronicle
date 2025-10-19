"""SQLAlchemy models for AI Session Recorder."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

Base = declarative_base()


class Commit(Base):
    """Git commit tracking."""

    __tablename__ = 'commits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    sha = Column(String(40), nullable=False, index=True)
    message = Column(Text, nullable=False)
    files_changed = Column(Text)  # JSON array
    branch = Column(String(255))
    author = Column(String(255))
    repo_path = Column(String(500), nullable=False, index=True)

    # Relationship to AI interactions
    ai_interactions = relationship("AIInteraction", back_populates="commit")

    def __repr__(self):
        return f"<Commit(sha='{self.sha[:8]}', message='{self.message[:50]}')>"

    @property
    def files_list(self):
        """Get files_changed as a Python list."""
        if self.files_changed:
            return json.loads(self.files_changed)
        return []

    @files_list.setter
    def files_list(self, value):
        """Set files_changed from a Python list."""
        self.files_changed = json.dumps(value)


class AIInteraction(Base):
    """AI tool interaction tracking."""

    __tablename__ = 'ai_interactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    ai_tool = Column(String(50), nullable=False)  # 'claude-code', 'gemini-cli', 'qwen-cli'
    prompt = Column(Text, nullable=False)
    response_summary = Column(Text)  # First 500 chars or AI-generated summary
    files_mentioned = Column(Text)  # JSON array
    duration_ms = Column(Integer)
    related_commit_id = Column(Integer, ForeignKey('commits.id'))

    # Session support
    is_session = Column(Integer, default=0)  # 0 = single interaction, 1 = full session
    session_transcript = Column(Text)  # Full session transcript for interactive sessions
    summary_generated = Column(Integer, default=0)  # 0 = not summarized, 1 = summarized

    # Relationship
    commit = relationship("Commit", back_populates="ai_interactions")

    def __repr__(self):
        return f"<AIInteraction(tool='{self.ai_tool}', prompt='{self.prompt[:30]}...')>"

    @property
    def files_list(self):
        """Get files_mentioned as a Python list."""
        if self.files_mentioned:
            return json.loads(self.files_mentioned)
        return []

    @files_list.setter
    def files_list(self, value):
        """Set files_mentioned from a Python list."""
        self.files_mentioned = json.dumps(value)


class DailySummary(Base):
    """Daily development session summary."""

    __tablename__ = 'daily_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False)
    topics = Column(Text)  # JSON array
    files_affected = Column(Text)  # JSON array
    commits_count = Column(Integer, default=0)
    ai_interactions_count = Column(Integer, default=0)
    key_decisions = Column(Text)  # JSON array

    def __repr__(self):
        return f"<DailySummary(date='{self.date.date()}', commits={self.commits_count})>"

    @property
    def topics_list(self):
        """Get topics as a Python list."""
        if self.topics:
            return json.loads(self.topics)
        return []

    @topics_list.setter
    def topics_list(self, value):
        """Set topics from a Python list."""
        self.topics = json.dumps(value)

    @property
    def files_list(self):
        """Get files_affected as a Python list."""
        if self.files_affected:
            return json.loads(self.files_affected)
        return []

    @files_list.setter
    def files_list(self, value):
        """Set files_affected from a Python list."""
        self.files_affected = json.dumps(value)

    @property
    def decisions_list(self):
        """Get key_decisions as a Python list."""
        if self.key_decisions:
            return json.loads(self.key_decisions)
        return []

    @decisions_list.setter
    def decisions_list(self, value):
        """Set key_decisions from a Python list."""
        self.key_decisions = json.dumps(value)


def init_db(db_path: str = None):
    """Initialize the database and create all tables.

    Args:
        db_path: Path to SQLite database file. Defaults to ~/.ai-session/sessions.db

    Returns:
        Tuple of (engine, SessionLocal)
    """
    if db_path is None:
        import os
        home = os.path.expanduser("~")
        ai_session_dir = os.path.join(home, ".ai-session")
        os.makedirs(ai_session_dir, exist_ok=True)
        db_path = os.path.join(ai_session_dir, "sessions.db")

    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)

    return engine, SessionLocal


def get_session(db_path: str = None):
    """Get a database session.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy session
    """
    _, SessionLocal = init_db(db_path)
    return SessionLocal()
