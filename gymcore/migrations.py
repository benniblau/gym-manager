"""Versioned schema migrations, tracked in the ``schema_version`` table.

``gymcore/schema.sql`` is the baseline (version 2). Each migration below runs
once, in order, inside a single transaction; every step is also written to be
harmless if the change is already present.
"""

BASELINE_VERSION = 2


def _remove_orphans(conn, log):
    """Rows left behind while foreign keys were not enforced."""
    for table in ("workout_exercises", "strava_uploads"):
        cursor = conn.execute(
            f"DELETE FROM {table} WHERE workout_id NOT IN (SELECT id FROM workouts)"
        )
        log(f"  removed {cursor.rowcount} orphaned {table} rows")


def _add_indexes(conn, log):
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_workouts_user_date
           ON workouts(user_id, is_template, scheduled_date)"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
    log("  indexes on workouts(user_id, is_template, scheduled_date) and api_keys(user_id)")


def _add_workout_sets(conn, log):
    """Per-set logging table, backfilled from the per-exercise summary columns."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS workout_sets (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               workout_exercise_id INTEGER NOT NULL
                   REFERENCES workout_exercises(id) ON DELETE CASCADE,
               set_number INTEGER NOT NULL CHECK (set_number >= 1),
               reps INTEGER,
               weight REAL,
               duration INTEGER,
               logged_at TIMESTAMP NOT NULL,
               UNIQUE (workout_exercise_id, set_number)
           )"""
    )
    rows = conn.execute(
        """SELECT we.id, we.actual_sets, we.actual_reps, we.actual_weight, we.actual_duration,
                  COALESCE(w.completed_at, we.updated_at, CURRENT_TIMESTAMP) AS logged_at
           FROM workout_exercises we
           JOIN workouts w ON w.id = we.workout_id
           WHERE w.is_template = 0
             AND (we.actual_sets IS NOT NULL OR we.actual_reps IS NOT NULL
                  OR we.actual_weight IS NOT NULL OR we.actual_duration IS NOT NULL)
             AND NOT EXISTS (SELECT 1 FROM workout_sets s WHERE s.workout_exercise_id = we.id)"""
    ).fetchall()
    created = 0
    for row in rows:
        for number in range(1, (row["actual_sets"] or 1) + 1):
            conn.execute(
                """INSERT INTO workout_sets
                   (workout_exercise_id, set_number, reps, weight, duration, logged_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (row["id"], number, row["actual_reps"], row["actual_weight"],
                 row["actual_duration"], row["logged_at"]),
            )
            created += 1
    log(f"  workout_sets table; backfilled {created} sets from {len(rows)} logged exercises")


MIGRATIONS = [
    (3, "remove orphaned rows", _remove_orphans),
    (4, "add lookup indexes", _add_indexes),
    (5, "per-set logging", _add_workout_sets),
]


def current_version(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_version (
               version INTEGER PRIMARY KEY,
               applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    return version or BASELINE_VERSION


def pending(conn):
    version = current_version(conn)
    return [m for m in MIGRATIONS if m[0] > version]


def migrate(conn, dry_run=False, log=print):
    """Apply pending migrations in one transaction. Returns the versions applied.

    The connection must be in autocommit mode (``isolation_level=None``) so the
    schema changes can be rolled back together on error or ``dry_run``.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        todo = pending(conn)
        for version, name, step in todo:
            log(f"{version}: {name}")
            step(conn, log)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            log(f"warning: {len(problems)} foreign key violations remain")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("ROLLBACK" if dry_run else "COMMIT")
    return [version for version, _, _ in todo]


def create_schema(conn):
    """Build a fresh database at the latest version (used by tests and new installs)."""
    from pathlib import Path

    conn.executescript((Path(__file__).parent / "schema.sql").read_text())
    conn.isolation_level = None
    migrate(conn, log=lambda message: None)
