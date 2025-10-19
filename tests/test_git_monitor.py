"""Tests for git monitoring service."""

import os
import tempfile
from datetime import datetime
import pytest
from git import Repo

from backend.database.models import init_db, Commit
from backend.services.git_monitor import GitMonitor


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


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)

        # Create initial commit
        test_file = os.path.join(tmpdir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('initial content')

        repo.index.add(['test.txt'])
        repo.index.commit('Initial commit')

        # Create second commit
        with open(test_file, 'w') as f:
            f.write('updated content')

        repo.index.add(['test.txt'])
        repo.index.commit('Update test file')

        yield tmpdir


def test_scan_repo(temp_db, temp_git_repo):
    """Test scanning a git repository."""
    monitor = GitMonitor(temp_db)

    commits = monitor.scan_repo(temp_git_repo, limit=10)

    assert len(commits) == 2
    assert commits[0].message == 'Update test file'
    assert commits[1].message == 'Initial commit'


def test_get_latest_commit(temp_db, temp_git_repo):
    """Test getting the latest commit."""
    monitor = GitMonitor(temp_db)

    # Scan first
    monitor.scan_repo(temp_git_repo, limit=10)

    # Get latest
    latest = monitor.get_latest_commit(temp_git_repo)

    assert latest is not None
    assert latest.message == 'Update test file'


def test_scan_duplicate_commits(temp_db, temp_git_repo):
    """Test that scanning twice doesn't create duplicates."""
    monitor = GitMonitor(temp_db)

    # First scan
    commits1 = monitor.scan_repo(temp_git_repo, limit=10)
    assert len(commits1) == 2

    # Second scan
    commits2 = monitor.scan_repo(temp_git_repo, limit=10)
    assert len(commits2) == 0  # No new commits

    # Verify database still has 2 commits
    all_commits = temp_db.query(Commit).all()
    assert len(all_commits) == 2


def test_search_commits(temp_db, temp_git_repo):
    """Test searching commits by message."""
    monitor = GitMonitor(temp_db)

    # Scan first
    monitor.scan_repo(temp_git_repo, limit=10)

    # Search
    results = monitor.search_commits('Update')
    assert len(results) == 1
    assert 'Update' in results[0].message

    # Search with no results
    results = monitor.search_commits('nonexistent')
    assert len(results) == 0


def test_get_commits_by_date(temp_db, temp_git_repo):
    """Test getting commits by date range."""
    monitor = GitMonitor(temp_db)

    # Scan first
    monitor.scan_repo(temp_git_repo, limit=10)

    # Get all commits from today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    commits = monitor.get_commits_by_date(today_start)

    assert len(commits) == 2


def test_repo_stats(temp_db, temp_git_repo):
    """Test repository statistics."""
    monitor = GitMonitor(temp_db)

    # Scan first
    monitor.scan_repo(temp_git_repo, limit=10)

    # Get stats
    stats = monitor.get_repo_stats(temp_git_repo)

    assert stats['total_commits'] == 2
    assert len(stats['authors']) > 0
    assert stats['latest_commit'] is not None
    assert stats['latest_commit'].message == 'Update test file'


def test_invalid_repo_path(temp_db):
    """Test error handling for invalid repository path."""
    monitor = GitMonitor(temp_db)

    with pytest.raises(ValueError, match="does not exist"):
        monitor.scan_repo('/nonexistent/path')


def test_non_git_directory(temp_db):
    """Test error handling for non-git directory."""
    monitor = GitMonitor(temp_db)

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Not a valid git repository"):
            monitor.scan_repo(tmpdir)
