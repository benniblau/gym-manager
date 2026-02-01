#!/usr/bin/env python3
"""
Migration Script: Add Suspension/TRX Exercises
Date: 2026-02-01
Description: Creates a new "suspension" category and adds comprehensive TRX/suspension
             exercises with descriptions, instructions, and muscle/equipment mappings.

Usage:
    python migrations/add_suspension_exercises.py [--db-path PATH] [--dry-run]

Options:
    --db-path PATH    Path to exercises.db (default: exercises.db)
    --dry-run         Show what would be done without making changes
"""

import sqlite3
import os
import sys
import argparse

# Suspension exercises organized by body part
EXERCISES = [
    # ==================== CHEST EXERCISES ====================
    {
        'name': 'TRX Chest Press',
        'description': 'A suspension training exercise that targets the chest, shoulders, and triceps while engaging the core for stability. The unstable nature of the straps increases muscle activation compared to traditional push-ups.',
        'category': 'suspension',
        'primary_muscles': ['chest'],
        'secondary_muscles': ['shoulders', 'triceps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Adjust the TRX straps to mid-length',
            'Face away from the anchor point and grab the handles',
            'Extend your arms forward at chest height, leaning into the straps',
            'Keep your body in a straight line from head to heels',
            'Lower your chest between your hands by bending your elbows',
            'Push through your palms to return to the starting position',
            'Maintain core engagement throughout the movement'
        ]
    },
    {
        'name': 'TRX Push-Up',
        'description': 'A challenging push-up variation with feet suspended in TRX straps, dramatically increasing core engagement and shoulder stability demands while targeting the chest and triceps.',
        'category': 'suspension',
        'primary_muscles': ['chest'],
        'secondary_muscles': ['triceps', 'shoulders', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Adjust straps to mid-calf height',
            'Place feet in the foot cradles, shoelaces facing down',
            'Get into a push-up position with hands under shoulders',
            'Keep your body in a straight plank position',
            'Lower your chest toward the ground by bending elbows',
            'Press back up to the starting position',
            'Avoid letting hips sag or pike up during the movement'
        ]
    },
    {
        'name': 'TRX Chest Fly',
        'description': 'An isolation exercise for the chest muscles performed on suspension straps. The fly motion targets the pectorals through a wide arc of movement while requiring significant core stabilization.',
        'category': 'suspension',
        'primary_muscles': ['chest'],
        'secondary_muscles': ['shoulders', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Adjust straps to mid-length and face away from anchor',
            'Grab handles and extend arms out to sides at chest height',
            'Lean forward with body in a straight line',
            'Keep a slight bend in your elbows throughout',
            'Open arms wide, lowering chest between the handles',
            'Squeeze chest muscles to bring handles back together',
            'Control the movement in both directions'
        ]
    },
    {
        'name': 'TRX Decline Push-Up',
        'description': 'An advanced push-up variation with feet elevated in the straps, increasing the load on the upper chest and shoulders while challenging core stability.',
        'category': 'suspension',
        'primary_muscles': ['chest', 'shoulders'],
        'secondary_muscles': ['triceps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Set straps to approximately knee height',
            'Place feet in the foot cradles',
            'Walk hands forward until body is at a decline angle',
            'Position hands slightly wider than shoulder-width',
            'Lower chest toward the ground with control',
            'Push back up to the starting position',
            'Keep core tight to prevent excessive swinging'
        ]
    },
    {
        'name': 'TRX Atomic Push-Up',
        'description': 'An advanced combination exercise that merges a push-up with a knee tuck, providing an intense challenge for the chest, core, and hip flexors simultaneously.',
        'category': 'suspension',
        'primary_muscles': ['chest', 'abdominals'],
        'secondary_muscles': ['triceps', 'shoulders', 'hip flexors'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Get into a push-up position with hands under shoulders',
            'Perform a full push-up, lowering chest to the ground',
            'As you push up, immediately drive knees toward chest',
            'Extend legs back to plank position',
            'Repeat the push-up and knee tuck combination',
            'Maintain a controlled tempo throughout'
        ]
    },
    {
        'name': 'TRX Single Arm Chest Press',
        'description': 'An advanced unilateral chest press that challenges anti-rotation strength and creates significant muscle imbalance correction. Requires exceptional core stability.',
        'category': 'suspension',
        'primary_muscles': ['chest'],
        'secondary_muscles': ['shoulders', 'triceps', 'abdominals', 'obliques'],
        'equipment': ['Strap'],
        'instructions': [
            'Grab one TRX handle with one hand',
            'Face away from the anchor point',
            'Extend arm forward and lean into the strap',
            'Place free hand on hip or behind back',
            'Lower chest toward the working hand',
            'Press back to starting position without rotating torso',
            'Complete all reps on one side before switching'
        ]
    },

    # ==================== CORE EXERCISES ====================
    {
        'name': 'TRX Plank',
        'description': 'A core stabilization exercise with feet suspended in straps, significantly increasing the challenge compared to a floor plank due to the unstable surface.',
        'category': 'suspension',
        'primary_muscles': ['abdominals'],
        'secondary_muscles': ['shoulders', 'glutes', 'lower back'],
        'equipment': ['Strap'],
        'instructions': [
            'Adjust straps to mid-calf height',
            'Place feet in the foot cradles',
            'Position yourself face down in a plank position',
            'Keep forearms on the ground, elbows under shoulders',
            'Maintain a straight line from head to heels',
            'Engage core and glutes to prevent sagging',
            'Hold for the prescribed duration'
        ]
    },
    {
        'name': 'TRX Mountain Climber',
        'description': 'A dynamic core exercise combining plank stability with alternating knee drives. The suspended feet increase core engagement and add a cardiovascular component.',
        'category': 'suspension',
        'primary_muscles': ['abdominals', 'hip flexors'],
        'secondary_muscles': ['shoulders', 'quadriceps'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Get into a push-up plank position',
            'Drive one knee toward your chest',
            'Return that leg and immediately drive the other knee',
            'Alternate legs in a running motion',
            'Keep hips level and core engaged',
            'Maintain a steady, controlled pace'
        ]
    },
    {
        'name': 'TRX Pike',
        'description': 'An advanced core exercise where you lift your hips toward the ceiling while keeping legs straight, intensely targeting the abs and hip flexors.',
        'category': 'suspension',
        'primary_muscles': ['abdominals'],
        'secondary_muscles': ['hip flexors', 'shoulders'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Start in a push-up plank position',
            'Keep legs straight and lift hips toward the ceiling',
            'Pike up until your body forms an inverted V',
            'Lower hips back to plank with control',
            'Keep core engaged throughout the movement',
            'Avoid bending knees during the pike'
        ]
    },
    {
        'name': 'TRX Body Saw',
        'description': 'A challenging plank variation where you rock your body forward and backward, creating constant tension on the core muscles through the full range of motion.',
        'category': 'suspension',
        'primary_muscles': ['abdominals'],
        'secondary_muscles': ['shoulders', 'lats', 'lower back'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Get into a forearm plank position',
            'Push your body backward, extending shoulders',
            'Pull your body forward past starting position',
            'Rock back and forth in a sawing motion',
            'Keep core braced and body in a straight line',
            'Control the movement in both directions'
        ]
    },
    {
        'name': 'TRX Pendulum',
        'description': 'A rotational core exercise where you swing your legs side to side while in a plank position, targeting the obliques and anti-rotation muscles.',
        'category': 'suspension',
        'primary_muscles': ['obliques', 'abdominals'],
        'secondary_muscles': ['hip flexors', 'shoulders'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Get into a push-up plank position',
            'Keep legs together and swing them to one side',
            'Return to center and swing to the other side',
            'Keep upper body stable and facing down',
            'Control the swinging motion with your core',
            'Avoid rotating your shoulders'
        ]
    },
    {
        'name': 'TRX Suspended Crunch',
        'description': 'A crunch variation with feet suspended, allowing for a greater range of motion and increased core activation compared to floor crunches.',
        'category': 'suspension',
        'primary_muscles': ['abdominals'],
        'secondary_muscles': ['hip flexors'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Start in a push-up plank position',
            'Keep arms straight and shoulders over wrists',
            'Drive both knees toward your chest',
            'Squeeze abs at the peak contraction',
            'Extend legs back to plank position',
            'Maintain controlled movement throughout'
        ]
    },

    # ==================== ARM EXERCISES ====================
    {
        'name': 'TRX Bicep Curl',
        'description': 'An effective bicep isolation exercise using body weight and suspension straps. The angle of lean determines the difficulty level.',
        'category': 'suspension',
        'primary_muscles': ['biceps'],
        'secondary_muscles': ['forearms', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor point and grab handles with underhand grip',
            'Lean back with arms extended, body in a straight line',
            'Keep elbows high and fixed in position',
            'Curl your body toward the handles by bending elbows',
            'Squeeze biceps at the top of the movement',
            'Lower back with control to starting position',
            'Walk feet closer to anchor to increase difficulty'
        ]
    },
    {
        'name': 'TRX Tricep Extension',
        'description': 'A tricep isolation exercise using suspension straps that targets all three heads of the triceps while engaging the core for stability.',
        'category': 'suspension',
        'primary_muscles': ['triceps'],
        'secondary_muscles': ['abdominals', 'shoulders'],
        'equipment': ['Strap'],
        'instructions': [
            'Face away from the anchor point',
            'Grab handles with overhand grip, arms extended overhead',
            'Lean forward with body in a straight line',
            'Bend elbows to lower your head between your hands',
            'Keep elbows close together and pointing forward',
            'Extend arms to press back to starting position',
            'Control the movement to avoid swinging'
        ]
    },
    {
        'name': 'TRX Skull Crusher',
        'description': 'A tricep exercise mimicking the traditional skull crusher but performed on suspension straps with your own body weight providing resistance.',
        'category': 'suspension',
        'primary_muscles': ['triceps'],
        'secondary_muscles': ['abdominals', 'shoulders'],
        'equipment': ['Strap'],
        'instructions': [
            'Face away from the anchor and grab handles',
            'Extend arms forward at forehead height',
            'Lean forward, keeping body straight',
            'Bend elbows to bring forehead toward handles',
            'Keep upper arms stationary throughout',
            'Extend elbows to return to start',
            'Maintain core engagement for stability'
        ]
    },
    {
        'name': 'TRX Hammer Curl',
        'description': 'A bicep curl variation with neutral grip that targets the brachialis and brachioradialis in addition to the biceps.',
        'category': 'suspension',
        'primary_muscles': ['biceps'],
        'secondary_muscles': ['forearms', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and grab handles with neutral grip',
            'Palms should face each other throughout',
            'Lean back with arms extended',
            'Curl body toward handles by bending elbows',
            'Keep elbows fixed at shoulder height',
            'Squeeze at the top and lower with control',
            'Maintain straight body alignment'
        ]
    },
    {
        'name': 'TRX Single Arm Bicep Curl',
        'description': 'An advanced unilateral bicep exercise that requires significant core stabilization to prevent rotation while isolating each arm.',
        'category': 'suspension',
        'primary_muscles': ['biceps'],
        'secondary_muscles': ['forearms', 'abdominals', 'obliques'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and grab one handle',
            'Extend arm fully and lean back',
            'Place free hand on hip or behind back',
            'Curl body toward the handle',
            'Prevent torso rotation during the curl',
            'Lower with control to full extension',
            'Complete all reps before switching arms'
        ]
    },
    {
        'name': 'TRX Power Pull',
        'description': 'A dynamic pulling exercise that combines a single-arm row with a rotational reach, developing pulling strength and rotational power.',
        'category': 'suspension',
        'primary_muscles': ['back', 'biceps'],
        'secondary_muscles': ['obliques', 'shoulders'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and grab one handle',
            'Lean back with arm extended, free arm reaching toward anchor',
            'Pull body up while rotating torso open',
            'Reach free arm toward the ceiling at the top',
            'Rotate back down, reaching free arm toward anchor',
            'Control the rotation through your core',
            'Complete all reps then switch sides'
        ]
    },

    # ==================== LEG EXERCISES ====================
    {
        'name': 'TRX Squat',
        'description': 'An assisted squat using TRX straps for balance and support, perfect for learning proper squat mechanics or as a rehabilitation exercise.',
        'category': 'suspension',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and hold both handles',
            'Stand with feet shoulder-width apart',
            'Keep arms extended with slight tension in straps',
            'Lower into a squat, pushing hips back',
            'Use straps for balance, not to pull yourself up',
            'Descend until thighs are parallel to ground',
            'Drive through heels to return to standing'
        ]
    },
    {
        'name': 'TRX Lunge',
        'description': 'A lunge variation using TRX straps for balance support, allowing focus on proper form and deeper range of motion.',
        'category': 'suspension',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and hold both handles',
            'Step one foot back into a lunge stance',
            'Lower back knee toward the ground',
            'Keep front knee aligned over ankle',
            'Use straps lightly for balance',
            'Push through front heel to return to start',
            'Complete all reps then switch legs'
        ]
    },
    {
        'name': 'TRX Single Leg Squat',
        'description': 'A challenging single-leg squat using the straps for balance assistance, developing unilateral leg strength and stability.',
        'category': 'suspension',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'abdominals', 'hip flexors'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and hold both handles',
            'Lift one foot off the ground in front of you',
            'Lower into a single-leg squat on standing leg',
            'Use straps for balance assistance as needed',
            'Descend as low as flexibility allows',
            'Push through heel to return to standing',
            'Keep lifted leg extended throughout'
        ]
    },
    {
        'name': 'TRX Hamstring Curl',
        'description': 'A lying hamstring exercise with feet in the straps, effectively targeting the hamstrings and glutes through hip extension and knee flexion.',
        'category': 'suspension',
        'primary_muscles': ['hamstrings'],
        'secondary_muscles': ['glutes', 'calves', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Lie on your back with feet in the foot cradles',
            'Lift hips off the ground into a bridge position',
            'Keep body straight from shoulders to knees',
            'Pull heels toward your glutes by bending knees',
            'Squeeze hamstrings at peak contraction',
            'Extend legs back to starting position',
            'Keep hips elevated throughout the movement'
        ]
    },
    {
        'name': 'TRX Pistol Squat',
        'description': 'An advanced single-leg squat to full depth with the non-working leg extended forward, using straps for minimal assistance.',
        'category': 'suspension',
        'primary_muscles': ['quadriceps', 'glutes'],
        'secondary_muscles': ['hamstrings', 'abdominals', 'hip flexors'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor holding both handles',
            'Extend one leg straight out in front',
            'Lower into a full single-leg squat',
            'Descend until hamstring touches calf',
            'Use straps minimally for balance only',
            'Drive through heel to stand back up',
            'Keep extended leg parallel to ground throughout'
        ]
    },
    {
        'name': 'TRX Sprinter Start',
        'description': 'An explosive lower body exercise simulating a sprinter starting position, developing power and hip drive.',
        'category': 'suspension',
        'primary_muscles': ['glutes', 'quadriceps'],
        'secondary_muscles': ['hamstrings', 'calves', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and hold handles at chest height',
            'Step back into a deep lunge position',
            'Back knee should be close to the ground',
            'Explosively drive forward, bringing back knee up',
            'Drive knee toward chest with power',
            'Return to deep lunge position with control',
            'Complete all reps then switch legs'
        ]
    },

    # ==================== SHOULDER EXERCISES ====================
    {
        'name': 'TRX Y Fly',
        'description': 'A posterior shoulder exercise where arms move into a Y position, targeting the rear deltoids and upper back muscles.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['back', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles in hands',
            'Lean back with arms extended forward',
            'Keep body in a straight line',
            'Pull arms up and out into a Y position',
            'Squeeze shoulder blades together at the top',
            'Lower with control back to starting position',
            'Keep arms straight throughout the movement'
        ]
    },
    {
        'name': 'TRX T Fly',
        'description': 'A rear deltoid exercise where arms extend straight out to the sides, forming a T shape to target the posterior shoulders.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['back', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles in hands',
            'Lean back with arms extended forward',
            'Keep body in a straight line',
            'Pull arms straight out to sides forming a T',
            'Keep arms at shoulder height',
            'Squeeze rear delts and upper back',
            'Lower with control to starting position'
        ]
    },
    {
        'name': 'TRX I Fly',
        'description': 'An overhead pulling movement where arms extend straight up above the head, targeting the shoulders and upper back.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['back', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles in hands',
            'Lean back with arms extended forward',
            'Keep body in a straight line',
            'Pull arms straight overhead forming an I',
            'Arms should end up beside your ears',
            'Squeeze shoulders at the top position',
            'Lower with control to starting position'
        ]
    },
    {
        'name': 'TRX W Fly',
        'description': 'A rear deltoid exercise targeting the rotator cuff and rear shoulders by pulling into a W position with bent elbows.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['back', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles in hands',
            'Lean back with arms extended forward',
            'Pull elbows back and out to form a W',
            'Rotate forearms to point toward ceiling',
            'Squeeze shoulder blades and rear delts',
            'Keep elbows at 90 degrees at the top',
            'Lower with control to starting position'
        ]
    },
    {
        'name': 'TRX Deltoid Fly',
        'description': 'An advanced rear deltoid isolation exercise requiring significant shoulder strength and stability.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['back', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles in hands',
            'Start with arms crossed in front of body',
            'Lean back maintaining straight body line',
            'Open arms wide to the sides uncrossing them',
            'Pull shoulder blades together',
            'Return arms to crossed position with control',
            'Keep arms nearly straight throughout'
        ]
    },
    {
        'name': 'TRX Overhead Press',
        'description': 'A challenging shoulder press using suspension straps, targeting the deltoids while requiring significant core stabilization.',
        'category': 'suspension',
        'primary_muscles': ['shoulders'],
        'secondary_muscles': ['triceps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face away from the anchor',
            'Hold handles at shoulder height, elbows bent',
            'Lean forward with body in a straight line',
            'Press handles overhead by extending arms',
            'Bring arms together at the top',
            'Lower with control back to shoulder height',
            'Keep core engaged to prevent arching'
        ]
    },

    # ==================== BACK EXERCISES ====================
    {
        'name': 'TRX Low Row',
        'description': 'A fundamental pulling exercise targeting the mid-back, lats, and biceps. Difficulty is adjusted by changing body angle.',
        'category': 'suspension',
        'primary_muscles': ['back', 'lats'],
        'secondary_muscles': ['biceps', 'shoulders', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and grab handles',
            'Lean back with arms extended',
            'Keep body in a straight line',
            'Pull chest toward handles',
            'Keep elbows close to your sides',
            'Squeeze shoulder blades together at the top',
            'Lower with control to starting position'
        ]
    },
    {
        'name': 'TRX High Row',
        'description': 'A rowing variation with elbows held high, emphasizing the rear deltoids and upper back muscles.',
        'category': 'suspension',
        'primary_muscles': ['back', 'shoulders'],
        'secondary_muscles': ['biceps', 'traps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor and grab handles',
            'Lean back with arms extended at face height',
            'Keep body in a straight line',
            'Pull elbows wide and high toward shoulders',
            'Keep hands at face level throughout',
            'Squeeze rear delts and upper back',
            'Lower with control to starting position'
        ]
    },
    {
        'name': 'TRX Face Pull',
        'description': 'An upper back and rear deltoid exercise pulling toward the face with external rotation, excellent for shoulder health.',
        'category': 'suspension',
        'primary_muscles': ['shoulders', 'back'],
        'secondary_muscles': ['traps', 'biceps', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor with handles at face height',
            'Lean back with arms extended forward',
            'Pull handles toward your face',
            'Separate hands and rotate externally',
            'Finish with hands beside ears, elbows high',
            'Squeeze rear delts and upper back',
            'Return to start with control'
        ]
    },
    {
        'name': 'TRX Single Arm Row',
        'description': 'A unilateral rowing exercise that challenges core stability and anti-rotation while building back strength.',
        'category': 'suspension',
        'primary_muscles': ['back', 'lats'],
        'secondary_muscles': ['biceps', 'obliques', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor holding one handle',
            'Extend arm and lean back',
            'Place free hand on hip',
            'Pull chest toward the handle',
            'Keep body from rotating during the pull',
            'Squeeze lat and middle back at the top',
            'Complete all reps then switch arms'
        ]
    },
    {
        'name': 'TRX Pull-Up',
        'description': 'A vertical pulling exercise using TRX straps, allowing for assisted or full pull-ups with adjustable difficulty.',
        'category': 'suspension',
        'primary_muscles': ['lats', 'back'],
        'secondary_muscles': ['biceps', 'shoulders', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Shorten straps and position under anchor',
            'Grab handles with overhand grip',
            'Hang with arms fully extended',
            'Pull body up toward the handles',
            'Drive elbows down and back',
            'Chin should reach handle height',
            'Lower with control to full extension'
        ]
    },
    {
        'name': 'TRX Archer Row',
        'description': 'An advanced rowing variation where one arm pulls while the other extends, creating a powerful unilateral pulling movement.',
        'category': 'suspension',
        'primary_muscles': ['back', 'lats'],
        'secondary_muscles': ['biceps', 'shoulders', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor holding both handles',
            'Lean back with arms extended',
            'Pull one arm to your side while extending the other',
            'The extending arm should straighten completely',
            'Rotate torso slightly toward the pulling arm',
            'Return to center and alternate sides',
            'Control the movement throughout'
        ]
    },

    # ==================== FULL BODY EXERCISES ====================
    {
        'name': 'TRX Burpee',
        'description': 'A challenging full-body exercise combining a suspended push-up with a knee tuck, providing cardio and strength benefits.',
        'category': 'suspension',
        'primary_muscles': ['chest', 'abdominals'],
        'secondary_muscles': ['shoulders', 'triceps', 'hip flexors', 'quadriceps'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Start in a push-up plank position',
            'Perform a push-up',
            'As you press up, drive knees to chest',
            'Extend legs back to plank',
            'Immediately perform next push-up',
            'Continue with fluid movement'
        ]
    },
    {
        'name': 'TRX Crossing Balance Lunge',
        'description': 'A dynamic lunge variation that crosses behind the body while holding TRX straps, challenging balance and hip mobility.',
        'category': 'suspension',
        'primary_muscles': ['glutes', 'quadriceps'],
        'secondary_muscles': ['hamstrings', 'abdominals', 'adductors'],
        'equipment': ['Strap'],
        'instructions': [
            'Face the anchor holding both handles',
            'Stand on one leg with slight tension in straps',
            'Step the free leg behind and across your body',
            'Lower into a curtsy lunge position',
            'Keep front knee tracking over toes',
            'Push through front heel to return to start',
            'Complete all reps then switch legs'
        ]
    },
    {
        'name': 'TRX Spiderman Push-Up',
        'description': 'An advanced push-up variation with feet suspended, adding a knee drive to the side that mimics a spider climbing motion.',
        'category': 'suspension',
        'primary_muscles': ['chest', 'obliques'],
        'secondary_muscles': ['shoulders', 'triceps', 'hip flexors', 'abdominals'],
        'equipment': ['Strap'],
        'instructions': [
            'Place feet in the TRX foot cradles',
            'Get into a push-up position',
            'As you lower into the push-up, drive one knee to elbow',
            'Push up while returning leg to center',
            'Alternate legs with each push-up',
            'Keep hips level throughout the movement',
            'Maintain controlled tempo'
        ]
    }
]


