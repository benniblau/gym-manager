import sqlite3
import json
import os


def create_database(db_path='exercises.db', json_path='exercises.json'):
    """
    Creates the exercises database and populates it from the JSON file.
    If the database already exists, it will be recreated.
    """

    # Remove existing database to start fresh
    if os.path.exists(db_path):
        print(f"Existing database found at {db_path}. Recreating...")
        os.remove(db_path)

    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    print("Creating database schema...")

    # Categories table
    cursor.execute('''
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Equipment table
    cursor.execute('''
        CREATE TABLE equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Muscles table (for both primary and secondary muscles)
    cursor.execute('''
        CREATE TABLE muscles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Exercises table
    cursor.execute('''
        CREATE TABLE exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category_id INTEGER,
            description TEXT,
            video TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Instructions table (one-to-many with exercises)
    cursor.execute('''
        CREATE TABLE instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL,
            instruction TEXT NOT NULL,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
        )
    ''')

    # Junction table for exercise-equipment (many-to-many)
    cursor.execute('''
        CREATE TABLE exercise_equipment (
            exercise_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, equipment_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        )
    ''')

    # Junction table for exercise-primary_muscles (many-to-many)
    cursor.execute('''
        CREATE TABLE exercise_primary_muscles (
            exercise_id INTEGER NOT NULL,
            muscle_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, muscle_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (muscle_id) REFERENCES muscles(id)
        )
    ''')

    # Junction table for exercise-secondary_muscles (many-to-many)
    cursor.execute('''
        CREATE TABLE exercise_secondary_muscles (
            exercise_id INTEGER NOT NULL,
            muscle_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, muscle_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (muscle_id) REFERENCES muscles(id)
        )
    ''')

    # Variations table (self-referencing for exercise variations)
    cursor.execute('''
        CREATE TABLE exercise_variations (
            exercise_id INTEGER NOT NULL,
            variation_name TEXT NOT NULL,
            PRIMARY KEY (exercise_id, variation_name),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes for better query performance
    cursor.execute('CREATE INDEX idx_exercises_category ON exercises(category_id)')
    cursor.execute('CREATE INDEX idx_instructions_exercise ON instructions(exercise_id)')
    cursor.execute('CREATE INDEX idx_exercise_equipment_exercise ON exercise_equipment(exercise_id)')
    cursor.execute('CREATE INDEX idx_exercise_primary_muscles_exercise ON exercise_primary_muscles(exercise_id)')
    cursor.execute('CREATE INDEX idx_exercise_secondary_muscles_exercise ON exercise_secondary_muscles(exercise_id)')

    conn.commit()
    print("Database schema created successfully.")

    # Load and populate data from JSON
    print(f"Loading data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Insert categories
    print("Inserting categories...")
    for category in data['categories']:
        cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))

    # Insert equipment
    print("Inserting equipment...")
    for equip in data['equipment']:
        cursor.execute('INSERT OR IGNORE INTO equipment (name) VALUES (?)', (equip,))

    # Collect all unique muscles from exercises
    print("Collecting and inserting muscles...")
    muscles = set()
    for exercise in data['exercises']:
        muscles.update(exercise.get('primary_muscles', []))
        muscles.update(exercise.get('secondary_muscles', []))

    for muscle in muscles:
        cursor.execute('INSERT OR IGNORE INTO muscles (name) VALUES (?)', (muscle,))

    conn.commit()

    # Create lookup dictionaries for foreign keys
    cursor.execute('SELECT id, name FROM categories')
    category_map = {name: id for id, name in cursor.fetchall()}

    cursor.execute('SELECT id, name FROM equipment')
    equipment_map = {name: id for id, name in cursor.fetchall()}

    cursor.execute('SELECT id, name FROM muscles')
    muscle_map = {name: id for id, name in cursor.fetchall()}

    # Insert exercises and related data
    print(f"Inserting {len(data['exercises'])} exercises...")
    exercise_count = 0

    for exercise in data['exercises']:
        try:
            # Insert exercise
            category_id = category_map.get(exercise['category'])
            cursor.execute('''
                INSERT INTO exercises (name, category_id, description, video)
                VALUES (?, ?, ?, ?)
            ''', (
                exercise['name'],
                category_id,
                exercise.get('description'),
                exercise.get('video')
            ))

            exercise_id = cursor.lastrowid

            # Insert instructions
            for step_num, instruction in enumerate(exercise.get('instructions', []), start=1):
                cursor.execute('''
                    INSERT INTO instructions (exercise_id, step_number, instruction)
                    VALUES (?, ?, ?)
                ''', (exercise_id, step_num, instruction))

            # Insert equipment associations
            for equip_name in exercise.get('equipment', []):
                equip_id = equipment_map.get(equip_name)
                if equip_id:
                    cursor.execute('''
                        INSERT INTO exercise_equipment (exercise_id, equipment_id)
                        VALUES (?, ?)
                    ''', (exercise_id, equip_id))

            # Insert primary muscles
            for muscle_name in exercise.get('primary_muscles', []):
                muscle_id = muscle_map.get(muscle_name)
                if muscle_id:
                    cursor.execute('''
                        INSERT INTO exercise_primary_muscles (exercise_id, muscle_id)
                        VALUES (?, ?)
                    ''', (exercise_id, muscle_id))

            # Insert secondary muscles
            for muscle_name in exercise.get('secondary_muscles', []):
                muscle_id = muscle_map.get(muscle_name)
                if muscle_id:
                    cursor.execute('''
                        INSERT INTO exercise_secondary_muscles (exercise_id, muscle_id)
                        VALUES (?, ?)
                    ''', (exercise_id, muscle_id))

            # Insert variations (handle both 'variations_on' and 'variation_on' keys)
            variations = exercise.get('variations_on', exercise.get('variation_on', []))
            for variation in variations:
                cursor.execute('''
                    INSERT INTO exercise_variations (exercise_id, variation_name)
                    VALUES (?, ?)
                ''', (exercise_id, variation))

            exercise_count += 1

            # Commit every 100 exercises for better performance
            if exercise_count % 100 == 0:
                conn.commit()
                print(f"  Inserted {exercise_count} exercises...")

        except sqlite3.IntegrityError as e:
            print(f"  Warning: Skipping duplicate exercise '{exercise.get('name')}': {e}")
            continue

    conn.commit()
    print(f"Successfully inserted {exercise_count} exercises.")

    # Print summary statistics
    print("\nDatabase Summary:")
    cursor.execute('SELECT COUNT(*) FROM categories')
    print(f"  Categories: {cursor.fetchone()[0]}")

    cursor.execute('SELECT COUNT(*) FROM equipment')
    print(f"  Equipment types: {cursor.fetchone()[0]}")

    cursor.execute('SELECT COUNT(*) FROM muscles')
    print(f"  Muscles: {cursor.fetchone()[0]}")

    cursor.execute('SELECT COUNT(*) FROM exercises')
    print(f"  Exercises: {cursor.fetchone()[0]}")

    cursor.execute('SELECT COUNT(*) FROM instructions')
    print(f"  Instructions: {cursor.fetchone()[0]}")

    conn.close()
    print(f"\nDatabase created successfully at {db_path}")


def get_connection(db_path='exercises.db'):
    """
    Returns a connection to the database.
    Creates the database if it doesn't exist.
    """
    if not os.path.exists(db_path):
        print(f"Database not found. Creating new database at {db_path}...")
        create_database(db_path)

    return sqlite3.connect(db_path)


if __name__ == '__main__':
    # Create the database when running this script directly
    create_database()
