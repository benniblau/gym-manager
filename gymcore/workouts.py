"""Workouts, templates and their exercise entries.

A template is a row in ``workouts`` with ``is_template = 1``; an "entry" is a
row in ``workout_exercises``. Every lookup that takes a user id checks
ownership, so callers cannot reach another user's rows by guessing ids.
"""

from datetime import datetime, timedelta

from gymcore.db import now, parse_dt

ENTRY_FIELDS = (
    "target_sets", "target_reps", "target_weight", "target_duration", "notes",
    "superset_group_id", "superset_target_reps",
)
WORKOUT_FIELDS = (
    "name", "scheduled_date", "scheduled_time", "notes", "status",
    "started_at", "completed_at", "duration_minutes", "is_public",
)


class NotFound(ValueError):
    """The row does not exist or does not belong to the user."""


# ===== LOOKUPS =====

def owned_workout(conn, user_id, workout_id, is_template=None):
    """Return the user's workout/template row, or raise NotFound."""
    sql = "SELECT * FROM workouts WHERE id = ? AND user_id = ?"
    params = [workout_id, user_id]
    if is_template is not None:
        sql += " AND is_template = ?"
        params.append(1 if is_template else 0)
    row = conn.execute(sql, params).fetchone()
    if not row:
        raise NotFound(f"{'Template' if is_template else 'Workout'} {workout_id} not found")
    return row


def owned_entry(conn, user_id, entry_id, workout_id=None, is_template=None):
    """Return an entry the user owns, optionally pinned to one workout."""
    sql = """SELECT we.*, w.is_template, w.status AS workout_status
             FROM workout_exercises we
             JOIN workouts w ON w.id = we.workout_id
             WHERE we.id = ? AND w.user_id = ?"""
    params = [entry_id, user_id]
    if workout_id is not None:
        sql += " AND we.workout_id = ?"
        params.append(workout_id)
    if is_template is not None:
        sql += " AND w.is_template = ?"
        params.append(1 if is_template else 0)
    row = conn.execute(sql, params).fetchone()
    if not row:
        raise NotFound(f"WorkoutExercise {entry_id} not found")
    return row


