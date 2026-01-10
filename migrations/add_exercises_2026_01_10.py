#!/usr/bin/env python3
"""
Migration Script: Add 18 New Exercises
Date: 2026-01-10
Description: Adds new exercises from screenshots with full details including
             categories, muscles, instructions, descriptions, and renames image files.

Usage:
    python migrations/add_exercises_2026_01_10.py [--db-path PATH] [--images-path PATH]

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
        'name': 'Elliptical Cross Trainer',
        'description': 'A low-impact cardiovascular exercise performed on an elliptical machine that simulates running without causing excessive pressure on the joints. This full-body cardio workout engages both upper and lower body muscles while providing an effective aerobic workout.',
        'category': 'cardio',
        'primary_muscles': ['quadriceps', 'hamstrings', 'glutes'],
        'secondary_muscles': ['calves', 'core'],
        'equipment': [],
        'instructions': [
            'Step onto the elliptical machine and place your feet on the pedals',
            'Grasp the moving handles with both hands',
            'Begin moving your legs in a smooth, elliptical motion',
            'Push and pull with your arms to engage your upper body',
            'Maintain an upright posture with your core engaged',
            'Continue for the desired duration, maintaining a steady pace',
            'Gradually slow down before stopping'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 15.58.25.png',
        'new_filename': 'elliptical-cross-trainer.png'
    },
    {
        'name': 'Battle Rope Alternating Waves',
        'description': 'A high-intensity cardio and strength exercise using battle ropes to create alternating wave patterns. This explosive movement builds power, endurance, and grip strength while engaging the entire body, particularly the shoulders, arms, and core.',
        'category': 'cardio',
        'primary_muscles': ['shoulders', 'core'],
        'secondary_muscles': ['forearms', 'back', 'quadriceps'],
        'equipment': [],
        'instructions': [
            'Stand with feet shoulder-width apart, holding one end of the rope in each hand',
            'Assume an athletic stance with knees slightly bent',
            'Engage your core and keep your back straight',
            'Rapidly raise one arm to shoulder height while lowering the other',
            'Continue alternating arms in a quick, powerful motion',
            'Create continuous waves traveling down the length of the rope',
            'Maintain consistent rhythm and intensity for the prescribed duration',
            'Keep your breathing steady throughout the movement'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 15.58.44.png',
        'new_filename': 'battle-rope-alternating-waves.png'
    },
    {
        'name': 'Battle Rope Double Waves - Wide Grip',
        'description': 'A battle rope variation where both arms move in unison with a wider grip, creating simultaneous waves. This variation emphasizes shoulder and back engagement while challenging cardiovascular endurance and full-body coordination.',
        'category': 'cardio',
        'primary_muscles': ['shoulders', 'back'],
        'secondary_muscles': ['core', 'forearms', 'glutes'],
        'equipment': [],
        'instructions': [
            'Stand with feet wider than shoulder-width, holding rope ends with arms extended',
            'Take a wider grip on the ropes than standard position',
            'Lower into a quarter squat position with core braced',
            'Simultaneously raise both arms overhead',
            'Quickly slam both ropes down together with force',
            'Create large, powerful waves moving down both ropes',
            'Maintain the wide stance and continuous motion',
            'Repeat for the prescribed duration or repetitions'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 15.59.03.png',
        'new_filename': 'battle-rope-double-waves-wide-grip.png'
    },
    {
        'name': 'Spine Traction Stretch',
        'description': 'A passive stretching exercise performed by hanging from a bar to decompress the spine and stretch the back muscles. This therapeutic movement helps improve spinal health, reduce tension, and increase flexibility in the back and shoulders.',
        'category': 'stretching',
        'primary_muscles': ['back', 'shoulders'],
        'secondary_muscles': ['core', 'forearms'],
        'equipment': [],
        'instructions': [
            'Grasp an overhead bar with both hands, palms facing forward',
            'Use a wide grip, slightly wider than shoulder-width',
            'Allow your body to hang freely, relaxing your shoulders',
            'Keep your knees together and slightly bent',
            'Let gravity gently decompress your spine',
            'Focus on relaxing all muscles and breathing deeply',
            'Hold the position for the prescribed duration',
            'Lower down gently when finished'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 15.59.26.png',
        'new_filename': 'spine-traction-stretch.png'
    },
    {
        'name': 'Reverse Grip Pull-Up',
        'description': 'A pull-up variation performed with an underhand (supinated) grip that emphasizes biceps engagement while still working the back muscles. This compound exercise builds upper body strength and is particularly effective for bicep and lat development.',
        'category': 'strength',
        'primary_muscles': ['back', 'biceps'],
        'secondary_muscles': ['forearms', 'shoulders'],
        'equipment': [],
        'instructions': [
            'Grasp the pull-up bar with an underhand grip (palms facing you)',
            'Hands should be shoulder-width apart',
            'Hang with arms fully extended and shoulders engaged',
            'Pull yourself up by driving your elbows down and back',
            'Continue until your chin clears the bar',
            'Squeeze your back and biceps at the top',
            'Lower yourself with control back to the starting position',
            'Repeat for the desired number of repetitions'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 15.59.43.png',
        'new_filename': 'reverse-grip-pull-up.png'
    },
    {
        'name': 'GHD Leg Raise - Knees Bent',
        'description': 'A core-strengthening exercise performed on a GHD (Glute-Ham Developer) bench with bent knees. This movement targets the lower abdominals and hip flexors while providing back support, making it accessible for various fitness levels.',
        'category': 'strength',
        'primary_muscles': ['core', 'hip flexors'],
        'secondary_muscles': ['quadriceps'],
        'equipment': [],
        'instructions': [
            'Position yourself on the GHD bench with your back supported',
            'Grip the handles or sides of the bench for stability',
            'Start with your knees bent and feet together',
            'Engage your core and press your lower back into the pad',
            'Raise your knees toward your chest in a controlled motion',
            'Squeeze your abs at the top of the movement',
            'Slowly lower your legs back to the starting position',
            'Maintain control throughout and avoid using momentum'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.00.06.png',
        'new_filename': 'ghd-leg-raise-knees-bent.png'
    },
    {
        'name': 'Kettlebell Swing',
        'description': 'A dynamic, explosive exercise that involves swinging a kettlebell from between the legs to chest height using hip drive. This fundamental kettlebell movement builds power, cardiovascular endurance, and strengthens the posterior chain.',
        'category': 'strength',
        'primary_muscles': ['glutes', 'hamstrings'],
        'secondary_muscles': ['core', 'back', 'shoulders'],
        'equipment': ['kettlebell'],
        'instructions': [
            'Stand with feet shoulder-width apart, kettlebell on the ground in front',
            'Hinge at the hips and grasp the kettlebell with both hands',
            'Hike the kettlebell back between your legs',
            'Explosively drive your hips forward, swinging the kettlebell up',
            'Let the kettlebell rise to chest height, arms extended',
            'Allow the kettlebell to swing back down between your legs',
            'Absorb the momentum with a hip hinge, not a squat',
            'Repeat the hip thrust for continuous swings'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.00.24.png',
        'new_filename': 'kettlebell-swing.png'
    },
    {
        'name': 'Barbell Back Squat',
        'description': 'The king of lower body exercises, the barbell back squat involves squatting with a loaded barbell resting on the upper back. This compound movement builds overall leg strength, power, and muscle mass while engaging the core and improving mobility.',
        'category': 'strength',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'core', 'calves'],
        'equipment': ['barbell'],
        'instructions': [
            'Position the barbell on your upper back across your traps',
            'Grip the bar with hands slightly wider than shoulder-width',
            'Step back and set your feet shoulder-width apart, toes slightly out',
            'Take a deep breath and brace your core',
            'Initiate the squat by breaking at the hips and knees simultaneously',
            'Descend until thighs are at least parallel to the ground',
            'Keep your chest up, knees tracking over toes',
            'Drive through your heels to return to standing',
            'Exhale at the top and repeat'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.00.41.png',
        'new_filename': 'barbell-back-squat.png'
    },
    {
        'name': 'Barbell Overhead Squat',
        'description': 'An advanced squat variation where the barbell is held overhead with locked-out arms throughout the movement. This highly technical exercise demands exceptional mobility, balance, and core stability while developing full-body strength and coordination.',
        'category': 'strength',
        'primary_muscles': ['quadriceps', 'shoulders'],
        'secondary_muscles': ['glutes', 'core', 'back'],
        'equipment': ['barbell'],
        'instructions': [
            'Start with the barbell overhead in a wide snatch grip',
            'Lock out your elbows and actively push the bar up',
            'Position feet shoulder-width apart with toes slightly out',
            'Keep your gaze forward and chest up throughout',
            'Slowly descend into a squat while keeping the bar overhead',
            'Maintain vertical torso as much as possible',
            'Squat as deep as mobility allows while keeping bar balanced',
            'Drive through your heels to return to standing',
            'Keep arms locked and bar overhead throughout the entire movement'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.00.59.png',
        'new_filename': 'barbell-overhead-squat.png'
    },
    {
        'name': 'Barbell Deadlift',
        'description': 'A fundamental compound exercise where you lift a loaded barbell from the ground to hip level. The deadlift is one of the best exercises for building overall strength, targeting the entire posterior chain and developing functional pulling power.',
        'category': 'strength',
        'primary_muscles': ['back', 'glutes', 'hamstrings'],
        'secondary_muscles': ['forearms', 'traps', 'core'],
        'equipment': ['barbell'],
        'instructions': [
            'Stand with feet hip-width apart, barbell over mid-foot',
            'Bend down and grip the bar just outside your legs',
            'Lower your hips, chest up, shoulders back, core braced',
            'Ensure your back is flat and shins are vertical',
            'Take a deep breath and drive through your heels',
            'Extend your hips and knees simultaneously to lift the bar',
            'Keep the bar close to your body as it travels up',
            'Stand tall at the top, squeezing glutes',
            'Lower the bar with control by pushing hips back first',
            'Reset your position between reps'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.01.18.png',
        'new_filename': 'barbell-deadlift.png'
    },
    {
        'name': 'Stability Ball Dumbbell Fly and Pullover',
        'description': 'A combination exercise performed on a stability ball that alternates between dumbbell flyes and pullovers. This movement targets the chest, back, and core while the unstable surface increases balance and stabilizer muscle engagement.',
        'category': 'strength',
        'primary_muscles': ['chest', 'back'],
        'secondary_muscles': ['shoulders', 'core', 'triceps'],
        'equipment': ['dumbbells', 'stability ball'],
        'instructions': [
            'Lie back on a stability ball with shoulder blades supported',
            'Hold dumbbells above your chest with a slight bend in elbows',
            'Keep your hips elevated and core engaged for stability',
            'For flyes: Open arms wide to the sides, stretching the chest',
            'Return dumbbells to center with control',
            'For pullovers: Extend arms overhead toward the ground',
            'Pull the dumbbells back over your chest',
            'Alternate between flyes and pullovers as prescribed',
            'Maintain stable hips and ball position throughout'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.01.35.png',
        'new_filename': 'stability-ball-dumbbell-fly-pullover.png'
    },
    {
        'name': 'Bulgarian Split Squat',
        'description': 'A single-leg squat variation where the rear foot is elevated on a bench or platform. This unilateral exercise builds leg strength, improves balance, and helps correct muscle imbalances while placing significant emphasis on the front leg.',
        'category': 'strength',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'core', 'calves'],
        'equipment': ['bench'],
        'instructions': [
            'Stand facing away from a bench or elevated platform',
            'Place the top of your rear foot on the bench behind you',
            'Position your front foot far enough forward for proper form',
            'Keep your torso upright and core engaged',
            'Lower your body by bending your front knee',
            'Descend until your front thigh is parallel to the ground',
            'Ensure your front knee stays aligned with your toes',
            'Push through your front heel to return to the starting position',
            'Complete all reps on one leg before switching'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.01.51.png',
        'new_filename': 'bulgarian-split-squat.png'
    },
    {
        'name': 'Back Extension',
        'description': 'A fundamental lower back exercise performed on a back extension bench (also called a hyperextension bench) that strengthens the erector spinae and posterior chain muscles. This movement is essential for building lower back strength and preventing injury.',
        'category': 'strength',
        'primary_muscles': ['lower back'],
        'secondary_muscles': ['glutes', 'hamstrings'],
        'equipment': [],
        'instructions': [
            'Position yourself on the back extension bench face down',
            'Hook your feet under the foot pads with heels secure',
            'Align your hips with the edge of the pad',
            'Cross your arms over your chest or place hands behind head',
            'Start with your upper body hanging toward the ground',
            'Engage your lower back and glutes to raise your torso',
            'Lift until your body forms a straight line',
            'Pause briefly at the top, squeezing your glutes',
            'Lower back down with control to the starting position',
            'Avoid hyperextending or arching excessively at the top'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.02.08.png',
        'new_filename': 'back-extension.png'
    },
    {
        'name': 'GHD Side Bend',
        'description': 'A lateral flexion exercise performed on a GHD bench that targets the oblique muscles. This movement strengthens the sides of the core, improves lateral stability, and helps develop a strong, balanced midsection.',
        'category': 'strength',
        'primary_muscles': ['core'],
        'secondary_muscles': ['lower back'],
        'equipment': [],
        'instructions': [
            'Position yourself sideways on the GHD bench',
            'Secure your feet under the foot pads with your side against the pad',
            'Place your hands behind your head or across your chest',
            'Keep your body in a straight line from head to feet',
            'Lower your upper body toward the ground by bending sideways',
            'Go as low as your flexibility allows while maintaining control',
            'Contract your obliques to return to the starting position',
            'Avoid rotating your torso; keep movement purely lateral',
            'Complete all reps on one side before switching'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.02.23.png',
        'new_filename': 'ghd-side-bend.png'
    },
    {
        'name': 'Barbell Hip Thrust',
        'description': 'A powerful glute-building exercise where you thrust a loaded barbell upward from a seated position with your back against a bench. This movement is highly effective for developing glute strength, size, and power while also engaging the hamstrings and core.',
        'category': 'strength',
        'primary_muscles': ['glutes'],
        'secondary_muscles': ['hamstrings', 'core'],
        'equipment': ['barbell', 'bench'],
        'instructions': [
            'Sit on the ground with your upper back against a bench',
            'Roll a loaded barbell over your legs to your hip crease',
            'Use a pad or towel on the bar for comfort',
            'Place your feet flat on the ground, hip-width apart',
            'Drive through your heels to lift your hips and the bar up',
            'Raise your hips until your body forms a straight line from shoulders to knees',
            'Squeeze your glutes hard at the top position',
            'Keep your chin tucked and core engaged',
            'Lower the bar back down with control',
            'Avoid overextending your lower back at the top'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.02.40.png',
        'new_filename': 'barbell-hip-thrust.png'
    },
    {
        'name': 'Pendulum Full Swing - Alternating Arms',
        'description': 'An advanced plyometric exercise performed on a pendulum platform that involves explosive movements with alternating arm swings. This dynamic exercise develops power, coordination, and cardiovascular endurance through full-body engagement.',
        'category': 'plyometrics',
        'primary_muscles': ['glutes', 'quadriceps'],
        'secondary_muscles': ['core', 'shoulders', 'calves'],
        'equipment': [],
        'instructions': [
            'Stand on the pendulum platform with feet shoulder-width apart',
            'Start in a squat position with weight in your heels',
            'Begin swinging one arm back in a backhand motion',
            'Explosively drive through your legs to stand up',
            'As you rise, swing the opposite arm forward and up',
            'Alternate arms with each repetition in a fluid motion',
            'Coordinate the arm swing with the squat-to-standing movement',
            'Maintain balance on the moving platform throughout',
            'Keep your core engaged for stability',
            'Continue alternating for the prescribed duration or repetitions'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.02.57.png',
        'new_filename': 'pendulum-full-swing-alternating-arms.png'
    },
    {
        'name': 'Medicine Ball French Press - Prone',
        'description': 'A triceps isolation exercise performed in a prone (plank) position with a medicine ball. This variation combines core stability with triceps strengthening, requiring you to extend your elbows while maintaining a stable plank position.',
        'category': 'strength',
        'primary_muscles': ['triceps'],
        'secondary_muscles': ['core', 'shoulders', 'chest'],
        'equipment': ['medicine ball'],
        'instructions': [
            'Start in a plank position with hands on a medicine ball',
            'Keep your body in a straight line from head to heels',
            'Engage your core and maintain stable hips',
            'Bend your elbows to lower your forearms toward the ball',
            'Keep your elbows pointing forward throughout',
            'Lower until your forearms are parallel to the ground',
            'Press through your triceps to extend your arms back to plank',
            'Maintain a rigid core throughout the movement',
            'Avoid sagging hips or piking up',
            'Repeat for the prescribed repetitions'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.03.19.png',
        'new_filename': 'medicine-ball-french-press-prone.png'
    },
    {
        'name': 'Foam Roller Spine Roll - Self Myofascial Release',
        'description': 'A self-massage technique using a foam roller to release tension in the thoracic spine and upper back muscles. This mobility and recovery exercise helps improve posture, reduce muscle tightness, and increase range of motion in the upper back.',
        'category': 'stretching',
        'primary_muscles': ['back'],
        'secondary_muscles': ['core'],
        'equipment': ['foam roller'],
        'instructions': [
            'Lie on your back with a foam roller positioned under your mid-back',
            'Cross your arms over your chest or support your head',
            'Keep your feet flat on the ground, knees bent',
            'Engage your core and lift your hips slightly off the ground',
            'Slowly roll up and down your thoracic spine',
            'Focus on areas of tightness, pausing on tender spots',
            'Avoid rolling directly on your lower back or neck',
            'Take deep breaths to help muscles relax',
            'Roll for 30-90 seconds, moving slowly and deliberately',
            'Stop on any particularly tight areas for 10-15 seconds'
        ],
        'old_filename': 'Screenshot 2026-01-10 at 16.03.36.png',
        'new_filename': 'foam-roller-spine-roll.png'
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

    # Add instructions
    for step_num, instruction in enumerate(exercise_data['instructions'], start=1):
        if dry_run:
            print(f"  [DRY RUN] Would add instruction {step_num}")
        else:
            cursor.execute('''
                INSERT INTO instructions (exercise_id, step_number, instruction)
                VALUES (?, ?, ?)
            ''', (exercise_id, step_num, instruction))

    # Rename image file
    old_path = os.path.join(images_path, exercise_data['old_filename'])
    new_path = os.path.join(images_path, exercise_data['new_filename'])

    if os.path.exists(old_path):
        if dry_run:
            print(f"  [DRY RUN] Would rename: {exercise_data['old_filename']} -> {exercise_data['new_filename']}")
        else:
            shutil.move(old_path, new_path)
            print(f"  ✓ Renamed image file")
    else:
        print(f"  ⚠ Warning: Image file not found: {old_path}")

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
    print("Exercise Migration Script")
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
