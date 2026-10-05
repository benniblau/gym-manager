-- Baseline schema (schema_version 2). Later changes live in gymcore/migrations.py.
CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
CREATE TABLE equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
CREATE TABLE muscles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
CREATE TABLE exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category_id INTEGER,
            description TEXT,
            video TEXT, garmin_id TEXT, difficulty TEXT, focus TEXT, image1_url TEXT, image2_url TEXT, garmin_url TEXT, is_garmin_exercise INTEGER DEFAULT 0, duplicate_of INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
CREATE TABLE instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL,
            instruction TEXT NOT NULL,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
        );
CREATE TABLE exercise_equipment (
            exercise_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, equipment_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );
CREATE TABLE exercise_primary_muscles (
            exercise_id INTEGER NOT NULL,
            muscle_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, muscle_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (muscle_id) REFERENCES muscles(id)
        );
CREATE TABLE exercise_secondary_muscles (
            exercise_id INTEGER NOT NULL,
            muscle_id INTEGER NOT NULL,
            PRIMARY KEY (exercise_id, muscle_id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (muscle_id) REFERENCES muscles(id)
        );
CREATE TABLE exercise_variations (
            exercise_id INTEGER NOT NULL,
            variation_name TEXT NOT NULL,
            PRIMARY KEY (exercise_id, variation_name),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
        );
CREATE INDEX idx_exercises_category ON exercises(category_id);
CREATE INDEX idx_instructions_exercise ON instructions(exercise_id);
CREATE INDEX idx_exercise_equipment_exercise ON exercise_equipment(exercise_id);
CREATE INDEX idx_exercise_primary_muscles_exercise ON exercise_primary_muscles(exercise_id);
CREATE INDEX idx_exercise_secondary_muscles_exercise ON exercise_secondary_muscles(exercise_id);
CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            , invited_by INTEGER, invitation_id INTEGER);
CREATE TABLE workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                order_position INTEGER NOT NULL,
                target_sets INTEGER,
                target_reps INTEGER,
                target_weight REAL,
                actual_sets INTEGER,
                actual_reps INTEGER,
                actual_weight REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, target_duration INTEGER, actual_duration INTEGER, superset_group_id INTEGER DEFAULT NULL, superset_target_reps INTEGER DEFAULT NULL, superset_actual_reps INTEGER DEFAULT NULL,
                FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT
            );
CREATE INDEX idx_workout_exercises_workout ON workout_exercises(workout_id);
CREATE INDEX idx_workout_exercises_exercise ON workout_exercises(exercise_id);
CREATE TABLE strava_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                athlete_id INTEGER,
                athlete_username TEXT,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE INDEX idx_strava_connections_user
            ON strava_connections(user_id)
        ;
CREATE TABLE strava_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                strava_activity_id INTEGER NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upload_status TEXT DEFAULT 'success' CHECK(upload_status IN ('success', 'failed')),
                error_message TEXT,
                FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(workout_id)
            );
CREATE INDEX idx_strava_uploads_workout
            ON strava_uploads(workout_id)
        ;
CREATE INDEX idx_strava_uploads_user
            ON strava_uploads(user_id)
        ;
CREATE INDEX idx_strava_uploads_strava_activity
            ON strava_uploads(strava_activity_id)
        ;
CREATE UNIQUE INDEX idx_exercises_garmin_id ON exercises(garmin_id);
CREATE TABLE IF NOT EXISTS "workouts" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            scheduled_date DATE,
            scheduled_time TIME,
            notes TEXT,
            status TEXT DEFAULT 'planned',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            is_template INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_public INTEGER DEFAULT 0, usage_count INTEGER DEFAULT 0, duration_minutes INTEGER, end_date DATE, end_time TIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
CREATE INDEX idx_workouts_template ON workouts(is_template);
CREATE INDEX idx_workouts_public
            ON workouts(is_public, is_template)
        ;
CREATE TABLE invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                sender_id INTEGER NOT NULL,
                recipient_email TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                accepted_at TIMESTAMP,
                recipient_user_id INTEGER,
                notes TEXT,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_sender ON invitations(sender_id);
CREATE INDEX idx_invitations_status ON invitations(status);
CREATE INDEX idx_workout_exercises_superset
            ON workout_exercises(workout_id, superset_group_id)
        ;
CREATE TABLE api_keys (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash     TEXT UNIQUE NOT NULL,
        key_prefix   TEXT NOT NULL,
        user_id      INTEGER NOT NULL REFERENCES users(id),
        scope        TEXT NOT NULL DEFAULT 'read',
        label        TEXT,
        last_used_at TEXT,
        created_at   TEXT NOT NULL
    );
INSERT INTO schema_version (version) VALUES (2);
