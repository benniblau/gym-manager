#!/usr/bin/env python3
"""
Migration Script: Add Cossack Squat Exercise
Date: 2026-02-08
Description: Adds the Cossack Squat exercise with description, instructions,
             primary/secondary muscles, and equipment mapping.

Usage:
    python migrations/add_cossack_squat.py [--db-path PATH] [--dry-run]

Options:
    --db-path PATH    Path to exercises.db (default: exercises.db)
    --dry-run         Show what would be done without making changes
"""

import sqlite3
import os
import sys
import argparse

EXERCISE = {
    'name': 'Cossack Squat',
    'description': 'A deep lateral squat where you shift your weight to one side while keeping the opposite leg straight. This exercise builds single-leg strength, improves hip mobility and adductor flexibility, and challenges balance. It is an excellent movement for developing functional lower body strength and range of motion.',
    'category': 'strength',
    'primary_muscles': ['quadriceps', 'glutes', 'adductors'],
    'secondary_muscles': ['hamstrings', 'calves'],
    'equipment': ['bodyweight'],
    'instructions': [
        'Stand with your feet wider than shoulder-width apart, toes slightly pointed outward',
        'Shift your weight to one side and bend that knee, sitting your hips back and down',
        'Keep the opposite leg straight with the foot flat on the floor or toes pointing up',
        'Descend as deep as you can while keeping your heel flat on the squatting side',
        'Keep your chest up and core engaged throughout the movement',
        'Drive through the heel of the bent leg to return to the starting position',
        'Repeat on the same side or alternate sides each rep',
    ]
}


def get_db_connection(db_path):
    """Create database connection"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")
    return sqlite3.connect(db_path)


def exercise_exists(cursor, exercise_name):
    """Check if exercise already exists"""
    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    return cursor.fetchone() is not None


def get_category_id(cursor, category_name):
    """Get category ID by name"""
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Category '{category_name}' not found")
    return row[0]


def get_muscle_id(cursor, muscle_name):
    """Get muscle ID by name"""
    cursor.execute("SELECT id FROM muscles WHERE LOWER(name) = LOWER(?)", (muscle_name,))
    row = cursor.fetchone()
    if not row:
        print(f"  Warning: Muscle '{muscle_name}' not found, skipping")
        return None
    return row[0]


def get_equipment_id(cursor, equipment_name):
    """Get equipment ID by name"""
    cursor.execute("SELECT id FROM equipment WHERE LOWER(name) = LOWER(?)", (equipment_name,))
    row = cursor.fetchone()
    if not row:
        print(f"  Warning: Equipment '{equipment_name}' not found, skipping")
        return None
    return row[0]


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Add Cossack Squat exercise to database')
    parser.add_argument('--db-path', default='exercises.db', help='Path to database file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Migration: Add Cossack Squat")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    print("=" * 60)

    try:
        conn = get_db_connection(args.db_path)
        cursor = conn.cursor()

        # Check if already exists
        if exercise_exists(cursor, EXERCISE['name']):
            print(f"\nSkipping: '{EXERCISE['name']}' already exists")
            print("Migration complete (nothing to do)")
            return 0

        # Get category
        category_id = get_category_id(cursor, EXERCISE['category'])
        print(f"\nCategory: {EXERCISE['category']} (ID: {category_id})")

        # Insert exercise
        print(f"\nAdding: {EXERCISE['name']}")
        if not args.dry_run:
            cursor.execute('''
                INSERT INTO exercises (name, description, category_id, is_garmin_exercise)
                VALUES (?, ?, ?, 0)
            ''', (EXERCISE['name'], EXERCISE['description'], category_id))
            exercise_id = cursor.lastrowid
        else:
            exercise_id = '???'
            print(f"  [DRY RUN] Would insert exercise")

        print(f"  Exercise ID: {exercise_id}")

        # Add primary muscles
        for muscle_name in EXERCISE['primary_muscles']:
            muscle_id = get_muscle_id(cursor, muscle_name)
            if muscle_id:
                if args.dry_run:
                    print(f"  [DRY RUN] Would add primary muscle: {muscle_name}")
                else:
                    cursor.execute('INSERT INTO exercise_primary_muscles (exercise_id, muscle_id) VALUES (?, ?)',
                                   (exercise_id, muscle_id))
                    print(f"  Primary muscle: {muscle_name}")

        # Add secondary muscles
        for muscle_name in EXERCISE['secondary_muscles']:
            muscle_id = get_muscle_id(cursor, muscle_name)
            if muscle_id:
                if args.dry_run:
                    print(f"  [DRY RUN] Would add secondary muscle: {muscle_name}")
                else:
                    cursor.execute('INSERT INTO exercise_secondary_muscles (exercise_id, muscle_id) VALUES (?, ?)',
                                   (exercise_id, muscle_id))
                    print(f"  Secondary muscle: {muscle_name}")

        # Add equipment
        for equipment_name in EXERCISE['equipment']:
            equipment_id = get_equipment_id(cursor, equipment_name)
            if equipment_id:
                if args.dry_run:
                    print(f"  [DRY RUN] Would add equipment: {equipment_name}")
                else:
                    cursor.execute('INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES (?, ?)',
                                   (exercise_id, equipment_id))
                    print(f"  Equipment: {equipment_name}")

        # Add instructions
        for step_num, instruction in enumerate(EXERCISE['instructions'], start=1):
            if args.dry_run:
                print(f"  [DRY RUN] Would add instruction {step_num}: {instruction[:50]}...")
            else:
                cursor.execute('INSERT INTO instructions (exercise_id, step_number, instruction) VALUES (?, ?, ?)',
                               (exercise_id, step_num, instruction))
        print(f"  Instructions: {len(EXERCISE['instructions'])} steps")

        # Commit
        if not args.dry_run:
            conn.commit()
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
        else:
            print("\n" + "=" * 60)
            print("DRY RUN completed - no changes were made")

        print("=" * 60)

    except Exception as e:
        print(f"\nMigration failed: {e}", file=sys.stderr)
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
