#!/usr/bin/env python3
"""
Migration: Add Invitations System
Date: 2026-01-11
Description: Creates invitations table and updates users table for invitation tracking

Usage:
    python3 migrations/add_invitations.py [--db-path PATH]
"""

import sqlite3
import sys
import argparse

def migrate(db_path='exercises.db'):
    """Run the invitation system migration"""
    print("=" * 60)
    print("Invitation System Migration")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create invitations table
        print("Creating invitations table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                sender_id INTEGER NOT NULL,
                recipient_email TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                accepted_at TIMESTAMP,
                recipient_user_id INTEGER,
                notes TEXT,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        print("  ✓ Created invitations table")

        # Create indexes for performance
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token)')
        print("  ✓ Created index on token")

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitations_sender ON invitations(sender_id)')
        print("  ✓ Created index on sender_id")

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invitations_status ON invitations(status)')
        print("  ✓ Created index on status")

        # Check if columns already exist in users table
        print("\nUpdating users table...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'invited_by' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN invited_by INTEGER')
            print("  ✓ Added invited_by column to users")
        else:
            print("  ⊙ Column invited_by already exists")

        if 'invitation_id' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN invitation_id INTEGER')
            print("  ✓ Added invitation_id column to users")
        else:
            print("  ⊙ Column invitation_id already exists")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nDatabase schema updated:")
        print("  - invitations table created")
        print("  - 3 indexes created")
        print("  - 2 columns added to users table")
        print("\nNext steps:")
        print("  1. Implement Invitation model in app/models.py")
        print("  2. Update User.create() method")
        print("  3. Add invitation routes and forms")

        return 0

    except Exception as e:
        conn.rollback()
        print("\n" + "=" * 60)
        print(f"✗ Migration failed: {e}")
        print("=" * 60)
        print("\nRolling back changes...")
        return 1

    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run invitation system migration')
    parser.add_argument('--db-path', default='exercises.db',
                       help='Path to database file (default: exercises.db)')
    args = parser.parse_args()

    sys.exit(migrate(args.db_path))
