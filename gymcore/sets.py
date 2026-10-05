"""Per-set logging.

A row in ``workout_sets`` is one performed set. Planned-but-not-done sets are
not stored, so set numbers may have gaps. The ``actual_*`` columns on
``workout_exercises`` are kept as a derived summary of the logged sets
(count, most common reps, heaviest weight, longest duration) for exports and
older consumers.
"""

from collections import Counter

from gymcore.db import now


def _clean(value, cast):
    """Treat empty and non-positive input as 'not recorded'."""
    if value in (None, ""):
        return None
    value = cast(value)
    return value if value > 0 else None


def log_set(conn, entry_id, set_number, reps=None, weight=None, duration=None):
    """Record (or overwrite) one performed set. Safe to repeat with the same values."""
    set_number = int(set_number)
    if not 1 <= set_number <= 99:
        raise ValueError("Set number must be between 1 and 99")
    conn.execute(
        """INSERT INTO workout_sets (workout_exercise_id, set_number, reps, weight, duration, logged_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(workout_exercise_id, set_number)
           DO UPDATE SET reps = excluded.reps, weight = excluded.weight, duration = excluded.duration""",
        (entry_id, set_number, _clean(reps, int), _clean(weight, float), _clean(duration, int), now()),
    )
    sync_summary(conn, entry_id)


def clear_set(conn, entry_id, set_number):
    """Remove a logged set (the set was not actually done)."""
    conn.execute(
        "DELETE FROM workout_sets WHERE workout_exercise_id = ? AND set_number = ?",
        (entry_id, int(set_number)),
    )
    sync_summary(conn, entry_id)


