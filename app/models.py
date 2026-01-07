import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


def get_db():
    """Get database connection, reuse within request context"""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_PATH'])
        g.db.row_factory = sqlite3.Row  # Access columns by name
    return g.db


def close_db(e=None):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


class User:
    """User model for authentication"""

    def __init__(self, id, username, email, password_hash, created_at, last_login):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.last_login = last_login

    @staticmethod
    def get_by_id(user_id):
        """Retrieve user by ID"""
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None

    @staticmethod
    def get_by_username(username):
        """Retrieve user by username"""
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None

    @staticmethod
    def get_by_email(email):
        """Retrieve user by email"""
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None

    @staticmethod
    def create(username, email, password):
        """Create new user"""
        db = get_db()
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        db.commit()
        return User.get_by_id(cursor.lastrowid)

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Update last login timestamp"""
        db = get_db()
        db.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.now(), self.id)
        )
        db.commit()

    def update_email(self, new_email):
        """Update user email"""
        db = get_db()
        db.execute(
            'UPDATE users SET email = ? WHERE id = ?',
            (new_email, self.id)
        )
        db.commit()
        self.email = new_email

    def update_password(self, new_password):
        """Update user password"""
        from app import bcrypt
        password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db = get_db()
        db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (password_hash, self.id)
        )
        db.commit()
        self.password_hash = password_hash

    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Workout:
    """Workout model"""

    def __init__(self, id, user_id, name, scheduled_date, scheduled_time=None,
                 notes=None, status='planned', started_at=None, completed_at=None,
                 is_template=0, created_at=None, updated_at=None, is_public=0, usage_count=0,
                 duration_minutes=None, end_date=None, end_time=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.scheduled_date = scheduled_date
        self.scheduled_time = scheduled_time
        self.duration_minutes = duration_minutes
        self.end_date = end_date
        self.end_time = end_time
        self.notes = notes
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.is_template = is_template
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_public = is_public
        self.usage_count = usage_count

    @staticmethod
    def get_by_id(workout_id):
        """Retrieve workout by ID"""
        db = get_db()
        row = db.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,)).fetchone()
        if row:
            return Workout(**dict(row))
        return None

    @staticmethod
    def get_by_user(user_id, limit=50, offset=0):
        """Get all workouts for a user"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ?
            ORDER BY scheduled_date DESC, scheduled_time DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def get_recent_by_user(user_id, limit=10):
        """Get recent workouts for a user"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ?
            ORDER BY scheduled_date DESC, scheduled_time DESC
            LIMIT ?
        ''', (user_id, limit)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def get_by_date(user_id, date):
        """Get workouts for a specific date"""
        db = get_db()
        # Convert date to string for SQLite comparison
        if hasattr(date, 'isoformat'):
            date = date.isoformat()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ? AND scheduled_date = ?
            ORDER BY scheduled_time
        ''', (user_id, date)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def create(user_id, name, scheduled_date, **kwargs):
        """Create new workout"""
        db = get_db()

        # Convert date to string for SQLite
        if hasattr(scheduled_date, 'isoformat'):
            scheduled_date = scheduled_date.isoformat()

        # Convert time to string for SQLite (if provided)
        scheduled_time = kwargs.get('scheduled_time')
        if scheduled_time and hasattr(scheduled_time, 'isoformat'):
            scheduled_time = scheduled_time.isoformat()

        # Convert end_date to string for SQLite (if provided)
        end_date = kwargs.get('end_date')
        if end_date and hasattr(end_date, 'isoformat'):
            end_date = end_date.isoformat()

        # Convert end_time to string for SQLite (if provided)
        end_time = kwargs.get('end_time')
        if end_time and hasattr(end_time, 'isoformat'):
            end_time = end_time.isoformat()

        cursor = db.execute('''
            INSERT INTO workouts (user_id, name, scheduled_date, scheduled_time, duration_minutes,
                                 end_date, end_time, notes, status, is_template)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, name, scheduled_date,
            scheduled_time,
            kwargs.get('duration_minutes'),
            end_date,
            end_time,
            kwargs.get('notes'),
            kwargs.get('status', 'planned'),
            kwargs.get('is_template', 0)
        ))
        db.commit()
        return Workout.get_by_id(cursor.lastrowid)

    def update(self, **kwargs):
        """Update workout fields"""
        db = get_db()

        # Build dynamic UPDATE query
        fields = []
        values = []

        for key in ['name', 'scheduled_date', 'scheduled_time', 'notes', 'status', 'started_at', 'completed_at']:
            if key in kwargs:
                value = kwargs[key]
                # Convert date/time/datetime objects to strings for SQLite
                if value and hasattr(value, 'isoformat'):
                    value = value.isoformat()
                fields.append(f'{key} = ?')
                values.append(value)

        if fields:
            fields.append('updated_at = ?')
            values.append(datetime.now().isoformat())
            values.append(self.id)

            query = f"UPDATE workouts SET {', '.join(fields)} WHERE id = ?"
            db.execute(query, values)
            db.commit()

    def delete(self):
        """Delete workout"""
        db = get_db()
        db.execute('DELETE FROM workouts WHERE id = ?', (self.id,))
        db.commit()

    def get_exercises(self):
        """Get all exercises in this workout"""
        return WorkoutExercise.get_by_workout(self.id)

    @staticmethod
    def get_templates_by_user(user_id, limit=50, offset=0):
        """Get all workout templates for a user"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ? AND is_template = 1
            ORDER BY name ASC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def create_template(user_id, name, notes=None, is_public=0):
        """Create a new workout template"""
        db = get_db()
        cursor = db.execute('''
            INSERT INTO workouts (user_id, name, scheduled_date, scheduled_time, notes, is_template, status, is_public, usage_count)
            VALUES (?, ?, NULL, NULL, ?, 1, 'planned', ?, 0)
        ''', (user_id, name, notes, is_public))
        db.commit()
        return Workout.get_by_id(cursor.lastrowid)

    @staticmethod
    def create_from_template(template_id, user_id, scheduled_date, scheduled_time=None,
                            duration_minutes=None, end_date=None, end_time=None, notes=None):
        """Create a new workout from a template"""
        # Get template
        template = Workout.get_by_id(template_id)

        if not template:
            raise ValueError("Template not found")

        if not template.is_template:
            raise ValueError("Workout is not a template")

        # Verify ownership OR public access
        if template.user_id != user_id and not template.is_public:
            raise ValueError("Template is private and does not belong to user")

        # Create new workout with template's name
        workout = Workout.create(
            user_id=user_id,
            name=template.name,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            end_date=end_date,
            end_time=end_time,
            notes=notes or template.notes
        )

        # Copy exercises from template
        template_exercises = template.get_exercises()
        for ex in template_exercises:
            WorkoutExercise.add_to_workout(
                workout_id=workout.id,
                exercise_id=ex['exercise_id'],
                order_position=ex['order_position'],
                target_sets=ex['target_sets'],
                target_reps=ex['target_reps'],
                target_weight=ex['target_weight'],
                target_duration=ex['target_duration'],
                notes=ex['notes']
            )

        # Increment usage count
        template.increment_usage_count()

        return workout

    @staticmethod
    def get_public_templates(order_by='usage_count', limit=50, offset=0):
        """Get all public templates with creator information"""
        db = get_db()

        # Determine ORDER BY clause
        order_clauses = {
            'usage_count': 'w.usage_count DESC, w.name ASC',
            'name': 'w.name ASC',
            'created_at': 'w.created_at DESC'
        }
        order_clause = order_clauses.get(order_by, order_clauses['usage_count'])

        rows = db.execute(f'''
            SELECT w.*, u.username as creator_username
            FROM workouts w
            JOIN users u ON w.user_id = u.id
            WHERE w.is_template = 1 AND w.is_public = 1
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def get_template_with_creator(template_id):
        """Get a single template with creator information"""
        db = get_db()
        row = db.execute('''
            SELECT w.*, u.username as creator_username
            FROM workouts w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = ? AND w.is_template = 1
        ''', (template_id,)).fetchone()

        return dict(row) if row else None

    def toggle_public(self):
        """Toggle template between public and private"""
        if not self.is_template:
            raise ValueError("Only templates can be made public/private")

        db = get_db()
        new_status = 0 if self.is_public else 1

        db.execute('''
            UPDATE workouts
            SET is_public = ?, updated_at = ?
            WHERE id = ?
        ''', (new_status, datetime.now().isoformat(), self.id))
        db.commit()

        self.is_public = new_status
        return new_status

    def increment_usage_count(self):
        """Increment the usage count for this template"""
        if not self.is_template:
            return

        db = get_db()
        db.execute('''
            UPDATE workouts
            SET usage_count = usage_count + 1
            WHERE id = ?
        ''', (self.id,))
        db.commit()

        self.usage_count += 1

    def convert_to_template(self):
        """Convert an existing workout to a template"""
        db = get_db()
        db.execute('''
            UPDATE workouts
            SET is_template = 1, scheduled_date = NULL, scheduled_time = NULL,
                status = 'planned', started_at = NULL, completed_at = NULL
            WHERE id = ?
        ''', (self.id,))
        db.commit()

        # Clear actual values from exercises
        db.execute('''
            UPDATE workout_exercises
            SET actual_sets = NULL, actual_reps = NULL, actual_weight = NULL
            WHERE workout_id = ?
        ''', (self.id,))
        db.commit()

        self.is_template = 1


class WorkoutExercise:
    """Workout exercise junction table model"""

    @staticmethod
    def get_by_workout(workout_id):
        """Get all exercises for a workout with exercise details"""
        db = get_db()
        rows = db.execute('''
            SELECT we.*,
                   e.name as exercise_name,
                   e.description as exercise_description,
                   c.name as category_name,
                   GROUP_CONCAT(m.name, ', ') as primary_muscles
            FROM workout_exercises we
            JOIN exercises e ON we.exercise_id = e.id
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN exercise_primary_muscles epm ON e.id = epm.exercise_id
            LEFT JOIN muscles m ON epm.muscle_id = m.id
            WHERE we.workout_id = ?
            GROUP BY we.id
            ORDER BY we.order_position
        ''', (workout_id,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(workout_exercise_id):
        """Get a specific workout exercise"""
        db = get_db()
        row = db.execute('''
            SELECT we.*, e.name as exercise_name
            FROM workout_exercises we
            JOIN exercises e ON we.exercise_id = e.id
            WHERE we.id = ?
        ''', (workout_exercise_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def add_to_workout(workout_id, exercise_id, order_position, **kwargs):
        """Add exercise to workout"""
        db = get_db()
        cursor = db.execute('''
            INSERT INTO workout_exercises
            (workout_id, exercise_id, order_position, target_sets, target_reps, target_weight, target_duration, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            workout_id, exercise_id, order_position,
            kwargs.get('target_sets'),
            kwargs.get('target_reps'),
            kwargs.get('target_weight'),
            kwargs.get('target_duration'),
            kwargs.get('notes')
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_next_order_position(workout_id):
        """Get the next order position for a workout"""
        db = get_db()
        row = db.execute('''
            SELECT MAX(order_position) as max_pos
            FROM workout_exercises
            WHERE workout_id = ?
        ''', (workout_id,)).fetchone()
        return (row['max_pos'] or 0) + 1

    @staticmethod
    def update(workout_exercise_id, **kwargs):
        """Update workout exercise"""
        db = get_db()

        fields = []
        values = []

        for key in ['actual_sets', 'actual_reps', 'actual_weight', 'actual_duration', 'target_sets', 'target_reps', 'target_weight', 'target_duration', 'notes', 'order_position']:
            if key in kwargs:
                fields.append(f'{key} = ?')
                values.append(kwargs[key])

        if fields:
            fields.append('updated_at = ?')
            values.append(datetime.now())
            values.append(workout_exercise_id)

            query = f"UPDATE workout_exercises SET {', '.join(fields)} WHERE id = ?"
            db.execute(query, values)
            db.commit()

    @staticmethod
    def delete(workout_exercise_id):
        """Remove exercise from workout"""
        db = get_db()
        db.execute('DELETE FROM workout_exercises WHERE id = ?', (workout_exercise_id,))
        db.commit()

    @staticmethod
    def reorder(workout_exercise_id, direction):
        """Reorder exercise in workout (move up or down)"""
        db = get_db()

        # Get current exercise
        current = db.execute('''
            SELECT id, workout_id, order_position
            FROM workout_exercises
            WHERE id = ?
        ''', (workout_exercise_id,)).fetchone()

        if not current:
            return

        current_pos = current['order_position']
        workout_id = current['workout_id']

        # Find the exercise to swap with
        if direction == 'up':
            swap_exercise = db.execute('''
                SELECT id, order_position
                FROM workout_exercises
                WHERE workout_id = ? AND order_position < ?
                ORDER BY order_position DESC
                LIMIT 1
            ''', (workout_id, current_pos)).fetchone()
        else:  # down
            swap_exercise = db.execute('''
                SELECT id, order_position
                FROM workout_exercises
                WHERE workout_id = ? AND order_position > ?
                ORDER BY order_position ASC
                LIMIT 1
            ''', (workout_id, current_pos)).fetchone()

        if not swap_exercise:
            return  # Already at the top or bottom

        swap_pos = swap_exercise['order_position']

        # Swap positions
        db.execute('''
            UPDATE workout_exercises
            SET order_position = ?
            WHERE id = ?
        ''', (swap_pos, workout_exercise_id))

        db.execute('''
            UPDATE workout_exercises
            SET order_position = ?
            WHERE id = ?
        ''', (current_pos, swap_exercise['id']))

        db.commit()


class Exercise:
    """Exercise model (read-only, from existing database)"""

    @staticmethod
    def get_by_id(exercise_id):
        """Get exercise by ID with full details"""
        db = get_db()

        # Get basic exercise info
        exercise = db.execute('''
            SELECT e.*, c.name as category_name
            FROM exercises e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.id = ?
        ''', (exercise_id,)).fetchone()

        if not exercise:
            return None

        exercise_dict = dict(exercise)

        # Prepend /static/images/ to image URLs only if they are local filenames (not paths or URLs)
        if exercise_dict.get('image1_url'):
            url = exercise_dict['image1_url']
            if not url.startswith('/') and not url.startswith('http'):
                exercise_dict['image1_url'] = f"/static/images/{url}"
        if exercise_dict.get('image2_url'):
            url = exercise_dict['image2_url']
            if not url.startswith('/') and not url.startswith('http'):
                exercise_dict['image2_url'] = f"/static/images/{url}"

        # Get instructions
        instructions = db.execute('''
            SELECT instruction FROM instructions
            WHERE exercise_id = ?
            ORDER BY step_number
        ''', (exercise_id,)).fetchall()
        exercise_dict['instructions'] = [row['instruction'] for row in instructions]

        # Get equipment
        equipment = db.execute('''
            SELECT eq.name FROM exercise_equipment ee
            JOIN equipment eq ON ee.equipment_id = eq.id
            WHERE ee.exercise_id = ?
        ''', (exercise_id,)).fetchall()
        exercise_dict['equipment'] = [row['name'] for row in equipment]

        # Get primary muscles
        primary_muscles = db.execute('''
            SELECT m.name FROM exercise_primary_muscles epm
            JOIN muscles m ON epm.muscle_id = m.id
            WHERE epm.exercise_id = ?
        ''', (exercise_id,)).fetchall()
        exercise_dict['primary_muscles'] = [row['name'] for row in primary_muscles]

        # Get secondary muscles
        secondary_muscles = db.execute('''
            SELECT m.name FROM exercise_secondary_muscles esm
            JOIN muscles m ON esm.muscle_id = m.id
            WHERE esm.exercise_id = ?
        ''', (exercise_id,)).fetchall()
        exercise_dict['secondary_muscles'] = [row['name'] for row in secondary_muscles]

        return exercise_dict

    @staticmethod
    def get_all(limit=50, offset=0):
        """Get all exercises with pagination"""
        db = get_db()
        rows = db.execute('''
            SELECT
                e.id,
                e.name,
                e.description,
                c.name as category_name,
                c.name as category,
                GROUP_CONCAT(m.name, ', ') as primary_muscles
            FROM exercises e
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN exercise_primary_muscles epm ON e.id = epm.exercise_id
            LEFT JOIN muscles m ON epm.muscle_id = m.id
            GROUP BY e.id, e.name, e.description, c.name
            ORDER BY e.name
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def count():
        """Count total number of exercises"""
        db = get_db()
        row = db.execute('SELECT COUNT(*) as count FROM exercises').fetchone()
        return row['count']

    @staticmethod
    def search(query, limit=50, offset=0):
        """Search exercises by name or description"""
        db = get_db()

        search_term = f'%{query}%'
        rows = db.execute('''
            SELECT e.id, e.name, e.description, c.name as category_name
            FROM exercises e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.name LIKE ? OR e.description LIKE ?
            ORDER BY e.name
            LIMIT ? OFFSET ?
        ''', (search_term, search_term, limit, offset)).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def filter(category=None, muscle=None, equipment=None, limit=50, offset=0):
        """Filter exercises by category, muscle, or equipment"""
        db = get_db()

        query = '''
            SELECT DISTINCT e.id, e.name, e.description, c.name as category_name
            FROM exercises e
            LEFT JOIN categories c ON e.category_id = c.id
        '''

        conditions = []
        params = []

        if category:
            conditions.append('c.name = ?')
            params.append(category)

        if muscle:
            query += '''
                LEFT JOIN exercise_primary_muscles epm ON e.id = epm.exercise_id
                LEFT JOIN exercise_secondary_muscles esm ON e.id = esm.exercise_id
                LEFT JOIN muscles m1 ON epm.muscle_id = m1.id
                LEFT JOIN muscles m2 ON esm.muscle_id = m2.id
            '''
            conditions.append('(m1.name = ? OR m2.name = ?)')
            params.extend([muscle, muscle])

        if equipment:
            query += '''
                LEFT JOIN exercise_equipment ee ON e.id = ee.exercise_id
                LEFT JOIN equipment eq ON ee.equipment_id = eq.id
            '''
            conditions.append('eq.name = ?')
            params.append(equipment)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY e.name LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        rows = db.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_categories():
        """Get all available categories"""
        db = get_db()
        rows = db.execute('SELECT name FROM categories ORDER BY name').fetchall()
        return [row['name'] for row in rows]

    @staticmethod
    def get_all_muscles():
        """Get all available muscles"""
        db = get_db()
        rows = db.execute('SELECT name FROM muscles ORDER BY name').fetchall()
        return [row['name'] for row in rows]

    @staticmethod
    def get_all_equipment():
        """Get all available equipment"""
        db = get_db()
        rows = db.execute('SELECT name FROM equipment ORDER BY name').fetchall()
        return [row['name'] for row in rows]


class StravaConnection:
    """Strava OAuth connection model"""

    @staticmethod
    def get_by_user_id(user_id):
        """Get Strava connection for user"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM strava_connections WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create_or_update(user_id, token_data):
        """Create or update Strava connection"""
        db = get_db()

        # Check if connection exists
        existing = db.execute(
            'SELECT id FROM strava_connections WHERE user_id = ?',
            (user_id,)
        ).fetchone()

        if existing:
            # Update existing
            db.execute('''
                UPDATE strava_connections
                SET access_token = ?, refresh_token = ?, expires_at = ?,
                    athlete_id = ?, athlete_username = ?, updated_at = ?
                WHERE user_id = ?
            ''', (
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expires_at'],
                token_data.get('athlete', {}).get('id'),
                token_data.get('athlete', {}).get('username'),
                datetime.now(),
                user_id
            ))
        else:
            # Create new
            db.execute('''
                INSERT INTO strava_connections
                (user_id, access_token, refresh_token, expires_at, athlete_id, athlete_username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expires_at'],
                token_data.get('athlete', {}).get('id'),
                token_data.get('athlete', {}).get('username')
            ))

        db.commit()

    @staticmethod
    def delete(user_id):
        """Delete Strava connection (disconnect)"""
        db = get_db()
        db.execute('DELETE FROM strava_connections WHERE user_id = ?', (user_id,))
        db.commit()

    @staticmethod
    def is_connected(user_id):
        """Check if user has Strava connected"""
        db = get_db()
        row = db.execute(
            'SELECT id FROM strava_connections WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        return row is not None


class StravaUpload:
    """Strava upload tracking model"""

    @staticmethod
    def is_uploaded(workout_id):
        """Check if workout has been uploaded"""
        db = get_db()
        row = db.execute(
            "SELECT id FROM strava_uploads WHERE workout_id = ? AND upload_status = 'success'",
            (workout_id,)
        ).fetchone()
        return row is not None

    @staticmethod
    def get_by_workout_id(workout_id):
        """Get upload record for workout"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM strava_uploads WHERE workout_id = ?',
            (workout_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_user(user_id, limit=50):
        """Get upload history for user"""
        db = get_db()
        rows = db.execute('''
            SELECT su.*, w.name as workout_name
            FROM strava_uploads su
            JOIN workouts w ON su.workout_id = w.id
            WHERE su.user_id = ?
            ORDER BY su.uploaded_at DESC
            LIMIT ?
        ''', (user_id, limit)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def record_upload(workout_id, user_id, strava_activity_id, status='success', error=None):
        """Record a workout upload (success or failure)"""
        db = get_db()

        # Check if record already exists (for retries)
        existing = db.execute(
            'SELECT id FROM strava_uploads WHERE workout_id = ?',
            (workout_id,)
        ).fetchone()

        if existing:
            # Update existing record (retry case)
            db.execute('''
                UPDATE strava_uploads
                SET strava_activity_id = ?, upload_status = ?,
                    error_message = ?, uploaded_at = ?
                WHERE workout_id = ?
            ''', (strava_activity_id, status, error, datetime.now(), workout_id))
        else:
            # Create new record
            db.execute('''
                INSERT INTO strava_uploads
                (workout_id, user_id, strava_activity_id, upload_status, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (workout_id, user_id, strava_activity_id, status, error))

        db.commit()
