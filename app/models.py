import os
import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from gymcore import workouts as core
from gymcore.db import connect, now
from gymcore.sets import attach_sets


def get_db():
    """Get database connection, reuse within request context"""
    if 'db' not in g:
        g.db = connect(current_app.config['DATABASE_PATH'])
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
    def create(username, email, password, invited_by=None, invitation_id=None):
        """Create new user"""
        db = get_db()
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            'INSERT INTO users (username, email, password_hash, invited_by, invitation_id) VALUES (?, ?, ?, ?, ?)',
            (username, email, password_hash, invited_by, invitation_id)
        )
        db.commit()
        return User.get_by_id(cursor.lastrowid)

    def check_password(self, password):
        """Verify password (also accepts bcrypt hashes written by older versions)"""
        if self.password_hash.startswith('$2'):
            from app import bcrypt
            return bcrypt.check_password_hash(self.password_hash, password)
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Update last login timestamp"""
        db = get_db()
        db.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (now(), self.id)
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
        password_hash = generate_password_hash(new_password)
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

    @staticmethod
    def count():
        """Count total number of users"""
        db = get_db()
        row = db.execute('SELECT COUNT(*) as count FROM users').fetchone()
        return row['count']


class Invitation:
    """Invitation model for user registration"""

    def __init__(self, id, token, sender_id, recipient_email, status,
                 created_at, expires_at, accepted_at, recipient_user_id, notes):
        self.id = id
        self.token = token
        self.sender_id = sender_id
        self.recipient_email = recipient_email
        self.status = status
        self.created_at = created_at
        self.expires_at = expires_at
        self.accepted_at = accepted_at
        self.recipient_user_id = recipient_user_id
        self.notes = notes

    @staticmethod
    def create(sender_id, recipient_email=None, expires_in_days=30, notes=None):
        """Create new invitation with unique token"""
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(32)

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        db = get_db()
        cursor = db.execute('''
            INSERT INTO invitations (token, sender_id, recipient_email, expires_at, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (token, sender_id, recipient_email, expires_at, notes))
        db.commit()

        return Invitation.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(invitation_id):
        """Get invitation by ID"""
        db = get_db()
        row = db.execute('SELECT * FROM invitations WHERE id = ?', (invitation_id,)).fetchone()
        if row:
            return Invitation(
                id=row['id'],
                token=row['token'],
                sender_id=row['sender_id'],
                recipient_email=row['recipient_email'],
                status=row['status'],
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                accepted_at=row['accepted_at'],
                recipient_user_id=row['recipient_user_id'],
                notes=row['notes']
            )
        return None

    @staticmethod
    def get_by_token(token):
        """Get invitation by token"""
        db = get_db()
        row = db.execute('SELECT * FROM invitations WHERE token = ?', (token,)).fetchone()
        if row:
            return Invitation(
                id=row['id'],
                token=row['token'],
                sender_id=row['sender_id'],
                recipient_email=row['recipient_email'],
                status=row['status'],
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                accepted_at=row['accepted_at'],
                recipient_user_id=row['recipient_user_id'],
                notes=row['notes']
            )
        return None

    @staticmethod
    def get_by_sender(sender_id, status=None):
        """Get all invitations sent by a user, optionally filtered by status"""
        db = get_db()

        if status:
            rows = db.execute('''
                SELECT * FROM invitations
                WHERE sender_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (sender_id, status)).fetchall()
        else:
            rows = db.execute('''
                SELECT * FROM invitations
                WHERE sender_id = ?
                ORDER BY created_at DESC
            ''', (sender_id,)).fetchall()

        return [Invitation(
            id=row['id'],
            token=row['token'],
            sender_id=row['sender_id'],
            recipient_email=row['recipient_email'],
            status=row['status'],
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            accepted_at=row['accepted_at'],
            recipient_user_id=row['recipient_user_id'],
            notes=row['notes']
        ) for row in rows]

    def is_valid(self):
        """Check if invitation is valid (not expired/accepted/revoked)"""
        if self.status != 'pending':
            return False

        if self.expires_at:
            from datetime import datetime as dt
            try:
                expires_dt = dt.fromisoformat(self.expires_at)
                if expires_dt < datetime.now():
                    # Auto-expire the invitation
                    self.update(status='expired')
                    return False
            except (ValueError, TypeError):
                # Invalid date format
                return False

        return True

    def accept(self, user_id):
        """Mark invitation as accepted"""
        db = get_db()
        db.execute('''
            UPDATE invitations
            SET status = 'accepted', accepted_at = ?, recipient_user_id = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), user_id, self.id))
        db.commit()

        self.status = 'accepted'
        self.accepted_at = datetime.now().isoformat()
        self.recipient_user_id = user_id

    def revoke(self):
        """Revoke pending invitation"""
        if self.status != 'pending':
            return False

        db = get_db()
        db.execute('''
            UPDATE invitations
            SET status = 'revoked'
            WHERE id = ?
        ''', (self.id,))
        db.commit()

        self.status = 'revoked'
        return True

    def update(self, **kwargs):
        """Update invitation fields"""
        db = get_db()

        fields = []
        values = []

        for key in ['status', 'recipient_email', 'notes', 'accepted_at', 'recipient_user_id']:
            if key in kwargs:
                fields.append(f'{key} = ?')
                values.append(kwargs[key])

        if fields:
            values.append(self.id)
            query = f"UPDATE invitations SET {', '.join(fields)} WHERE id = ?"
            db.execute(query, values)
            db.commit()

            # Update instance attributes
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)



class Workout:
    """Workout model (templates are workouts with is_template=1)"""

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
        """Get a user's workouts (templates excluded), newest first"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ? AND is_template = 0
            ORDER BY scheduled_date DESC, scheduled_time DESC, id DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def count_by_user(user_id):
        """Workout counts for a user (templates excluded): {'total', 'completed'}"""
        db = get_db()
        row = db.execute('''
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(status = 'completed'), 0) AS completed
            FROM workouts WHERE user_id = ? AND is_template = 0
        ''', (user_id,)).fetchone()
        return dict(row)

    @staticmethod
    def get_open_by_user(user_id, limit=5):
        """Workouts still to do: in progress first, then planned by date"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ? AND is_template = 0 AND status != 'completed'
            ORDER BY status = 'in_progress' DESC, scheduled_date, scheduled_time
            LIMIT ?
        ''', (user_id, limit)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def get_by_date(user_id, date):
        """Get workouts for a specific date"""
        db = get_db()
        if hasattr(date, 'isoformat'):
            date = date.isoformat()
        rows = db.execute('''
            SELECT * FROM workouts
            WHERE user_id = ? AND is_template = 0 AND scheduled_date = ?
            ORDER BY scheduled_time
        ''', (user_id, date)).fetchall()
        return [Workout(**dict(row)) for row in rows]

    @staticmethod
    def create(user_id, name, scheduled_date, **kwargs):
        """Create new workout"""
        db = get_db()
        with db:
            workout_id = core.create_workout(db, user_id, name, scheduled_date, **kwargs)
        return Workout.get_by_id(workout_id)

    def update(self, **kwargs):
        """Update workout fields"""
        db = get_db()
        with db:
            core.update_workout(db, self.id, **kwargs)

    def delete(self):
        """Delete workout with its exercises and logged sets"""
        db = get_db()
        with db:
            core.delete_workout(db, self.id)

    def get_exercises(self):
        """Exercises in this workout, each with its logged 'sets'"""
        db = get_db()
        return attach_sets(db, core.list_entries(db, self.id))

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
        with db:
            template_id = core.create_template(db, user_id, name, notes, is_public)
        return Workout.get_by_id(template_id)

    @staticmethod
    def create_from_template(template_id, user_id, scheduled_date, **kwargs):
        """Create a workout from the user's own or a public template"""
        db = get_db()
        with db:
            workout_id = core.create_from_template(db, user_id, template_id, scheduled_date, **kwargs)
        return Workout.get_by_id(workout_id)

    @staticmethod
    def get_all_templates(user_id, visibility='all', order_by='name', limit=100, offset=0):
        """Get all templates accessible to user (own + public) with filtering and sorting.

        Args:
            user_id: Current user's ID
            visibility: 'all', 'mine', or 'public'
            order_by: 'name', 'usage_count', or 'created_at'
        """
        db = get_db()

        order_clauses = {
            'usage_count': 'w.usage_count DESC, w.name ASC',
            'name': 'w.name ASC',
            'created_at': 'w.created_at DESC'
        }
        order_clause = order_clauses.get(order_by, order_clauses['name'])

        if visibility == 'mine':
            where_clause = 'w.is_template = 1 AND w.user_id = ?'
            params = [user_id]
        elif visibility == 'public':
            where_clause = 'w.is_template = 1 AND w.is_public = 1'
            params = []
        else:  # 'all' - user's own templates + public templates from others
            where_clause = 'w.is_template = 1 AND (w.user_id = ? OR w.is_public = 1)'
            params = [user_id]

        params.extend([limit, offset])

        rows = db.execute(f'''
            SELECT w.*, u.username as creator_username,
                   CASE WHEN w.user_id = ? THEN 1 ELSE 0 END as is_owner,
                   (SELECT COUNT(*) FROM workout_exercises we WHERE we.workout_id = w.id) as exercise_count
            FROM workouts w
            JOIN users u ON w.user_id = u.id
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        ''', [user_id] + params).fetchall()

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
        self.is_public = 0 if self.is_public else 1
        self.update(is_public=self.is_public)
        return self.is_public



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

        # Local filenames get the /static/images/ prefix; paths and URLs are used as-is
        for key in ('image1_url', 'image2_url'):
            exercise_dict[key] = Exercise._image_url(exercise_dict.get(key))

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
    def _image_url(value):
        """Public URL for a stored image value, preferring the smaller .webp copy if present."""
        if not value or value.startswith('/') or value.startswith('http'):
            return value
        webp = os.path.splitext(value)[0] + '.webp'
        if os.path.exists(os.path.join(current_app.static_folder, 'images', webp)):
            value = webp
        return f"/static/images/{value}"

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
    def count_search(query):
        """Count exercises matching search query"""
        db = get_db()
        search_term = f'%{query}%'
        row = db.execute('''
            SELECT COUNT(*) as count FROM exercises
            WHERE name LIKE ? OR description LIKE ?
        ''', (search_term, search_term)).fetchone()
        return row['count']

    @staticmethod
    def count_filter(category=None, muscle=None, equipment=None):
        """Count exercises matching filter criteria"""
        db = get_db()

        query = '''
            SELECT COUNT(DISTINCT e.id) as count
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

        row = db.execute(query, params).fetchone()
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
    def find(query=None, category=None, muscle=None, equipment=None, limit=30, offset=0):
        """Search and filter exercises in one query.

        Matches the text against the name (and, as a weaker match, the
        description) and applies any of the filters. Name matches come first.
        Returns (rows, total) where rows carry category_name and primary_muscles.
        """
        db = get_db()
        conditions = []
        params = []

        if query:
            conditions.append('(e.name LIKE ? OR e.description LIKE ?)')
            params.extend([f'%{query}%', f'%{query}%'])
        if category:
            conditions.append('c.name = ?')
            params.append(category)
        if muscle:
            conditions.append('''e.id IN (
                SELECT exercise_id FROM exercise_primary_muscles x JOIN muscles m ON m.id = x.muscle_id WHERE m.name = ?
                UNION
                SELECT exercise_id FROM exercise_secondary_muscles x JOIN muscles m ON m.id = x.muscle_id WHERE m.name = ?)''')
            params.extend([muscle, muscle])
        if equipment:
            conditions.append('''e.id IN (
                SELECT exercise_id FROM exercise_equipment x JOIN equipment q ON q.id = x.equipment_id WHERE q.name = ?)''')
            params.append(equipment)

        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        base = f'FROM exercises e LEFT JOIN categories c ON e.category_id = c.id{where}'

        total = db.execute(f'SELECT COUNT(*) {base}', params).fetchone()[0]
        rows = db.execute(f'''
            SELECT e.id, e.name, e.description, c.name AS category_name,
                   (SELECT GROUP_CONCAT(m.name, ', ')
                    FROM exercise_primary_muscles x JOIN muscles m ON m.id = x.muscle_id
                    WHERE x.exercise_id = e.id) AS primary_muscles
            {base}
            ORDER BY {'e.name LIKE ? DESC, ' if query else ''}e.name
            LIMIT ? OFFSET ?
        ''', params + ([f'{query}%'] if query else []) + [limit, offset]).fetchall()
        return [dict(row) for row in rows], total

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
                now(),
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
            ''', (strava_activity_id, status, error, now(), workout_id))
        else:
            # Create new record
            db.execute('''
                INSERT INTO strava_uploads
                (workout_id, user_id, strava_activity_id, upload_status, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (workout_id, user_id, strava_activity_id, status, error))

        db.commit()
