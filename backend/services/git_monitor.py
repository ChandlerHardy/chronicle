"""Git commit monitoring and tracking service."""

import os
from datetime import datetime
from typing import List, Optional, Dict
from git import Repo, GitCommandError, InvalidGitRepositoryError
from sqlalchemy.orm import Session

from backend.database.models import Commit


class GitMonitor:
    """Monitor git repositories and track commits."""

    def __init__(self, db_session: Session):
        """Initialize git monitor.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def scan_repo(self, repo_path: str, limit: int = 50) -> List[Commit]:
        """Scan a git repository and store recent commits.

        Args:
            repo_path: Path to git repository
            limit: Maximum number of recent commits to scan

        Returns:
            List of Commit objects that were added to database

        Raises:
            ValueError: If path is not a valid git repository
        """
        if not os.path.exists(repo_path):
            raise ValueError(f"Path does not exist: {repo_path}")

        try:
            repo = Repo(repo_path)
        except (GitCommandError, InvalidGitRepositoryError):
            raise ValueError(f"Not a valid git repository: {repo_path}")

        # Get recent commits
        commits_added = []
        for git_commit in list(repo.iter_commits(max_count=limit)):
            # Check if commit already exists
            existing = self.db.query(Commit).filter_by(
                sha=git_commit.hexsha,
                repo_path=repo_path
            ).first()

            if existing:
                continue

            # Get list of files changed
            files_changed = []
            try:
                if git_commit.parents:
                    diff = git_commit.parents[0].diff(git_commit)
                    files_changed = [item.a_path or item.b_path for item in diff]
            except Exception:
                # If we can't get diff (e.g., initial commit), skip it
                pass

            # Create commit record
            commit = Commit(
                timestamp=datetime.fromtimestamp(git_commit.committed_date),
                sha=git_commit.hexsha,
                message=git_commit.message.strip(),
                files_changed=None,
                branch=repo.active_branch.name if repo.active_branch else "unknown",
                author=str(git_commit.author),
                repo_path=os.path.abspath(repo_path)
            )
            commit.files_list = files_changed

            self.db.add(commit)
            commits_added.append(commit)

        self.db.commit()
        return commits_added

    def get_latest_commit(self, repo_path: str) -> Optional[Commit]:
        """Get the most recent commit for a repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Most recent Commit object or None
        """
        return self.db.query(Commit).filter_by(
            repo_path=os.path.abspath(repo_path)
        ).order_by(Commit.timestamp.desc()).first()

    def get_commits_by_date(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        repo_path: Optional[str] = None
    ) -> List[Commit]:
        """Get commits within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (defaults to now)
            repo_path: Optional filter by repository path

        Returns:
            List of Commit objects
        """
        query = self.db.query(Commit).filter(Commit.timestamp >= start_date)

        if end_date:
            query = query.filter(Commit.timestamp <= end_date)

        if repo_path:
            query = query.filter_by(repo_path=os.path.abspath(repo_path))

        return query.order_by(Commit.timestamp.desc()).all()

    def get_commits_today(self, repo_path: Optional[str] = None) -> List[Commit]:
        """Get all commits from today.

        Args:
            repo_path: Optional filter by repository path

        Returns:
            List of Commit objects from today
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_commits_by_date(today_start, repo_path=repo_path)

    def search_commits(self, search_term: str) -> List[Commit]:
        """Search commits by message content.

        Args:
            search_term: Term to search for in commit messages

        Returns:
            List of matching Commit objects
        """
        return self.db.query(Commit).filter(
            Commit.message.contains(search_term)
        ).order_by(Commit.timestamp.desc()).all()

    def get_repo_stats(self, repo_path: str) -> Dict:
        """Get statistics for a repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Dictionary with stats (total_commits, latest_commit, etc.)
        """
        commits = self.db.query(Commit).filter_by(
            repo_path=os.path.abspath(repo_path)
        ).all()

        if not commits:
            return {
                "total_commits": 0,
                "latest_commit": None,
                "authors": []
            }

        authors = list(set(c.author for c in commits))
        latest = max(commits, key=lambda c: c.timestamp)

        return {
            "total_commits": len(commits),
            "latest_commit": latest,
            "authors": authors,
            "repo_path": os.path.abspath(repo_path)
        }
