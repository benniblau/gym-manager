#!/usr/bin/env python3
"""
Migration Script: Add 4 New Plyometric Exercises (Batch 2)
Date: 2026-01-29
Description: Adds new plyometric exercises from screenshots with full details including
             categories, muscles, instructions, descriptions, and renames image files.

Usage:
    python migrations/add_exercises_2026_01_29_v2.py [--db-path PATH] [--images-path PATH]

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
        'name': 'Single Leg Lateral Drop Landing',
        'description': 'A unilateral plyometric drill focusing on lateral landing mechanics. This exercise teaches proper deceleration and stability when landing on one leg from a sideways drop, essential for injury prevention in sports involving lateral movements like basketball, tennis, and soccer.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'adductors', 'abductors'],
        'equipment': ['box'],
        'instructions': [
            'Stand sideways on the edge of a low box (15-20cm height)',
            'Balance on the leg closest to the edge of the box',
            'Step off the box laterally with your outside foot',
            'Land softly on the outside leg only',
            'Absorb the impact by bending your knee and hip',
            'Keep your knee tracking over your toes, avoiding inward collapse',
            'Maintain an upright torso and engaged core',
            'Hold the landing position for 2-3 seconds to check stability',
            'Step back up and repeat for prescribed repetitions',
            'Complete all reps on one side before switching'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.33.14.png',
        'new_filename': 'single-leg-lateral-drop-landing.png'
    },
    {
        'name': 'Single Leg Lateral Box Jump',
        'description': 'An advanced unilateral plyometric exercise where you jump laterally onto a box using one leg. This movement develops single-leg power in the frontal plane, improving lateral explosiveness and stability crucial for cutting and change-of-direction movements in sports.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'adductors', 'abductors'],
        'equipment': ['box'],
        'instructions': [
            'Stand on one leg beside a low box (15-20cm height)',
            'Position yourself about one foot away from the box',
            'Bend your standing knee slightly and swing your arms',
            'Explosively push off laterally toward the box',
            'Land softly on the same leg on top of the box',
            'Absorb the landing with a bent knee and stable hip',
            'Maintain balance and hold for a moment',
            'Step down carefully and reset',
            'Complete all repetitions on one leg before switching',
            'Focus on controlled, quality landings over height'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.33.36.png',
        'new_filename': 'single-leg-lateral-box-jump.png'
    },
    {
        'name': 'Standing Long Jump',
        'description': 'A fundamental plyometric exercise testing and developing horizontal explosive power. Starting from a stationary position, you jump as far forward as possible. This classic athletic movement builds leg power, coordination, and is commonly used as a fitness assessment in sports.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Stand with feet shoulder-width apart at the starting line',
            'Bend your knees and hinge at the hips into a quarter squat',
            'Swing your arms back behind your body',
            'Explosively swing arms forward while extending hips, knees, and ankles',
            'Drive forward and upward at approximately 45 degrees',
            'Bring your knees up toward your chest during flight',
            'Extend your legs forward as you prepare to land',
            'Land on both feet simultaneously with soft knees',
            'Absorb the impact and stick the landing without falling backward',
            'Measure distance from starting line to nearest heel'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.34.02.png',
        'new_filename': 'standing-long-jump.png'
    },
    {
        'name': 'Scissor Jumps',
        'description': 'A dynamic plyometric exercise where you explosively alternate your leg positions in a split stance while airborne. Also known as split jump alternations, this exercise develops lower body power, cardiovascular endurance, and coordination while challenging balance and stability.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'hip flexors', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Start in a split stance with one foot forward and one back',
            'Lower into a lunge position with both knees at 90 degrees',
            'Keep your torso upright and core engaged',
            'Explosively jump straight up, driving through both legs',
            'While airborne, switch your leg positions (scissor motion)',
            'Land softly with the opposite leg now in front',
            'Immediately lower into a lunge on the new side',
            'Continue alternating legs with each jump',
            'Maintain a steady rhythm and controlled landings',
            'Keep your arms swinging naturally for momentum and balance'
        ],
        'old_filename': 'Screenshot 2026-01-29 at 17.34.24.png',
        'new_filename': 'scissor-jumps.png'
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
            print(f"  Renamed image file")
    elif os.path.exists(new_path):
        print(f"  Image file already exists: {exercise_data['new_filename']}")
    else:
        print(f"  Warning: Image file not found (checked both old and new names)")

    print(f"  Added successfully")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description='Add new exercises to database')
    parser.add_argument('--db-path', default='exercises.db', help='Path to database file')
    parser.add_argument('--images-path', default='app/static/images', help='Path to images directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Exercise Migration Script - 2026-01-29 (Batch 2)")
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
                print(f"  Error adding exercise: {e}")
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
        print(f"\nMigration failed: {e}", file=sys.stderr)
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