def replace_sets(conn, entry_id, count, reps=None, weight=None, duration=None):
    """Replace all logged sets with ``count`` identical ones (summary-style logging)."""
    conn.execute("DELETE FROM workout_sets WHERE workout_exercise_id = ?", (entry_id,))
    stamp = now()
    conn.executemany(
        """INSERT INTO workout_sets (workout_exercise_id, set_number, reps, weight, duration, logged_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (entry_id, number, _clean(reps, int), _clean(weight, float), _clean(duration, int), stamp)
            for number in range(1, int(count or 0) + 1)
        ],
    )
    sync_summary(conn, entry_id)


def sync_summary(conn, entry_id):
    """Recompute the entry's actual_* summary columns from its logged sets."""
    sets = conn.execute(
        "SELECT reps, weight, duration FROM workout_sets WHERE workout_exercise_id = ? ORDER BY set_number",
        (entry_id,),
    ).fetchall()
    reps = [row["reps"] for row in sets if row["reps"]]
    weights = [row["weight"] for row in sets if row["weight"]]
    durations = [row["duration"] for row in sets if row["duration"]]
    conn.execute(
        """UPDATE workout_exercises
           SET actual_sets = ?, actual_reps = ?, actual_weight = ?, actual_duration = ?, updated_at = ?
           WHERE id = ?""",
        (
            len(sets) or None,
            Counter(reps).most_common(1)[0][0] if reps else None,
            max(weights) if weights else None,
            max(durations) if durations else None,
            now(), entry_id,
        ),
    )


def sets_for(conn, entry_ids):
    """Logged sets for several entries: {entry_id: [set dicts ordered by number]}."""
    result = {entry_id: [] for entry_id in entry_ids}
    if not result:
        return result
    marks = ",".join("?" * len(result))
    for row in conn.execute(
        f"""SELECT workout_exercise_id, set_number, reps, weight, duration, logged_at
            FROM workout_sets WHERE workout_exercise_id IN ({marks})
            ORDER BY workout_exercise_id, set_number""",
        list(result),
    ):
        result[row["workout_exercise_id"]].append(
            {k: row[k] for k in ("set_number", "reps", "weight", "duration", "logged_at")}
        )
    return result


def attach_sets(conn, entries):
    """Add a 'sets' list and a 'sets_text' summary to each entry dict."""
    by_entry = sets_for(conn, [entry["id"] for entry in entries])
    for entry in entries:
        entry["sets"] = by_entry[entry["id"]]
        entry["sets_text"] = describe(entry["sets"])
    return entries


def last_performance(conn, user_id, exercise_ids, exclude_workout_id=None):
    """Most recent completed session per exercise: {exercise_id: {date, workout_id, sets, text}}."""
    exercise_ids = list(set(exercise_ids))
    if not exercise_ids:
        return {}
    marks = ",".join("?" * len(exercise_ids))
    rows = conn.execute(
        f"""SELECT we.exercise_id, we.id AS entry_id, w.id AS workout_id,
                   COALESCE(w.completed_at, w.scheduled_date) AS performed_at
            FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE w.user_id = ? AND w.is_template = 0 AND w.status = 'completed'
              AND w.id != ? AND we.exercise_id IN ({marks})
              AND EXISTS (SELECT 1 FROM workout_sets s WHERE s.workout_exercise_id = we.id)
            ORDER BY performed_at DESC, we.order_position""",
        [user_id, exclude_workout_id or 0] + exercise_ids,
    ).fetchall()
    latest = {}
    for row in rows:
        latest.setdefault(row["exercise_id"], row)
    by_entry = sets_for(conn, [row["entry_id"] for row in latest.values()])
    return {
        exercise_id: {
            "date": (row["performed_at"] or "")[:10],
            "workout_id": row["workout_id"],
            "sets": by_entry[row["entry_id"]],
            "text": describe(by_entry[row["entry_id"]]),
        }
        for exercise_id, row in latest.items()
    }


# ===== TEXT =====

def fmt_weight(weight):
    return f"{weight:g}"


def fmt_duration(seconds):
    if seconds >= 60:
        minutes, rest = divmod(seconds, 60)
        return f"{minutes}m{rest}s" if rest else f"{minutes}m"
    return f"{seconds}s"


def _describe_one(row):
    parts = []
    if row.get("reps"):
        parts.append(str(row["reps"]))
    if row.get("duration"):
        parts.append(fmt_duration(row["duration"]))
    text = " / ".join(parts)
    if row.get("weight"):
        text = f"{text} @ {fmt_weight(row['weight'])} kg" if text else f"{fmt_weight(row['weight'])} kg"
    return text


def describe(sets):
    """'3 × 10 @ 50 kg' when all sets match, otherwise each set joined by ' · '."""
    if not sets:
        return ""
    each = [_describe_one(row) for row in sets]
    if len(set(each)) == 1:
        return f"{len(each)} × {each[0]}" if each[0] else f"{len(each)} sets"
    return " · ".join(text or "done" for text in each)


def describe_plan(entry):
    """Planned values of an entry in the same style, e.g. '3 × 10 @ 50 kg'."""
    one = _describe_one({
        "reps": entry.get("target_reps"),
        "weight": entry.get("target_weight"),
        "duration": entry.get("target_duration"),
    })
    sets = entry.get("target_sets")
    if sets and one:
        return f"{sets} × {one}"
    if sets:
        return f"{sets} sets"
    return one


def log_as_planned(conn, workout_id):
    """Log every exercise that has a plan but no sets yet as done exactly as planned.

    Returns the number of exercises filled in.
    """
    rows = conn.execute(
        """SELECT id, target_sets, target_reps, target_weight, target_duration
           FROM workout_exercises we
           WHERE workout_id = ?
             AND (target_sets IS NOT NULL OR target_reps IS NOT NULL OR target_duration IS NOT NULL)
             AND NOT EXISTS (SELECT 1 FROM workout_sets s WHERE s.workout_exercise_id = we.id)""",
        (workout_id,),
    ).fetchall()
    for row in rows:
        replace_sets(
            conn, row["id"], row["target_sets"] or 1,
            reps=row["target_reps"], weight=row["target_weight"], duration=row["target_duration"],
        )
    return len(rows)