def get_db_connection(db_path):
    """Create database connection"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")
    return sqlite3.connect(db_path)


def category_exists(cursor, category_name):
    """Check if category already exists"""
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    return cursor.fetchone()


def create_category(cursor, category_name):
    """Create a new category and return its ID"""
    cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
    return cursor.lastrowid


def get_category_id(cursor, category_name):
    """Get category ID by name, creating if needed"""
    result = category_exists(cursor, category_name)
    if result:
        return result[0]
    return create_category(cursor, category_name)


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


def exercise_exists(cursor, exercise_name):
    """Check if exercise already exists"""
    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    return cursor.fetchone() is not None


def get_next_exercise_id(cursor):
    """Get the next available exercise ID"""
    cursor.execute("SELECT MAX(id) FROM exercises")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1


def add_exercise(cursor, exercise_data, exercise_id, category_id, dry_run=False):
    """Add a single exercise to the database"""
    print(f"\nAdding: {exercise_data['name']} (ID: {exercise_id})")

    if dry_run:
        print(f"  [DRY RUN] Would insert exercise with category_id={category_id}")
    else:
        cursor.execute('''
            INSERT INTO exercises (id, name, description, category_id)
            VALUES (?, ?, ?, ?)
        ''', (
            exercise_id,
            exercise_data['name'],
            exercise_data['description'],
            category_id
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
        equipment_id = get_equipment_id(cursor, equipment_name)
        if equipment_id:
            if dry_run:
                print(f"  [DRY RUN] Would add equipment: {equipment_name}")
            else:
                cursor.execute('''
                    INSERT INTO exercise_equipment (exercise_id, equipment_id)
                    VALUES (?, ?)
                ''', (exercise_id, equipment_id))

    # Add instructions
    for step_num, instruction in enumerate(exercise_data['instructions'], start=1):
        if dry_run:
            print(f"  [DRY RUN] Would add instruction {step_num}")
        else:
            cursor.execute('''
                INSERT INTO instructions (exercise_id, step_number, instruction)
                VALUES (?, ?, ?)
            ''', (exercise_id, step_num, instruction))

    print(f"  Added successfully")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Add suspension/TRX exercises to database')
    parser.add_argument('--db-path', default='exercises.db', help='Path to database file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Suspension Exercises Migration Script")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    print(f"Exercises to add: {len(EXERCISES)}")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    print("=" * 60)

    try:
        conn = get_db_connection(args.db_path)
        cursor = conn.cursor()

        # Create or get suspension category
        print("\nChecking suspension category...")
        if category_exists(cursor, 'suspension'):
            print("  Category 'suspension' already exists")
            category_id = get_category_id(cursor, 'suspension')
        else:
            if args.dry_run:
                print("  [DRY RUN] Would create 'suspension' category")
                category_id = 999  # Placeholder for dry run
            else:
                category_id = create_category(cursor, 'suspension')
                print(f"  Created 'suspension' category (ID: {category_id})")

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
                add_exercise(cursor, exercise_data, exercise_id, category_id, args.dry_run)
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
