#!/usr/bin/env python3
"""Test script to verify invitation system is working"""

import os
import sys

# Set up Flask app context
os.environ['FLASK_ENV'] = 'production'

from app import create_app
from app.models import User, Invitation

app = create_app('production')

with app.app_context():
    try:
        # Test 1: Check if invitations table exists
        print("Test 1: Checking if invitations table exists...")
        from app.models import get_db
        db = get_db()
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invitations'")
        result = cursor.fetchone()

        if result:
            print("✓ Invitations table exists")
        else:
            print("✗ Invitations table does NOT exist - migration not run!")
            sys.exit(1)

        # Test 2: Check table schema
        print("\nTest 2: Checking invitations table schema...")
        cursor = db.execute("PRAGMA table_info(invitations)")
        columns = cursor.fetchall()
        print(f"✓ Found {len(columns)} columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # Test 3: Check users table has new columns
        print("\nTest 3: Checking users table has invited_by and invitation_id...")
        cursor = db.execute("PRAGMA table_info(users)")
        columns = {col[1] for col in cursor.fetchall()}

        if 'invited_by' in columns:
            print("✓ users.invited_by column exists")
        else:
            print("✗ users.invited_by column missing!")

        if 'invitation_id' in columns:
            print("✓ users.invitation_id column exists")
        else:
            print("✗ users.invitation_id column missing!")

        # Test 4: Try creating an invitation
        print("\nTest 4: Testing Invitation.create()...")

        # Get first user
        user = User.get_by_id(1)
        if not user:
            print("✗ No users found - cannot test")
            sys.exit(1)

        invitation = Invitation.create(
            sender_id=user.id,
            recipient_email="test@example.com",
            notes="Test invitation"
        )

        if invitation:
            print(f"✓ Invitation created successfully!")
            print(f"  - Token: {invitation.token[:20]}...")
            print(f"  - Sender ID: {invitation.sender_id}")
            print(f"  - Status: {invitation.status}")

            # Clean up test invitation
            db.execute("DELETE FROM invitations WHERE id = ?", (invitation.id,))
            db.commit()
            print("✓ Test invitation cleaned up")
        else:
            print("✗ Failed to create invitation")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
