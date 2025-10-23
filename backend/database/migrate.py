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


if __name__ == "__main__":
    print("Running all migrations...")
    migrate_v1_to_v2()
    migrate_v2_to_v3()
    migrate_v3_to_v4()
