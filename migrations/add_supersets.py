#!/usr/bin/env python3
"""
Migration: Add Supersets Support
Date: 2026-01-18
Description: Adds superset_group_id column to workout_exercises table
             to support grouping exercises into supersets
"""

import sqlite3
import sys
import os
import argparse


def get_default_db_path():
    """Find the database path, checking common locations"""
    # Check environment variable first
    if os.environ.get('DATABASE_PATH'):
        return os.environ.get('DATABASE_PATH')

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Common locations to check
    candidates = [
        os.path.join(project_root, 'exercises.db'),  # Project root
        'exercises.db',  # Current directory
        os.path.join(script_dir, '..', 'exercises.db'),  # Relative to migrations/
        '/app/exercises.db',  # Docker/container path
    ]

    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)

    # Default to project root if none found (will be created or error)
    return os.path.join(project_root, 'exercises.db')


def migrate(db_path=None):
    """Run the supersets migration"""
    if db_path is None:
        db_path = get_default_db_path()

    print("=" * 60)
    print("Supersets Migration")
    print("=" * 60)
    print(f"Database: {db_path}")

    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"\n✗ Database file not found: {db_path}")
        print("\nTry specifying the correct path:")
        print("  python add_supersets.py --db-path /path/to/exercises.db")
        print("\nOr set the DATABASE_PATH environment variable:")
        print("  DATABASE_PATH=/path/to/exercises.db python add_supersets.py")
        return 1

    print(f"File size: {os.path.getsize(db_path)} bytes\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Verify the workout_exercises table exists
        print("Verifying database schema...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_exercises'")
        if not cursor.fetchone():
            print("\n✗ Table 'workout_exercises' not found in database.")
            print("This database may not be the correct Gym Manager database.")
            print("\nAvailable tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                print(f"  - {table[0]}")
            return 1
        print("  ✓ Found workout_exercises table")

        # Check if column already exists
        print("\nChecking current schema...")
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'superset_group_id' in columns:
            print("  - Column superset_group_id already exists")
        else:
            print("Adding superset_group_id column...")
            cursor.execute('''
                ALTER TABLE workout_exercises
                ADD COLUMN superset_group_id INTEGER DEFAULT NULL
            ''')
            print("  ✓ Added superset_group_id column")

        # Create index for efficient queries
        print("Creating index...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workout_exercises_superset
            ON workout_exercises(workout_id, superset_group_id)
        ''')
        print("  ✓ Created index on superset_group_id")

        conn.commit()

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        return 1

    finally:
        conn.close()


def rollback(db_path=None):
    """Rollback the migration (remove superset_group_id column)"""
    if db_path is None:
        db_path = get_default_db_path()

    print("=" * 60)
    print("Supersets Migration - ROLLBACK")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    print("Note: SQLite doesn't support DROP COLUMN directly.")
    print("To rollback, you would need to:")
    print("  1. Create a new table without superset_group_id")
    print("  2. Copy data from old table")
    print("  3. Drop old table")
    print("  4. Rename new table")
    print("\nThis is a destructive operation. Manual intervention required.")
    return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run supersets migration')
    parser.add_argument('--db-path', default=None,
                        help='Path to database file (auto-detected if not specified)')
    parser.add_argument('--rollback', action='store_true',
                        help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        sys.exit(rollback(args.db_path))
    else:
        sys.exit(migrate(args.db_path))
