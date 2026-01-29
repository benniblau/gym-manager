#!/usr/bin/env python3
"""
Migration Script: Add 3 New Plyometric Exercises
Date: 2026-01-29
Description: Adds new plyometric exercises from screenshots with full details including
             categories, muscles, instructions, descriptions, and renames image files.

Usage:
    python migrations/add_exercises_2026_01_29.py [--db-path PATH] [--images-path PATH]

Options:
    --db-path PATH          Path to exercises.db (default: exercises.db)
    --images-path PATH      Path to static/images directory (default: app/static/images)
    --dry-run              Show what would be done without making changes
"""

import sqlite3
import os
import shutil
import sys
from datetime import datetime

# Exercise data with complete information
EXERCISES = [
    {
        'name': 'Triple Standing Long Jump',
        'description': 'An explosive plyometric exercise where you perform three consecutive broad jumps without stopping. This exercise develops horizontal power, leg strength, and coordination while mimicking athletic movements used in sports like track and field.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Stand with feet shoulder-width apart at the starting mark',
            'Swing your arms back and bend your knees to load the jump',
            'Explosively swing arms forward and jump as far as possible',
            'Land softly on both feet, immediately absorbing into the next jump',
            'Without pausing, explode into the second jump using the momentum',
            'Land and immediately perform the third and final jump',
            'Stick the final landing with knees bent to absorb impact',
            'Focus on horizontal distance rather than height',
            'Maintain balance and control throughout all three jumps'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.02.08.png',
        'new_filename': 'triple-standing-long-jump.png'
    },
    {
        'name': 'Single Leg Box Jump',
        'description': 'A unilateral plyometric exercise where you jump onto an elevated platform using only one leg. This challenging movement develops single-leg power, balance, and stability while improving explosive strength and addressing muscle imbalances between legs.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'hip flexors'],
        'equipment': ['box'],
        'instructions': [
            'Stand on one leg facing a low box or platform (start with 15-30cm height)',
            'Keep your standing knee slightly bent and arms ready',
            'Swing your arms back while loading into a quarter squat on one leg',
            'Explosively drive through your standing leg to jump onto the box',
            'Land softly on the same leg with knee bent to absorb impact',
            'Stand tall on the box, maintaining balance',
            'Step down carefully and reset for the next repetition',
            'Complete all reps on one leg before switching',
            'Keep your core engaged throughout for stability'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.02.44.png',
        'new_filename': 'single-leg-box-jump.png'
    },
    {
        'name': 'Depth Drop Landing',
        'description': 'A foundational plyometric drill where you step off an elevated platform and focus on landing mechanics. This exercise teaches proper deceleration, shock absorption, and landing technique, which is essential for injury prevention and serves as a progression toward depth jumps.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['box'],
        'instructions': [
            'Stand on the edge of a box or platform (start with 30-40cm height)',
            'Step off the box with one foot, do not jump off',
            'Drop straight down, leading with both feet',
            'Land simultaneously on both feet with soft knees',
            'Absorb the impact by bending knees into a quarter squat position',
            'Keep your chest up and core engaged upon landing',
            'Freeze the landing position for 2-3 seconds to check form',
            'Knees should track over toes, not caving inward',
            'Step back up and repeat for the prescribed repetitions',
            'Progress to higher boxes only when landing mechanics are perfect'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.03.02.png',
        'new_filename': 'depth-drop-landing.png'
    }
]


def get_db_connection(db_path):
    """Create database connection"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")
    return sqlite3.connect(db_path)


def get_category_id(cursor, category_name):
    """Get category ID by name"""
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Category '{category_name}' not found in database")
    return row[0]


def get_muscle_id(cursor, muscle_name):
    """Get muscle ID by name"""
    cursor.execute("SELECT id FROM muscles WHERE LOWER(name) = LOWER(?)", (muscle_name,))
    row = cursor.fetchone()
    if not row:
        print(f"  Warning: Muscle '{muscle_name}' not found, skipping")
        return None
    return row[0]


def exercise_exists(cursor, exercise_name):
    """Check if exercise already exists"""
    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    return cursor.fetchone() is not None


def get_next_exercise_id(cursor):
    """Get the next available exercise ID"""
    cursor.execute("SELECT MAX(id) FROM exercises")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1


def add_exercise(cursor, exercise_data, exercise_id, images_path, dry_run=False):
    """Add a single exercise to the database"""
    print(f"\nAdding: {exercise_data['name']} (ID: {exercise_id})")

    # Get category ID
    category_id = get_category_id(cursor, exercise_data['category'])

    if dry_run:
        print(f"  [DRY RUN] Would insert exercise with category_id={category_id}")
    else:
        # Insert exercise
        cursor.execute('''
            INSERT INTO exercises (id, name, description, category_id, image1_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            exercise_id,
            exercise_data['name'],
            exercise_data['description'],
            category_id,
            exercise_data['new_filename']
        ))

    # Add primary muscles
    for muscle_name in exercise_data['primary_muscles']:
        muscle_id = get_muscle_id(cursor, muscle_name)
        if muscle_id:
            if dry_run:
                print(f"  [DRY RUN] Would add primary muscle: {muscle_name}")
            else:
                cursor.execute('''
                    INSERT INTO exercise_primary_muscles (exercise_id, muscle_id)
                    VALUES (?, ?)
                ''', (exercise_id, muscle_id))

    # Add secondary muscles
    for muscle_name in exercise_data['secondary_muscles']:
        muscle_id = get_muscle_id(cursor, muscle_name)
        if muscle_id:
            if dry_run:
                print(f"  [DRY RUN] Would add secondary muscle: {muscle_name}")
            else:
                cursor.execute('''
                    INSERT INTO exercise_secondary_muscles (exercise_id, muscle_id)
                    VALUES (?, ?)
                ''', (exercise_id, muscle_id))

    # Add equipment
    for equipment_name in exercise_data['equipment']:
        cursor.execute("SELECT id FROM equipment WHERE LOWER(name) = LOWER(?)", (equipment_name,))
        row = cursor.fetchone()
        if row:
            if dry_run:
                print(f"  [DRY RUN] Would add equipment: {equipment_name}")
            else:
                cursor.execute('''
                    INSERT INTO exercise_equipment (exercise_id, equipment_id)
                    VALUES (?, ?)
                ''', (exercise_id, row[0]))
        else:
            print(f"  Warning: Equipment '{equipment_name}' not found, skipping")

    # Add instructions
    for step_num, instruction in enumerate(exercise_data['instructions'], start=1):
        if dry_run:
            print(f"  [DRY RUN] Would add instruction {step_num}")
        else:
            cursor.execute('''
                INSERT INTO instructions (exercise_id, step_number, instruction)
                VALUES (?, ?, ?)
            ''', (exercise_id, step_num, instruction))

    # Rename image file (if old file exists) or verify new file exists
    old_path = os.path.join(images_path, exercise_data['old_filename'])
    new_path = os.path.join(images_path, exercise_data['new_filename'])

    if os.path.exists(old_path):
        if dry_run:
            print(f"  [DRY RUN] Would rename: {exercise_data['old_filename']} -> {exercise_data['new_filename']}")
        else:
            shutil.move(old_path, new_path)
            print(f"  ✓ Renamed image file")
    elif os.path.exists(new_path):
        print(f"  ✓ Image file already exists: {exercise_data['new_filename']}")
    else:
        print(f"  ⚠ Warning: Image file not found (checked both old and new names)")

    print(f"  ✓ Added successfully")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description='Add new exercises to database')
    parser.add_argument('--db-path', default='exercises.db', help='Path to database file')
    parser.add_argument('--images-path', default='app/static/images', help='Path to images directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Exercise Migration Script - 2026-01-29")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    print(f"Images: {args.images_path}")
    print(f"Exercises to add: {len(EXERCISES)}")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    print("=" * 60)

    try:
        # Connect to database
        conn = get_db_connection(args.db_path)
        cursor = conn.cursor()

        # Get starting exercise ID
        start_id = get_next_exercise_id(cursor)
        print(f"\nStarting exercise ID: {start_id}")

        # Track results
        added_count = 0
        skipped_count = 0

        # Add each exercise
        for i, exercise_data in enumerate(EXERCISES):
            exercise_id = start_id + i

            # Check if exercise already exists
            if exercise_exists(cursor, exercise_data['name']):
                print(f"\nSkipping (already exists): {exercise_data['name']}")
                skipped_count += 1
                continue

            try:
                add_exercise(cursor, exercise_data, exercise_id, args.images_path, args.dry_run)
                added_count += 1
            except Exception as e:
                print(f"  ✗ Error adding exercise: {e}")
                if not args.dry_run:
                    conn.rollback()
                    raise

        # Commit changes
        if not args.dry_run:
            conn.commit()
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
        else:
            print("\n" + "=" * 60)
            print("DRY RUN completed - no changes were made")

        print("=" * 60)
        print(f"Added: {added_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total: {len(EXERCISES)}")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
