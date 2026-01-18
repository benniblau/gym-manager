#!/usr/bin/env python3
"""
Migration: Add Supersets Support
Date: 2026-01-18
Description: Adds superset_group_id column to workout_exercises table
             to support grouping exercises into supersets
"""

import sqlite3
import sys
import argparse


def migrate(db_path='exercises.db'):
    """Run the supersets migration"""
    print("=" * 60)
    print("Supersets Migration")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        print("Checking current schema...")
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


def rollback(db_path='exercises.db'):
    """Rollback the migration (remove superset_group_id column)"""
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
    parser.add_argument('--db-path', default='exercises.db',
                        help='Path to database file')
    parser.add_argument('--rollback', action='store_true',
                        help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        sys.exit(rollback(args.db_path))
    else:
        sys.exit(migrate(args.db_path))