def list_entries(conn, workout_id):
    """All entries of a workout in order, with exercise details."""
    rows = conn.execute(
        """SELECT we.*,
                  e.name AS exercise_name,
                  e.description AS exercise_description,
                  c.name AS category_name,
                  GROUP_CONCAT(m.name, ', ') AS primary_muscles
           FROM workout_exercises we
           JOIN exercises e ON we.exercise_id = e.id
           LEFT JOIN categories c ON e.category_id = c.id
           LEFT JOIN exercise_primary_muscles epm ON e.id = epm.exercise_id
           LEFT JOIN muscles m ON epm.muscle_id = m.id
           WHERE we.workout_id = ?
           GROUP BY we.id
           ORDER BY we.order_position, we.id""",
        (workout_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# ===== ORDERING =====
# Order is handled in blocks: a standalone entry is a block of one, a superset
# is one block of all its members. Moving and renumbering work on blocks so a
# superset always stays contiguous.

def _blocks(conn, workout_id):
    rows = conn.execute(
        """SELECT id, superset_group_id FROM workout_exercises
           WHERE workout_id = ? ORDER BY order_position, id""",
        (workout_id,),
    ).fetchall()
    blocks, by_group = [], {}
    for row in rows:
        group = row["superset_group_id"]
        if group and group in by_group:
            by_group[group].append(row["id"])
            continue
        block = [row["id"]]
        blocks.append(block)
        if group:
            by_group[group] = block
    return blocks


def _write_order(conn, entry_ids):
    for position, entry_id in enumerate(entry_ids, start=1):
        conn.execute(
            "UPDATE workout_exercises SET order_position = ? WHERE id = ?",
            (position, entry_id),
        )


def _write_blocks(conn, blocks):
    _write_order(conn, [entry_id for block in blocks for entry_id in block])


def renumber(conn, workout_id):
    """Rewrite positions as 1..n with supersets contiguous."""
    _write_blocks(conn, _blocks(conn, workout_id))


def move_entry(conn, entry_id, direction):
    """Move an entry (or the whole superset it belongs to) one step up or down."""
    if direction not in ("up", "down"):
        raise ValueError("Invalid direction")
    row = conn.execute(
        "SELECT workout_id FROM workout_exercises WHERE id = ?", (entry_id,)
    ).fetchone()
    if not row:
        raise NotFound(f"WorkoutExercise {entry_id} not found")
    blocks = _blocks(conn, row["workout_id"])
    index = next(i for i, block in enumerate(blocks) if entry_id in block)
    other = index - 1 if direction == "up" else index + 1
    if 0 <= other < len(blocks):
        blocks[index], blocks[other] = blocks[other], blocks[index]
    _write_blocks(conn, blocks)


def set_order(conn, workout_id, entry_ids):
    """Set the absolute order; the ids must be exactly this workout's entries."""
    existing = {
        row["id"] for row in conn.execute(
            "SELECT id FROM workout_exercises WHERE workout_id = ?", (workout_id,)
        )
    }
    try:
        entry_ids = [int(entry_id) for entry_id in entry_ids]
    except (TypeError, ValueError):
        raise ValueError("Order must be a list of exercise ids")
    if set(entry_ids) != existing or len(entry_ids) != len(existing):
        raise ValueError("Order does not match this workout's exercises")
    _write_order(conn, entry_ids)
    renumber(conn, workout_id)


# ===== ENTRIES =====

def add_entry(conn, workout_id, exercise_id, order_position=None, **fields):
    """Add an exercise to a workout/template; appended unless a position is given."""
    if not conn.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone():
        raise NotFound(f"Exercise {exercise_id} not found")
    if order_position is None:
        order_position = conn.execute(
            "SELECT COALESCE(MAX(order_position), 0) + 1 FROM workout_exercises WHERE workout_id = ?",
            (workout_id,),
        ).fetchone()[0]
    columns = [name for name in ENTRY_FIELDS if fields.get(name) is not None]
    stamp = now()
    cursor = conn.execute(
        f"""INSERT INTO workout_exercises
            (workout_id, exercise_id, order_position, created_at, updated_at{''.join(', ' + c for c in columns)})
            VALUES (?, ?, ?, ?, ?{', ?' * len(columns)})""",
        [workout_id, exercise_id, order_position, stamp, stamp] + [fields[c] for c in columns],
    )
    return cursor.lastrowid


def update_entry(conn, entry_id, **fields):
    """Update planned values. Keys that are present are written, including None."""
    allowed = ENTRY_FIELDS + ("order_position",)
    columns = [name for name in allowed if name in fields]
    if not columns:
        return
    conn.execute(
        f"UPDATE workout_exercises SET {', '.join(c + ' = ?' for c in columns)}, updated_at = ? WHERE id = ?",
        [fields[c] for c in columns] + [now(), entry_id],
    )


def remove_entry(conn, entry_id):
    row = conn.execute(
        "SELECT workout_id, superset_group_id FROM workout_exercises WHERE id = ?", (entry_id,)
    ).fetchone()
    if not row:
        return
    conn.execute("DELETE FROM workout_sets WHERE workout_exercise_id = ?", (entry_id,))
    conn.execute("DELETE FROM workout_exercises WHERE id = ?", (entry_id,))
    if row["superset_group_id"]:
        _dissolve_if_single(conn, row["workout_id"], row["superset_group_id"])
    renumber(conn, row["workout_id"])


def duplicate_entry(conn, entry_id):
    """Copy an entry's plan as a standalone entry placed right after it."""
    source = conn.execute(
        "SELECT * FROM workout_exercises WHERE id = ?", (entry_id,)
    ).fetchone()
    if not source:
        raise NotFound(f"WorkoutExercise {entry_id} not found")
    new_id = add_entry(
        conn, source["workout_id"], source["exercise_id"],
        target_sets=source["target_sets"], target_reps=source["target_reps"],
        target_weight=source["target_weight"], target_duration=source["target_duration"],
        notes=source["notes"],
    )
    blocks = _blocks(conn, source["workout_id"])
    blocks.remove([new_id])
    index = next(i for i, block in enumerate(blocks) if entry_id in block)
    blocks.insert(index + 1, [new_id])
    _write_blocks(conn, blocks)
    return new_id


# ===== SUPERSETS =====

def create_superset(conn, workout_id, entry_ids):
    """Group two or more standalone entries of one workout into a superset."""
    if len(entry_ids) < 2:
        raise ValueError("Superset requires at least 2 exercises")
    for entry_id in entry_ids:
        row = conn.execute(
            "SELECT workout_id, superset_group_id FROM workout_exercises WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if not row or row["workout_id"] != workout_id:
            raise ValueError("All exercises must belong to the same workout")
        if row["superset_group_id"]:
            raise ValueError("Exercise is already in a superset")
    group_id = conn.execute(
        "SELECT COALESCE(MAX(superset_group_id), 0) + 1 FROM workout_exercises WHERE workout_id = ?",
        (workout_id,),
    ).fetchone()[0]
    conn.executemany(
        "UPDATE workout_exercises SET superset_group_id = ? WHERE id = ?",
        [(group_id, entry_id) for entry_id in entry_ids],
    )
    renumber(conn, workout_id)
    return group_id


def _dissolve_if_single(conn, workout_id, group_id):
    count = conn.execute(
        "SELECT COUNT(*) FROM workout_exercises WHERE workout_id = ? AND superset_group_id = ?",
        (workout_id, group_id),
    ).fetchone()[0]
    if count == 1:
        dissolve_superset(conn, workout_id, group_id)


def dissolve_superset(conn, workout_id, group_id):
    conn.execute(
        """UPDATE workout_exercises
           SET superset_group_id = NULL, superset_target_reps = NULL, superset_actual_reps = NULL
           WHERE workout_id = ? AND superset_group_id = ?""",
        (workout_id, group_id),
    )


def remove_from_superset(conn, entry_id):
    row = conn.execute(
        "SELECT workout_id, superset_group_id FROM workout_exercises WHERE id = ?", (entry_id,)
    ).fetchone()
    if not row or not row["superset_group_id"]:
        return
    conn.execute(
        """UPDATE workout_exercises
           SET superset_group_id = NULL, superset_target_reps = NULL, superset_actual_reps = NULL
           WHERE id = ?""",
        (entry_id,),
    )
    _dissolve_if_single(conn, row["workout_id"], row["superset_group_id"])
    renumber(conn, row["workout_id"])


def set_superset_reps(conn, workout_id, group_id, target_reps=None, actual_reps=None):
    """Set planned/performed rounds for a superset. None leaves a value alone, 0 clears it."""
    columns, values = [], []
    if target_reps is not None:
        columns.append("superset_target_reps = ?")
        values.append(target_reps or None)
    if actual_reps is not None:
        columns.append("superset_actual_reps = ?")
        values.append(actual_reps or None)
    if columns:
        conn.execute(
            f"UPDATE workout_exercises SET {', '.join(columns)} WHERE workout_id = ? AND superset_group_id = ?",
            values + [workout_id, group_id],
        )


# ===== WORKOUTS AND TEMPLATES =====

def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def create_workout(conn, user_id, name, scheduled_date=None, **fields):
    stamp = now()
    cursor = conn.execute(
        """INSERT INTO workouts (user_id, name, scheduled_date, scheduled_time, duration_minutes,
                                 started_at, completed_at, notes, status, is_template,
                                 created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
        (
            user_id, name, _iso(scheduled_date), _iso(fields.get("scheduled_time")),
            fields.get("duration_minutes"), _iso(fields.get("started_at")),
            _iso(fields.get("completed_at")), fields.get("notes"),
            fields.get("status", "planned"), stamp, stamp,
        ),
    )
    return cursor.lastrowid


def create_template(conn, user_id, name, notes=None, is_public=False):
    stamp = now()
    cursor = conn.execute(
        """INSERT INTO workouts (user_id, name, notes, status, is_template, is_public,
                                 usage_count, created_at, updated_at)
           VALUES (?, ?, ?, 'planned', 1, ?, 0, ?, ?)""",
        (user_id, name, notes, 1 if is_public else 0, stamp, stamp),
    )
    return cursor.lastrowid


def update_workout(conn, workout_id, **fields):
    columns = [name for name in WORKOUT_FIELDS if name in fields]
    if not columns:
        return
    conn.execute(
        f"UPDATE workouts SET {', '.join(c + ' = ?' for c in columns)}, updated_at = ? WHERE id = ?",
        [_iso(fields[c]) for c in columns] + [now(), workout_id],
    )


def delete_workout(conn, workout_id):
    """Delete a workout/template with its entries and logged sets."""
    conn.execute(
        """DELETE FROM workout_sets WHERE workout_exercise_id IN
           (SELECT id FROM workout_exercises WHERE workout_id = ?)""",
        (workout_id,),
    )
    conn.execute("DELETE FROM workout_exercises WHERE workout_id = ?", (workout_id,))
    conn.execute("DELETE FROM strava_uploads WHERE workout_id = ?", (workout_id,))
    conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))


def copy_entries(conn, source_id, target_id):
    """Copy the planned entries (targets, notes, supersets) of one workout into another."""
    for entry in conn.execute(
        "SELECT * FROM workout_exercises WHERE workout_id = ? ORDER BY order_position, id",
        (source_id,),
    ).fetchall():
        add_entry(
            conn, target_id, entry["exercise_id"], order_position=entry["order_position"],
            **{name: entry[name] for name in ENTRY_FIELDS},
        )
    renumber(conn, target_id)


def create_from_template(conn, user_id, template_id, scheduled_date=None, **fields):
    """Create a workout from the user's own or a public template."""
    template = conn.execute(
        """SELECT * FROM workouts
           WHERE id = ? AND is_template = 1 AND (user_id = ? OR is_public = 1)""",
        (template_id, user_id),
    ).fetchone()
    if not template:
        raise NotFound(f"Template {template_id} not found")
    if fields.get("notes") is None:
        fields["notes"] = template["notes"]
    workout_id = create_workout(conn, user_id, template["name"], scheduled_date, **fields)
    copy_entries(conn, template_id, workout_id)
    conn.execute("UPDATE workouts SET usage_count = usage_count + 1 WHERE id = ?", (template_id,))
    return workout_id


def save_as_template(conn, user_id, workout_id):
    workout = owned_workout(conn, user_id, workout_id)
    template_id = create_template(conn, user_id, f"{workout['name']} Template", workout["notes"])
    copy_entries(conn, workout_id, template_id)
    return template_id


def start_workout(conn, workout_id):
    """Move a planned workout to in_progress and stamp the start time once."""
    workout = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if not workout or workout["status"] != "planned":
        return
    fields = {"status": "in_progress"}
    if not workout["started_at"]:
        fields["started_at"] = now()
    update_workout(conn, workout_id, **fields)


def complete_workout(conn, workout_id, duration_minutes=None):
    """Mark a workout completed, filling start, end and duration where missing."""
    workout = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    if not workout:
        raise NotFound(f"Workout {workout_id} not found")
    current = datetime.now().replace(microsecond=0)
    fields = {"status": "completed"}

    end = parse_dt(workout["completed_at"])
    if not end:
        end = current
        fields["completed_at"] = end

    start = parse_dt(workout["started_at"])
    if not start:
        duration = duration_minutes or workout["duration_minutes"]
        try:
            start = datetime.combine(
                datetime.strptime(workout["scheduled_date"], "%Y-%m-%d").date(),
                datetime.strptime(workout["scheduled_time"][:5], "%H:%M").time(),
            )
        except (ValueError, TypeError):
            start = end - timedelta(minutes=duration) if duration else end
        fields["started_at"] = start

    if duration_minutes:
        fields["duration_minutes"] = duration_minutes
    elif not workout["duration_minutes"] and start < end:
        fields["duration_minutes"] = int((end - start).total_seconds() / 60)

    update_workout(conn, workout_id, **fields)
