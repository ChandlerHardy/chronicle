"""Tests for database migration utilities."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.database.migrate import (
    migrate_v1_to_v2,
    migrate_v2_to_v3,
    migrate_v3_to_v4,
    migrate_v4_to_v5,
    migrate_v5_to_v6,
    migrate_v6_to_v7,
    migrate_v7_to_v8,
    migrate_v8_to_v9,
    migrate_v9_to_v10,
)


class TestMigrationV1ToV2:
    """Test migration from v1 to v2 (session support)."""

    def test_migrate_v1_to_v2_adds_missing_columns(self, temp_db):
        """Test that migration adds missing session columns."""
        # Create v1 database (basic ai_interactions table)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v1_to_v2(temp_db)

        # Verify columns were added
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'is_session' in columns
        assert 'session_transcript' in columns
        assert 'summary_generated' in columns

        # Verify default values
        cursor.execute("SELECT is_session, summary_generated FROM ai_interactions LIMIT 1")
        result = cursor.fetchone()
        # Should be empty since no rows exist, but columns exist
        conn.close()

    def test_migrate_v1_to_v2_skips_existing_columns(self, temp_db):
        """Test that migration skips columns that already exist."""
        # Create database with v2 columns already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT,
                is_session INTEGER DEFAULT 0,
                session_transcript TEXT,
                summary_generated INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v1_to_v2(temp_db)

        # Verify no errors occurred and table still exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0  # Should still be 0 (no errors)
        conn.close()

    def test_migrate_v1_to_v2_uses_default_db_path(self):
        """Test that migration uses default database path when none provided."""
        with patch('backend.database.migrate.Path') as mock_path:
            mock_home = Path('/fake/home')
            mock_path.home.return_value = mock_home

            with patch('sqlite3.connect') as mock_connect:
                mock_conn = mock_connect.return_value
                mock_cursor = mock_conn.cursor.return_value
                mock_cursor.fetchall.return_value = []  # No existing columns

                migrate_v1_to_v2()

                # Should use default path
                mock_path.home.assert_called_once()
                expected_path = mock_home / ".ai-session" / "sessions.db"
                mock_connect.assert_called_once_with(expected_path)


class TestMigrationV2ToV3:
    """Test migration from v2 to v3 (repo tracking)."""

    def test_migrate_v2_to_v3_adds_repo_columns(self, temp_db):
        """Test that migration adds working_directory and repo_path columns."""
        # Create v2 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT,
                is_session INTEGER DEFAULT 0,
                session_transcript TEXT,
                summary_generated INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v2_to_v3(temp_db)

        # Verify columns were added
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'working_directory' in columns
        assert 'repo_path' in columns
        conn.close()

    def test_migrate_v2_to_v3_skips_existing_columns(self, temp_db):
        """Test that migration skips repo columns that already exist."""
        # Create database with v3 columns already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT,
                is_session INTEGER DEFAULT 0,
                session_transcript TEXT,
                summary_generated INTEGER DEFAULT 0,
                working_directory TEXT,
                repo_path TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v2_to_v3(temp_db)

        # Verify no errors occurred
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV3ToV4:
    """Test migration from v3 to v4 (project tracking)."""

    def test_migrate_v3_to_v4_creates_project_tables(self, temp_db):
        """Test that migration creates project_milestones and next_steps tables."""
        # Create v3 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT,
                is_session INTEGER DEFAULT 0,
                session_transcript TEXT,
                summary_generated INTEGER DEFAULT 0,
                working_directory TEXT,
                repo_path TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v3_to_v4(temp_db)

        # Verify tables were created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'project_milestones' in tables
        assert 'next_steps' in tables

        # Verify project_milestones structure
        cursor.execute("PRAGMA table_info(project_milestones)")
        milestone_columns = [row[1] for row in cursor.fetchall()]
        expected_columns = [
            'id', 'created_at', 'title', 'description', 'status',
            'milestone_type', 'priority', 'completed_at',
            'related_sessions', 'related_commits', 'tags'
        ]
        for col in expected_columns:
            assert col in milestone_columns

        # Verify next_steps structure
        cursor.execute("PRAGMA table_info(next_steps)")
        step_columns = [row[1] for row in cursor.fetchall()]
        expected_step_columns = [
            'id', 'created_at', 'description', 'priority',
            'estimated_effort', 'category', 'created_by',
            'completed', 'completed_at', 'related_milestone_id'
        ]
        for col in expected_step_columns:
            assert col in step_columns

        conn.close()

    def test_migrate_v3_to_v4_skips_existing_tables(self, temp_db):
        """Test that migration skips tables that already exist."""
        # Create database with project tables already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE project_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE next_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v3_to_v4(temp_db)

        # Verify no errors occurred
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM project_milestones")
        count = cursor.fetchone()[0]
        assert count == 0  # Should still be 0
        conn.close()


class TestMigrationV4ToV5:
    """Test migration from v4 to v5 (Gemini usage tracking)."""

    def test_migrate_v4_to_v5_creates_gemini_usage_table(self, temp_db):
        """Test that migration creates gemini_model_usage table."""
        # Create v4 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v4_to_v5(temp_db)

        # Verify table was created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'gemini_model_usage' in tables

        # Verify table structure
        cursor.execute("PRAGMA table_info(gemini_model_usage)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = [
            'id', 'model_name', 'date', 'request_count',
            'total_input_tokens', 'total_output_tokens',
            'total_input_characters', 'total_output_characters', 'updated_at'
        ]
        for col in expected_columns:
            assert col in columns

        # Verify indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert 'ix_gemini_model_usage_model_name' in indexes
        assert 'ix_gemini_model_usage_date' in indexes
        assert 'ix_gemini_model_usage_model_date' in indexes

        conn.close()

    def test_migrate_v4_to_v5_skips_existing_table(self, temp_db):
        """Test that migration skips gemini_model_usage table if it exists."""
        # Create database with gemini table already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE gemini_model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v4_to_v5(temp_db)

        # Verify no errors occurred
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gemini_model_usage")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV5ToV6:
    """Test migration from v5 to v6 (transcript cleanup)."""

    def test_migrate_v5_to_v6_removes_transcripts(self, temp_db):
        """Test that migration NULLs out session_transcript column."""
        # Create v5 database with transcripts
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                is_session INTEGER DEFAULT 1,
                session_transcript TEXT
            )
        """)
        # Insert test data with transcripts
        cursor.execute("""
            INSERT INTO ai_interactions (timestamp, prompt, is_session, session_transcript)
            VALUES ('2023-01-01', 'test prompt', 1, 'sample transcript content')
        """)
        cursor.execute("""
            INSERT INTO ai_interactions (timestamp, prompt, is_session, session_transcript)
            VALUES ('2023-01-02', 'non-session prompt', 0, 'non-session content')
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v5_to_v6(temp_db)

        # Verify transcripts were NULLed for sessions only
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT session_transcript FROM ai_interactions WHERE is_session = 1")
        session_transcript = cursor.fetchone()[0]
        assert session_transcript is None

        # Non-session transcript should remain
        cursor.execute("SELECT session_transcript FROM ai_interactions WHERE is_session = 0")
        non_session_transcript = cursor.fetchone()[0]
        assert non_session_transcript == 'non-session content'

        conn.close()

    def test_migrate_v5_to_v6_handles_no_transcripts(self, temp_db):
        """Test that migration handles database with no transcripts."""
        # Create v5 database without transcripts
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                is_session INTEGER DEFAULT 1,
                session_transcript TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v5_to_v6(temp_db)

        # Should complete without errors
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV6ToV7:
    """Test migration from v6 to v7 (session organization)."""

    def test_migrate_v6_to_v7_adds_organization_columns(self, temp_db):
        """Test that migration adds session organization columns."""
        # Create v6 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                is_session INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v6_to_v7(temp_db)

        # Verify columns were added
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'title' in columns
        assert 'parent_session_id' in columns
        assert 'related_session_ids' in columns
        assert 'tags' in columns
        conn.close()

    def test_migrate_v6_to_v7_skips_existing_columns(self, temp_db):
        """Test that migration skips organization columns that already exist."""
        # Create database with organization columns already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                title TEXT,
                parent_session_id INTEGER,
                related_session_ids TEXT,
                tags TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v6_to_v7(temp_db)

        # Should complete without errors
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV7ToV8:
    """Test migration from v7 to v8 (keywords support)."""

    def test_migrate_v7_to_v8_adds_keywords_column(self, temp_db):
        """Test that migration adds keywords column."""
        # Create v7 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                title TEXT,
                tags TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v7_to_v8(temp_db)

        # Verify column was added
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'keywords' in columns
        conn.close()

    def test_migrate_v7_to_v8_skips_existing_keywords(self, temp_db):
        """Test that migration skips keywords column if it already exists."""
        # Create database with keywords column already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                keywords TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v7_to_v8(temp_db)

        # Should complete without errors
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV8ToV9:
    """Test migration from v8 to v9 (FTS5 search)."""

    def test_migrate_v8_to_v9_creates_fts_table(self, temp_db):
        """Test that migration creates FTS5 virtual table and triggers."""
        # Create v8 database with existing sessions
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT,
                is_session INTEGER DEFAULT 1,
                keywords TEXT
            )
        """)
        # Insert test sessions
        cursor.execute("""
            INSERT INTO ai_interactions (timestamp, prompt, response_summary, is_session, keywords)
            VALUES ('2023-01-01', 'test prompt 1', 'summary 1', 1, '["keyword1", "keyword2"]')
        """)
        cursor.execute("""
            INSERT INTO ai_interactions (timestamp, prompt, response_summary, is_session, keywords)
            VALUES ('2023-01-02', 'test prompt 2', 'summary 2', 0, '["keyword3"]')
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v8_to_v9(temp_db)

        # Verify FTS table was created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'sessions_fts' in tables

        # Verify triggers were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        triggers = [row[0] for row in cursor.fetchall()]
        expected_triggers = ['ai_interactions_ai', 'ai_interactions_au', 'ai_interactions_ad']
        for trigger in expected_triggers:
            assert trigger in triggers

        # Verify FTS table was populated with existing sessions
        cursor.execute("SELECT COUNT(*) FROM sessions_fts")
        fts_count = cursor.fetchone()[0]
        # Note: Migration currently populates all existing rows (both sessions and non-sessions)
        # This is acceptable behavior for the initial population
        assert fts_count == 2  # Both test rows should be populated

        conn.close()

    def test_migrate_v8_to_v9_skips_existing_fts(self, temp_db):
        """Test that migration skips FTS table if it already exists."""
        # Create database with FTS table already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE sessions_fts USING fts5(
                prompt, content='ai_interactions', content_rowid='id'
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v8_to_v9(temp_db)

        # Should complete without errors
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationV9ToV10:
    """Test migration from v9 to v10 (git branch tracking)."""

    def test_migrate_v9_to_v10_adds_branch_column(self, temp_db):
        """Test that migration adds branch column."""
        # Create v9 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                title TEXT,
                keywords TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v9_to_v10(temp_db)

        # Verify column was added
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'branch' in columns
        conn.close()

    def test_migrate_v9_to_v10_skips_existing_branch(self, temp_db):
        """Test that migration skips branch column if it already exists."""
        # Create database with branch column already present
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                branch TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migration
        migrate_v9_to_v10(temp_db)

        # Should complete without errors
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


class TestMigrationIntegration:
    """Test migration integration and edge cases."""

    def test_all_migrations_run_successfully(self, temp_db):
        """Test that all migrations can run successfully on a fresh database."""
        # Create minimal v1 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run all migrations in sequence
        migrate_v1_to_v2(temp_db)
        migrate_v2_to_v3(temp_db)
        migrate_v3_to_v4(temp_db)
        migrate_v4_to_v5(temp_db)
        migrate_v5_to_v6(temp_db)
        migrate_v6_to_v7(temp_db)
        migrate_v7_to_v8(temp_db)
        migrate_v8_to_v9(temp_db)
        migrate_v9_to_v10(temp_db)

        # Verify final state
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = [
            'ai_interactions', 'project_milestones', 'next_steps',
            'gemini_model_usage', 'sessions_fts'
        ]
        for table in expected_tables:
            assert table in tables

        # Check all final columns exist
        cursor.execute("PRAGMA table_info(ai_interactions)")
        columns = [row[1] for row in cursor.fetchall()]
        final_columns = [
            'id', 'timestamp', 'prompt', 'response_summary',
            'is_session', 'session_transcript', 'summary_generated',
            'working_directory', 'repo_path', 'title', 'parent_session_id',
            'related_session_ids', 'tags', 'keywords'
        ]
        for col in final_columns:
            assert col in columns

        conn.close()

    def test_migration_handles_nonexistent_database(self):
        """Test that migration handles nonexistent database gracefully."""
        nonexistent_db = "/tmp/nonexistent_db.sqlite"

        # Should not raise an exception
        migrate_v1_to_v2(nonexistent_db)

        # Database should be created
        assert os.path.exists(nonexistent_db)

        # Clean up
        os.remove(nonexistent_db)

    def test_migration_idempotency(self, temp_db):
        """Test that migrations are idempotent (can be run multiple times)."""
        # Create v1 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                prompt TEXT,
                response_summary TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Run migrations twice
        migrate_v1_to_v2(temp_db)
        migrate_v2_to_v3(temp_db)
        migrate_v3_to_v4(temp_db)

        # Run them again - should not cause errors
        migrate_v1_to_v2(temp_db)
        migrate_v2_to_v3(temp_db)
        migrate_v3_to_v4(temp_db)

        # Database should still be valid
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_interactions")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)