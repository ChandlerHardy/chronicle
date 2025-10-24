"""Database migration utilities."""

import sqlite3
from pathlib import Path


def migrate_v1_to_v2(db_path: str = None):
    """Migrate database from v1 (Phase 1) to v2 (Phase 2 with sessions).

    Adds session support columns to ai_interactions table.
    """
    if db_path is None:
        home = Path.home()
        db_path = home / ".ai-session" / "sessions.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(ai_interactions)")
    columns = [row[1] for row in cursor.fetchall()]

    migrations_needed = []

    if 'is_session' not in columns:
        migrations_needed.append(
            "ALTER TABLE ai_interactions ADD COLUMN is_session INTEGER DEFAULT 0"
        )

    if 'session_transcript' not in columns:
        migrations_needed.append(
            "ALTER TABLE ai_interactions ADD COLUMN session_transcript TEXT"
        )

    if 'summary_generated' not in columns:
        migrations_needed.append(
            "ALTER TABLE ai_interactions ADD COLUMN summary_generated INTEGER DEFAULT 0"
        )

    if not migrations_needed:
        print("✅ Database is up to date")
        conn.close()
        return

    print(f"📝 Running {len(migrations_needed)} migrations...")

    for migration in migrations_needed:
        print(f"  - {migration.split('ADD COLUMN')[1].split()[0] if 'ADD COLUMN' in migration else 'unknown'}")
        cursor.execute(migration)

    conn.commit()
    conn.close()

    print("✅ Migration complete!")


def migrate_v2_to_v3(db_path: str = None):
    """Migrate database from v2 to v3 (add repo tracking).

    Adds working_directory and repo_path columns to ai_interactions table.
    """
    if db_path is None:
        home = Path.home()
        db_path = home / ".ai-session" / "sessions.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(ai_interactions)")
    columns = [row[1] for row in cursor.fetchall()]

    migrations_needed = []

    if 'working_directory' not in columns:
        migrations_needed.append(
            "ALTER TABLE ai_interactions ADD COLUMN working_directory TEXT"
        )

    if 'repo_path' not in columns:
        migrations_needed.append(
            "ALTER TABLE ai_interactions ADD COLUMN repo_path TEXT"
        )

    if not migrations_needed:
        print("✅ Database is already at v3")
        conn.close()
        return

    print(f"📝 Running {len(migrations_needed)} migrations to v3...")

    for migration in migrations_needed:
        print(f"  - {migration.split('ADD COLUMN')[1].split()[0] if 'ADD COLUMN' in migration else 'unknown'}")
        cursor.execute(migration)

    conn.commit()
    conn.close()

    print("✅ Migration to v3 complete!")


def migrate_v3_to_v4(db_path: str = None):
    """Migrate database from v3 to v4 (add project tracking).

    Adds project_milestones and next_steps tables for meta-development tracking.
    """
    if db_path is None:
        home = Path.home()
        db_path = home / ".ai-session" / "sessions.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    migrations_needed = []

    if 'project_milestones' not in existing_tables:
        migrations_needed.append("""
            CREATE TABLE project_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'planned',
                milestone_type VARCHAR(50) NOT NULL DEFAULT 'feature',
                priority INTEGER DEFAULT 3,
                completed_at DATETIME,
                related_sessions TEXT,
                related_commits TEXT,
                tags TEXT
            )
        """)
        migrations_needed.append(
            "CREATE INDEX ix_project_milestones_created_at ON project_milestones (created_at)"
        )
        migrations_needed.append(
            "CREATE INDEX ix_project_milestones_status ON project_milestones (status)"
        )

    if 'next_steps' not in existing_tables:
        migrations_needed.append("""
            CREATE TABLE next_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                estimated_effort VARCHAR(50),
                category VARCHAR(50) DEFAULT 'feature',
                created_by VARCHAR(100),
                completed INTEGER DEFAULT 0,
                completed_at DATETIME,
                related_milestone_id INTEGER,
                FOREIGN KEY (related_milestone_id) REFERENCES project_milestones (id)
            )
        """)
        migrations_needed.append(
            "CREATE INDEX ix_next_steps_created_at ON next_steps (created_at)"
        )

    if not migrations_needed:
        print("✅ Database is already at v4")
        conn.close()
        return

    print(f"📝 Running {len(migrations_needed)} migrations to v4 (project tracking)...")

    for migration in migrations_needed:
        if 'CREATE TABLE' in migration:
            table_name = migration.split('CREATE TABLE')[1].split()[0].strip()
            print(f"  - Creating table: {table_name}")
        elif 'CREATE INDEX' in migration:
            index_name = migration.split('CREATE INDEX')[1].split()[0].strip()
            print(f"  - Creating index: {index_name}")
        cursor.execute(migration)

    conn.commit()
    conn.close()

    print("✅ Migration to v4 complete!")
    print("   New tables: project_milestones, next_steps")


