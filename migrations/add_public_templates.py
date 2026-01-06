#!/usr/bin/env python3
"""
Database Migration: Add public template functionality

Adds is_public and usage_count columns to the workouts table
to enable public/private template sharing.
"""

import sqlite3
import os
import shutil
from datetime import datetime


def backup_database(db_path):
    """Create a backup of the database before migration"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✓ Backup created successfully")
    return backup_path


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate(db_path='exercises.db'):
    """Run the migration"""

    print("=" * 60)
    print("Public Templates Migration")
    print("=" * 60)

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False

    # Create backup
    backup_path = backup_database(db_path)

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\nChecking current schema...")

        # Check if columns already exist
        has_is_public = column_exists(cursor, 'workouts', 'is_public')
        has_usage_count = column_exists(cursor, 'workouts', 'usage_count')

        if has_is_public and has_usage_count:
            print("⚠ Migration already applied - columns exist")
            conn.close()
            return True

        # Add is_public column
        if not has_is_public:
            print("\nAdding is_public column...")
            cursor.execute('''
                ALTER TABLE workouts ADD COLUMN is_public INTEGER DEFAULT 0
            ''')
            print("✓ is_public column added")
        else:
            print("⊘ is_public column already exists")

        # Add usage_count column
        if not has_usage_count:
            print("\nAdding usage_count column...")
            cursor.execute('''
                ALTER TABLE workouts ADD COLUMN usage_count INTEGER DEFAULT 0
            ''')
            print("✓ usage_count column added")
        else:
            print("⊘ usage_count column already exists")

        # Create index for efficient public template queries
        print("\nCreating index for public templates...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_workouts_public
            ON workouts(is_public, is_template)
        ''')
        print("✓ Index created")

        # Commit changes
        conn.commit()

        # Verify migration
        print("\nVerifying migration...")
        cursor.execute("PRAGMA table_info(workouts)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if 'is_public' in columns and 'usage_count' in columns:
            print("✓ Migration verified successfully")

            # Show updated schema
            print("\nUpdated workouts table columns:")
            cursor.execute("PRAGMA table_info(workouts)")
            for row in cursor.fetchall():
                col_id, name, type_, notnull, default, pk = row
                print(f"  - {name} ({type_})")

            conn.close()
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)
            return True
        else:
            print("✗ Migration verification failed")
            conn.close()
            return False

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        print(f"\nRestoring from backup: {backup_path}")

        # Restore from backup
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            print("✓ Database restored from backup")

        return False


def rollback(db_path='exercises.db'):
    """Rollback the migration (removes added columns)"""

    print("=" * 60)
    print("Rolling back Public Templates Migration")
    print("=" * 60)
    print("\nNote: SQLite does not support DROP COLUMN directly.")
    print("Rollback requires recreating the table without the columns.")
    print("Use a backup file to restore if needed.")
    print("=" * 60)


if __name__ == '__main__':
    import sys

    db_path = 'exercises.db'

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'rollback':
            rollback(db_path)
        else:
            db_path = sys.argv[1]
            migrate(db_path)
    else:
        # Run migration
        success = migrate(db_path)
        sys.exit(0 if success else 1)
