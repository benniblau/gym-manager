#!/usr/bin/env python3
"""
Migration Script: Add 7 New Plyometric Exercises (2026-02-23)
Date: 2026-02-23
Description: Adds new plyometric jump training exercises from screenshots, including
             descriptions, instructions, muscle mappings, and image file renames.

Usage:
    python migrations/add_exercises_2026_02_23.py [--db-path PATH] [--images-path PATH] [--dry-run]

Options:
    --db-path PATH          Path to exercises.db (default: exercises.db)
    --images-path PATH      Path to static/images directory (default: app/static/images)
    --dry-run               Show what would be done without making changes
"""

import sqlite3
import os
import shutil
import sys
import argparse

EXERCISES = [
    {
        'name': 'Single Leg Lateral Drop',
        'description': 'A unilateral plyometric deceleration drill performed from a low box. You step or drop off the side of the box and land softly on one leg, training the neuromuscular system to absorb lateral forces efficiently. This exercise is fundamental for injury prevention and developing eccentric leg strength for sports requiring lateral movements.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'adductors', 'abductors'],
        'equipment': ['box'],
        'instructions': [
            'Stand on top of a low box (15–20 cm height) on one leg',
            'Position the standing leg close to the lateral edge of the box',
            'Keep a slight bend in the knee and engage your core',
            'Step off the side of the box with your outside foot, dropping laterally',
            'Land softly on the outside leg only, bending the knee to absorb impact',
            'Keep the knee tracking over your toes — avoid inward collapse (valgus)',
            'Maintain an upright torso and controlled posture throughout the landing',
            'Hold the landing position for 2–3 seconds to confirm stability',
            'Step back up onto the box and repeat for prescribed repetitions',
            'Complete all reps on one side before switching legs',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.57.18.png',
        'new_filename': 'single-leg-lateral-drop.png',
    },
    {
        'name': 'Single Leg Lateral Jump',
        'description': 'An advanced unilateral plyometric exercise where you explosively jump sideways onto a low box using one leg. This movement builds lateral power and single-leg stability in the frontal plane, essential for sports that require quick side-to-side change of direction. Focus on quality landings over maximum height.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'adductors', 'abductors'],
        'equipment': ['box'],
        'instructions': [
            'Stand on one leg beside a low box (15–20 cm height), positioned about one foot away',
            'Bend the standing knee slightly and load your hip',
            'Swing your arms back to generate momentum',
            'Explosively push off the standing leg laterally toward the box',
            'Land softly on the same leg on top of the box',
            'Absorb the landing by bending the knee and hinging slightly at the hip',
            'Maintain balance and hold the landing for a moment before stepping down',
            'Step down carefully to the starting position and reset',
            'Complete all repetitions on one leg before switching',
            'Prioritise controlled, quiet landings over maximum jump distance',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.57.45.png',
        'new_filename': 'single-leg-lateral-jump.png',
    },
    {
        'name': 'Stretch Broad Jump',
        'description': 'A plyometric broad jump variation emphasising maximum forward reach and full-body extension during flight. Starting from a squat countermovement, you drive explosively upward and forward, fully extending the hips, knees, and ankles before reaching out with the legs to maximise horizontal distance. A key assessment and training tool for explosive power.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'hip flexors'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Stand with feet shoulder-width apart at the starting mark',
            'Perform a quick countermovement: bend knees, hinge hips, and swing arms back',
            'Explosively drive upward and forward, extending hips, knees, and ankles fully',
            'Swing the arms forcefully forward and up to add momentum',
            'During flight, fully extend the body — reach long through the legs and arms',
            'As you approach landing, pull the knees toward your chest to maximise reach',
            'Extend legs forward and reach with your heels as far as possible',
            'Land on both feet simultaneously with soft, bent knees',
            'Absorb the impact and hold the landing without falling backward',
            'Measure distance from the starting line to the nearest point of contact',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.58.06.png',
        'new_filename': 'stretch-broad-jump.png',
    },
    {
        'name': 'Alternating Jumps',
        'description': 'A plyometric jump training exercise where you explosively switch your split stance with each jump, alternating which leg leads. Also known as scissor jumps or split jump alternations, this drill develops lower body power, cardiovascular conditioning, and coordination simultaneously, making it a staple in jump training circuits.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'hip flexors', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Start in a split stance with one foot forward and one foot back',
            'Lower into a lunge position with both knees at approximately 90 degrees',
            'Keep your torso upright and core braced throughout the movement',
            'Explosively jump straight up, driving through both legs simultaneously',
            'While airborne, switch your leg positions in a scissor motion',
            'Land softly with the opposite leg now in front',
            'Immediately lower into a lunge on the new side',
            'Continue alternating legs with each jump without pausing',
            'Swing your arms naturally for rhythm and balance',
            'Maintain consistent depth on each lunge and controlled landings',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.58.39.png',
        'new_filename': 'alternating-jumps.png',
    },
    {
        'name': 'Bounding',
        'description': 'A plyometric running drill involving exaggerated, powerful strides where you drive explosively off one foot and travel as far forward as possible with each step. Bounding bridges the gap between strength and sprint performance, developing maximum horizontal power output and reactive strength in the sagittal plane. A cornerstone exercise in sprint and athletic development.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes', 'hamstrings'],
        'secondary_muscles': ['calves', 'hip flexors', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Begin with a short build-up jog to generate momentum',
            'Push off powerfully from one foot, driving the opposite knee high',
            'Aim for maximum forward distance with each stride',
            'Maintain a tall, slightly forward-leaning posture throughout',
            'Swing the arms in opposition to the legs for added power',
            'Land on the ball of the foot of the leading leg',
            'Immediately drive off the landing leg into the next bound',
            'Keep ground contact time as short and explosive as possible',
            'Focus on power and distance rather than speed',
            'Perform over a set distance (e.g., 20–30 m) and count the strides',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.59.12.png',
        'new_filename': 'bounding.png',
    },
    {
        'name': 'Single Leg Lateral Bounds',
        'description': 'A unilateral plyometric exercise where you bound sideways from one leg to the same leg repeatedly, or alternate sides, covering horizontal distance laterally. This drill trains single-leg power in the frontal plane, lateral explosiveness, and the ability to absorb and redirect forces — all critical for sports requiring rapid side-to-side movements.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'adductors', 'abductors', 'abdominals'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Stand on one leg with a slight bend in the knee',
            'Load the hip by sitting back slightly, engaging the glutes',
            'Drive explosively off the standing leg, pushing laterally',
            'Aim for maximum horizontal distance to the side',
            'Land softly on the same leg (or opposite leg for alternating bounds)',
            'Absorb the landing with a bent knee and stable hip',
            'Keep the knee aligned over the toes — prevent inward collapse',
            'Immediately load into the next bound without excessive pause',
            'Maintain a tall, controlled posture throughout',
            'Perform for a set number of reps or distance per leg',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 09.59.35.png',
        'new_filename': 'single-leg-lateral-bounds.png',
    },
    {
        'name': 'Single Leg Broad Jump',
        'description': 'A demanding unilateral plyometric exercise where you jump as far forward as possible from a single-leg takeoff and land on both feet or the same leg. This movement reveals and develops asymmetries in explosive leg power, tests single-leg stability under load, and challenges the athlete to coordinate a powerful push-off with a controlled landing.',
        'category': 'plyometrics',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals', 'hip flexors'],
        'equipment': ['bodyweight'],
        'instructions': [
            'Stand on one leg at the starting mark, with a slight bend in the knee',
            'Perform a single-leg countermovement: bend the knee, hinge at the hip, swing arms back',
            'Explosively drive forward off the standing leg, extending hip, knee, and ankle fully',
            'Swing both arms forcefully forward and up to maximise distance',
            'During flight, reach your legs forward and keep your chest up',
            'Land on both feet (or the same foot for advanced variation) with soft, bent knees',
            'Absorb the impact evenly and hold the landing without stepping forward',
            'Measure distance from the starting line to the nearest heel',
            'Rest adequately between repetitions to maintain power output',
            'Compare left and right leg distances to identify and address strength asymmetries',
        ],
        'old_filename': 'Screenshot 2026-02-23 at 10.00.04.png',
        'new_filename': 'single-leg-broad-jump.png',
    },
]


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


def get_next_exercise_id(cursor):
    """Get the next available exercise ID"""
    cursor.execute("SELECT MAX(id) FROM exercises")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1


def add_exercise(cursor, exercise_data, exercise_id, images_path, dry_run=False):
    """Add a single exercise to the database"""
    print(f"\nAdding: {exercise_data['name']} (ID: {exercise_id})")

    category_id = get_category_id(cursor, exercise_data['category'])

    if dry_run:
        print(f"  [DRY RUN] Would insert exercise with category_id={category_id}")
    else:
        cursor.execute('''
            INSERT INTO exercises (id, name, description, category_id, image1_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            exercise_id,
            exercise_data['name'],
            exercise_data['description'],
            category_id,
            exercise_data['new_filename'],
        ))

    # Primary muscles
    for muscle_name in exercise_data['primary_muscles']:
        muscle_id = get_muscle_id(cursor, muscle_name)
        if muscle_id:
            if dry_run:
                print(f"  [DRY RUN] Would add primary muscle: {muscle_name}")
            else:
                cursor.execute(
                    'INSERT INTO exercise_primary_muscles (exercise_id, muscle_id) VALUES (?, ?)',
                    (exercise_id, muscle_id)
                )

    # Secondary muscles
    for muscle_name in exercise_data['secondary_muscles']:
        muscle_id = get_muscle_id(cursor, muscle_name)
        if muscle_id:
            if dry_run:
                print(f"  [DRY RUN] Would add secondary muscle: {muscle_name}")
            else:
                cursor.execute(
                    'INSERT INTO exercise_secondary_muscles (exercise_id, muscle_id) VALUES (?, ?)',
                    (exercise_id, muscle_id)
                )

    # Equipment
    for equipment_name in exercise_data['equipment']:
        cursor.execute("SELECT id FROM equipment WHERE LOWER(name) = LOWER(?)", (equipment_name,))
        row = cursor.fetchone()
        if row:
            if dry_run:
                print(f"  [DRY RUN] Would add equipment: {equipment_name}")
            else:
                cursor.execute(
                    'INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES (?, ?)',
                    (exercise_id, row[0])
                )
        else:
            print(f"  Warning: Equipment '{equipment_name}' not found, skipping")

    # Instructions
    for step_num, instruction in enumerate(exercise_data['instructions'], start=1):
        if dry_run:
            print(f"  [DRY RUN] Would add instruction {step_num}: {instruction[:60]}...")
        else:
            cursor.execute(
                'INSERT INTO instructions (exercise_id, step_number, instruction) VALUES (?, ?, ?)',
                (exercise_id, step_num, instruction)
            )
    if not dry_run:
        print(f"  Instructions: {len(exercise_data['instructions'])} steps")

    # Rename image file
    old_path = os.path.join(images_path, exercise_data['old_filename'])
    new_path = os.path.join(images_path, exercise_data['new_filename'])

    if os.path.exists(old_path):
        if dry_run:
            print(f"  [DRY RUN] Would rename: {exercise_data['old_filename']} -> {exercise_data['new_filename']}")
        else:
            shutil.move(old_path, new_path)
            print(f"  Renamed image: {exercise_data['old_filename']} -> {exercise_data['new_filename']}")
    elif os.path.exists(new_path):
        print(f"  Image already renamed: {exercise_data['new_filename']}")
    else:
        print(f"  Warning: Image not found (checked both old and new names)")

    if not dry_run:
        print(f"  Added successfully")


def main():
    parser = argparse.ArgumentParser(description='Add 7 new plyometric exercises (2026-02-23)')
    parser.add_argument('--db-path', default='exercises.db', help='Path to database file')
    parser.add_argument('--images-path', default='app/static/images', help='Path to images directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Exercise Migration Script — 2026-02-23")
    print("=" * 60)
    print(f"Database:  {args.db_path}")
    print(f"Images:    {args.images_path}")
    print(f"Exercises: {len(EXERCISES)}")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    print("=" * 60)

    try:
        conn = get_db_connection(args.db_path)
        cursor = conn.cursor()

        start_id = get_next_exercise_id(cursor)
        print(f"\nStarting exercise ID: {start_id}")

        added_count = 0
        skipped_count = 0
        id_offset = 0

        for exercise_data in EXERCISES:
            if exercise_exists(cursor, exercise_data['name']):
                print(f"\nSkipping (already exists): {exercise_data['name']}")
                skipped_count += 1
                continue

            exercise_id = start_id + id_offset
            try:
                add_exercise(cursor, exercise_data, exercise_id, args.images_path, args.dry_run)
                added_count += 1
                id_offset += 1
            except Exception as e:
                print(f"  Error adding exercise: {e}")
                if not args.dry_run:
                    conn.rollback()
                    raise

        if not args.dry_run:
            conn.commit()
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
        else:
            print("\n" + "=" * 60)
            print("DRY RUN completed — no changes were made")

        print("=" * 60)
        print(f"Added:   {added_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total:   {len(EXERCISES)}")
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