def migrate_v4_to_v5(db_path: str = None):
    """Migrate database from v4 to v5 (add Gemini model usage tracking).

    Adds gemini_model_usage table for tracking daily API usage across models.
    """
    if db_path is None:
        home = Path.home()
        db_path = home / ".ai-session" / "sessions.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    migrations_needed = []

    if 'gemini_model_usage' not in existing_tables:
        migrations_needed.append("""
            CREATE TABLE gemini_model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name VARCHAR(100) NOT NULL,
                date DATETIME NOT NULL,
                request_count INTEGER DEFAULT 0,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_input_characters INTEGER DEFAULT 0,
                total_output_characters INTEGER DEFAULT 0,
                updated_at DATETIME
            )
        """)
        migrations_needed.append(
            "CREATE INDEX ix_gemini_model_usage_model_name ON gemini_model_usage (model_name)"
        )
        migrations_needed.append(
            "CREATE INDEX ix_gemini_model_usage_date ON gemini_model_usage (date)"
        )
        migrations_needed.append(
            "CREATE UNIQUE INDEX ix_gemini_model_usage_model_date ON gemini_model_usage (model_name, date)"
        )

    if not migrations_needed:
        print("✅ Database is already at v5")
        conn.close()
        return

    print(f"📝 Running {len(migrations_needed)} migrations to v5 (Gemini usage tracking)...")

    for migration in migrations_needed:
        if 'CREATE TABLE' in migration:
            table_name = migration.split('CREATE TABLE')[1].split()[0].strip()
            print(f"  - Creating table: {table_name}")
        elif 'CREATE INDEX' in migration or 'CREATE UNIQUE INDEX' in migration:
            index_name = migration.split('INDEX')[1].split()[0].strip()
            print(f"  - Creating index: {index_name}")
        cursor.execute(migration)

    conn.commit()
    conn.close()

    print("✅ Migration to v5 complete!")
    print("   New table: gemini_model_usage (tracks API usage by model and date)")


def migrate_v5_to_v6(db_path: str = None):
    """Migrate database from v5 to v6 (move transcripts from database to files).

    NULLs out session_transcript column to free up database space.
    Transcripts are now stored in .cleaned files in ~/.ai-session/sessions/

    This dramatically reduces database size (110MB → ~10MB for 13 sessions).
    """
    if db_path is None:
        home = Path.home()
        db_path = home / ".ai-session" / "sessions.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check current database size
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    size_before = cursor.fetchone()[0]
    size_before_mb = size_before / 1024 / 1024

    # Count sessions with transcripts in database
    cursor.execute("SELECT COUNT(*) FROM ai_interactions WHERE session_transcript IS NOT NULL AND is_session = 1")
    count = cursor.fetchone()[0]

    if count == 0:
        print(f"✅ Database is already at v6 (no transcripts in database)")
        print(f"   Current size: {size_before_mb:.1f} MB")
        conn.close()
        return

    print(f"📝 Migration v5 → v6: Moving transcripts from database to files...")
    print(f"   Database size: {size_before_mb:.1f} MB")
    print(f"   Sessions with transcripts in DB: {count}")

    # NULL out all session transcripts
    cursor.execute("UPDATE ai_interactions SET session_transcript = NULL WHERE is_session = 1")

    # VACUUM to reclaim space
    print(f"   Vacuuming database to reclaim space...")
    cursor.execute("VACUUM")

    conn.commit()

    # Check new size
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    size_after = cursor.fetchone()[0]
    size_after_mb = size_after / 1024 / 1024
    saved_mb = size_before_mb - size_after_mb
    saved_pct = (saved_mb / size_before_mb * 100) if size_before_mb > 0 else 0

    conn.close()

    print(f"✅ Migration to v6 complete!")
    print(f"   New size: {size_after_mb:.1f} MB (saved {saved_mb:.1f} MB, {saved_pct:.1f}% reduction)")
    print(f"   Transcripts now stored in ~/.ai-session/sessions/*.cleaned files")


if __name__ == "__main__":
    print("Running all migrations...")
    migrate_v1_to_v2()
    migrate_v2_to_v3()
    migrate_v3_to_v4()
    migrate_v4_to_v5()
    migrate_v5_to_v6()
