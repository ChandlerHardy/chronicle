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


if __name__ == "__main__":
    migrate_v1_to_v2()
