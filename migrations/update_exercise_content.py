#!/usr/bin/env python3
"""
Migration Script: Apply Generated Exercise Content to Database
Description: Updates exercises in the database with AI-generated descriptions
             and instructions.

Usage:
    python migrations/update_exercise_content.py --content FILE [options]

Options:
    --content FILE      JSON file with generated content (from generate_exercise_content.py)
    --db-path PATH      Path to exercises.db (default: exercises.db)
    --dry-run           Show what would be done without making changes
    --backup            Create a backup of the database before changes

WARNING: This script modifies the database. Use --dry-run first to verify changes.
"""

import sqlite3
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path


def backup_database(db_path):
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def apply_updates(content_file, db_path, dry_run=True):
    """Apply generated content to the database."""

    # Load generated content
    with open(content_file) as f:
        content = json.load(f)

    print(f"Loaded content for {len(content)} exercises from {content_file}")

    if dry_run:
        print("\n[DRY RUN MODE] - No changes will be made\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    updated_descriptions = 0
    updated_instructions = 0
    errors = 0

    for exercise_id, data in content.items():
        try:
            # Get current exercise info
            exercise = conn.execute(
                'SELECT id, name, description FROM exercises WHERE id = ?',
                (exercise_id,)
            ).fetchone()

            if not exercise:
                print(f"  [SKIP] Exercise ID {exercise_id} not found in database")
                continue

            exercise_name = exercise['name']
            current_desc = exercise['description']

            # Check if we have valid content
            if 'description' not in data or 'instructions' not in data:
                print(f"  [SKIP] {exercise_name}: Missing description or instructions in content")
                continue

            new_desc = data['description']
            instructions = data['instructions']

            if dry_run:
                print(f"  [{exercise_id}] {exercise_name}")
                print(f"      Description: \"{new_desc[:60]}...\"")
                print(f"      Instructions: {len(instructions)} steps")
            else:
                # Update description
                conn.execute(
                    'UPDATE exercises SET description = ? WHERE id = ?',
                    (new_desc, exercise_id)
                )
                updated_descriptions += 1

                # Clear existing instructions
                conn.execute(
                    'DELETE FROM instructions WHERE exercise_id = ?',
                    (exercise_id,)
                )

                # Insert new instructions
                for step_num, instruction in enumerate(instructions, 1):
                    conn.execute(
                        'INSERT INTO instructions (exercise_id, step_number, instruction) VALUES (?, ?, ?)',
                        (exercise_id, step_num, instruction)
                    )
                updated_instructions += 1

        except Exception as e:
            print(f"  [ERROR] Exercise {exercise_id}: {e}")
            errors += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*60}")
    if dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print(f"Would update {len(content)} exercises")
    else:
        print("UPDATE COMPLETE")
        print(f"  Descriptions updated: {updated_descriptions}")
        print(f"  Instructions updated: {updated_instructions}")
        print(f"  Errors: {errors}")
    print(f"{'='*60}\n")

    return updated_descriptions, updated_instructions, errors


def verify_updates(db_path, sample_size=5):
    """Verify that updates were applied correctly by sampling random exercises."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("\n--- Verification Sample ---")

    # Get random exercises with instructions
    samples = conn.execute('''
        SELECT e.id, e.name, e.description
        FROM exercises e
        JOIN instructions i ON e.id = i.exercise_id
        WHERE e.description != 'Strength exercise for overall fitness.'
        GROUP BY e.id
        ORDER BY RANDOM()
        LIMIT ?
    ''', (sample_size,)).fetchall()

    for ex in samples:
        instructions = conn.execute(
            'SELECT instruction FROM instructions WHERE exercise_id = ? ORDER BY step_number',
            (ex['id'],)
        ).fetchall()

        print(f"\n[{ex['id']}] {ex['name']}")
        print(f"  Description: {ex['description'][:80]}...")
        print(f"  Instructions ({len(instructions)} steps):")
        for i, inst in enumerate(instructions[:3], 1):
            print(f"    {i}. {inst['instruction'][:60]}...")
        if len(instructions) > 3:
            print(f"    ... and {len(instructions) - 3} more steps")

    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply generated exercise content to database')
    parser.add_argument('--content', required=True, help='JSON file with generated content')
    parser.add_argument('--db-path', default='exercises.db', help='Path to exercises.db')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--backup', action='store_true', help='Create backup before changes')
    parser.add_argument('--verify', action='store_true', help='Verify updates after applying')
    args = parser.parse_args()

    if not Path(args.content).exists():
        print(f"Error: Content file not found: {args.content}")
        exit(1)

    if not Path(args.db_path).exists():
        print(f"Error: Database not found: {args.db_path}")
        exit(1)

    # Create backup if requested
    if args.backup and not args.dry_run:
        backup_database(args.db_path)

    # Apply updates
    apply_updates(args.content, args.db_path, dry_run=args.dry_run)

    # Verify if requested
    if args.verify and not args.dry_run:
        verify_updates(args.db_path)
