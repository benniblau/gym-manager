#!/usr/bin/env python3
"""
Migration: Add Superset Reps Support
Date: 2026-01-28
Description: Adds superset_target_reps and superset_actual_reps columns to workout_exercises
             to support specifying the number of rounds for supersets
"""

import sqlite3
import sys
import os
import argparse


def get_default_db_path():
    """Find the database path, checking common locations"""
    if os.environ.get('DATABASE_PATH'):
        return os.environ.get('DATABASE_PATH')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    candidates = [
        os.path.join(project_root, 'exercises.db'),
        'exercises.db',
        os.path.join(script_dir, '..', 'exercises.db'),
        '/app/exercises.db',
    ]

    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)

    return os.path.join(project_root, 'exercises.db')


def migrate(db_path=None):
    """Run the superset reps migration"""
    if db_path is None:
        db_path = get_default_db_path()

    print("=" * 60)
    print("Superset Reps Migration")
    print("=" * 60)
    print(f"Database: {db_path}")

    if not os.path.exists(db_path):
        print(f"\n[ERROR] Database file not found: {db_path}")
        return 1

    print(f"File size: {os.path.getsize(db_path)} bytes\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Verify the workout_exercises table exists
        print("Verifying database schema...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_exercises'")
        if not cursor.fetchone():
            print("\n[ERROR] Table 'workout_exercises' not found in database.")
            return 1
        print("  [OK] Found workout_exercises table")

        # Check current columns
        print("\nChecking current schema...")
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add superset_target_reps column
        if 'superset_target_reps' in columns:
            print("  - Column superset_target_reps already exists")
        else:
            print("Adding superset_target_reps column...")
            cursor.execute('''
                ALTER TABLE workout_exercises
                ADD COLUMN superset_target_reps INTEGER DEFAULT NULL
            ''')
            print("  [OK] Added superset_target_reps column")

        # Add superset_actual_reps column
        if 'superset_actual_reps' in columns:
            print("  - Column superset_actual_reps already exists")
        else:
            print("Adding superset_actual_reps column...")
            cursor.execute('''
                ALTER TABLE workout_exercises
                ADD COLUMN superset_actual_reps INTEGER DEFAULT NULL
            ''')
            print("  [OK] Added superset_actual_reps column")

        conn.commit()

        print("\n" + "=" * 60)
        print("[OK] Migration completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        return 1

    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add superset reps columns')
    parser.add_argument('--db-path', default=None,
                        help='Path to database file (auto-detected if not specified)')
    args = parser.parse_args()

    sys.exit(migrate(args.db_path))
