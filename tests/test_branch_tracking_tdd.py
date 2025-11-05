"""Test branch tracking functionality using proper TDD approach."""

import pytest
from unittest.mock import Mock, patch
from backend.services.session_manager import SessionManager
from backend.database.models import AIInteraction
from datetime import datetime


class TestBranchTrackingTDD:
    """Branch tracking feature developed using TDD."""

    def test_session_manager_captures_git_branch_when_starting_session(self):
        """SessionManager should capture current git branch when starting a session in a git repo."""
        # Arrange - This test will fail because branch tracking doesn't exist yet

        # Create a SessionManager with mocked database
        mock_db_session = Mock()
        manager = SessionManager(mock_db_session)

        # Mock the current working directory and git operations
        with patch('backend.services.session_manager.os.getcwd', return_value='/path/to/git/repo'), \
             patch('backend.services.session_manager.subprocess.run') as mock_subprocess, \
             patch('backend.services.session_manager.print_chronicle_banner'), \
             patch.object(manager, '_finalize_session'), \
             patch.object(manager, '_find_git_root', return_value='/path/to/git/repo'), \
             patch.object(manager, '_get_current_branch', return_value='main'):

            # Mock git commands: first finds git root, second gets branch
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout='/path/to/git/repo'),  # git rev-parse --show-toplevel
                Mock(returncode=0, stdout='main\n')              # git rev-parse --abbrev-ref HEAD
            ]

            # Act - This should fail because _get_current_branch method doesn't exist
            try:
                session_id = manager.start_session('claude')

                # If we get here, the feature works - verify branch was captured
                # Find the AIInteraction that was created
                created_session = mock_db_session.add.call_args[0][0]
                assert created_session.branch == "main"
                assert created_session.repo_path == "/path/to/git/repo"

            except AttributeError as e:
                # Expected failure - method doesn't exist yet
                assert "_get_current_branch" in str(e)
                pytest.fail(f"Expected _get_current_branch method to exist but got: {e}")

    def test_session_manager_handles_detached_head_state(self):
        """SessionManager should handle detached HEAD state gracefully."""
        mock_db_session = Mock()
        manager = SessionManager(mock_db_session)

        with patch('backend.services.session_manager.os.getcwd', return_value='/path/to/git/repo'), \
             patch('backend.services.session_manager.subprocess.run') as mock_subprocess, \
             patch('backend.services.session_manager.print_chronicle_banner'), \
             patch.object(manager, '_finalize_session'):

            # Mock git commands for detached HEAD
            mock_subprocess.side_effect = [
                Mock(returncode=0, stdout='/path/to/git/repo'),        # git rev-parse --show-toplevel
                Mock(returncode=0, stdout='HEAD\n'),                   # git rev-parse --abbrev-ref HEAD returns HEAD
                Mock(returncode=0, stdout='abc123def\n')               # git rev-parse --short HEAD
            ]

            # This should fail until we implement the feature
            try:
                session_id = manager.start_session('claude')
                created_session = mock_db_session.add.call_args[0][0]
                assert created_session.branch == "detached-HEAD-abc123def"
            except AttributeError:
                pytest.fail("Expected detached HEAD handling to be implemented")

    def test_session_manager_handles_non_git_directory(self):
        """SessionManager should gracefully handle sessions outside git repositories."""
        mock_db_session = Mock()
        manager = SessionManager(mock_db_session)

        with patch('backend.services.session_manager.os.getcwd', return_value='/path/to/non-git'), \
             patch('backend.services.session_manager.subprocess.run') as mock_subprocess, \
             patch('backend.services.session_manager.print_chronicle_banner'), \
             patch.object(manager, '_finalize_session'):

            # Mock git command failure (not in git repo)
            mock_subprocess.return_value = Mock(returncode=1, stderr='fatal: not a git repository')

            try:
                session_id = manager.start_session('claude')
                created_session = mock_db_session.add.call_args[0][0]
                assert created_session.branch is None
                assert created_session.repo_path is None
            except AttributeError:
                pytest.fail("Expected non-git handling to be implemented")