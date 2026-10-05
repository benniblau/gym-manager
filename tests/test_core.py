import pytest

from gymcore import sets as core_sets
from gymcore import workouts as core
from gymcore.db import connect
from gymcore.migrations import current_version, migrate


def order(conn, workout_id):
    return [e["id"] for e in core.list_entries(conn, workout_id)]


def test_ownership_lookups(conn, workout):
    assert core.owned_workout(conn, 1, workout["id"])["name"] == "Push day"
    with pytest.raises(core.NotFound):
        core.owned_workout(conn, 2, workout["id"])
    with pytest.raises(core.NotFound):
        core.owned_entry(conn, 2, workout["entries"][0])
    with pytest.raises(core.NotFound):
        core.owned_entry(conn, 1, workout["entries"][0], workout_id=workout["id"] + 99)


def test_move_and_duplicate_keep_supersets_together(conn, workout):
    a, b, c, d = workout["entries"]
    with conn:
        core.create_superset(conn, workout["id"], [a, c])
    assert order(conn, workout["id"]) == [a, c, b, d]

    with conn:
        core.move_entry(conn, a, "down")  # moves the whole superset below b
    assert order(conn, workout["id"]) == [b, a, c, d]

    with conn:
        copy = core.duplicate_entry(conn, a)  # lands after the superset, not inside it
    assert order(conn, workout["id"]) == [b, a, c, copy, d]
    positions = [e["order_position"] for e in core.list_entries(conn, workout["id"])]
    assert positions == [1, 2, 3, 4, 5]


def test_set_order_rejects_foreign_ids(conn, workout):
    with pytest.raises(ValueError):
        core.set_order(conn, workout["id"], workout["entries"][:2])
    with pytest.raises(ValueError):
        core.set_order(conn, workout["id"], workout["entries"][:3] + [9999])
    with conn:
        core.set_order(conn, workout["id"], list(reversed(workout["entries"])))
    assert order(conn, workout["id"]) == list(reversed(workout["entries"]))


def test_superset_dissolves_when_one_member_left(conn, workout):
    a, b, c, _ = workout["entries"]
    with conn:
        group = core.create_superset(conn, workout["id"], [a, b, c])
        core.remove_from_superset(conn, a)
        core.remove_entry(conn, b)
    rows = {e["id"]: e["superset_group_id"] for e in core.list_entries(conn, workout["id"])}
    assert group and rows[a] is None and rows[c] is None


def test_superset_must_stay_in_one_workout(conn, workout):
    with conn:
        other = core.create_workout(conn, 1, "Other")
        foreign = core.add_entry(conn, other, 1)
    with pytest.raises(ValueError):
        core.create_superset(conn, workout["id"], [workout["entries"][0], foreign])


def test_sets_drive_the_summary(conn, workout):
    entry = workout["entries"][0]
    with conn:
        core_sets.log_set(conn, entry, 1, reps=10, weight=50)
        core_sets.log_set(conn, entry, 2, reps=8, weight=55)
        core_sets.log_set(conn, entry, 3, reps=8, weight=60)
        core_sets.log_set(conn, entry, 3, reps=8, weight=60)  # retry is harmless
    row = core.list_entries(conn, workout["id"])[0]
    assert (row["actual_sets"], row["actual_reps"], row["actual_weight"]) == (3, 8, 60)
    sets = core_sets.sets_for(conn, [entry])[entry]
    assert core_sets.describe(sets) == "10 @ 50 kg · 8 @ 55 kg · 8 @ 60 kg"

    with conn:
        core_sets.clear_set(conn, entry, 1)
        core_sets.clear_set(conn, entry, 2)
        core_sets.clear_set(conn, entry, 3)
    row = core.list_entries(conn, workout["id"])[0]
    assert row["actual_sets"] is None and row["actual_weight"] is None


def test_describe_uniform_and_duration():
    assert core_sets.describe([{"reps": 10, "weight": 50.0}] * 3) == "3 × 10 @ 50 kg"
    assert core_sets.describe([{"duration": 90}]) == "1 × 1m30s"
    assert core_sets.describe([]) == ""
    assert core_sets.describe_plan({"target_sets": 3, "target_reps": 10, "target_weight": 12.5}) == "3 × 10 @ 12.5 kg"


def test_log_as_planned_only_fills_untouched_exercises(conn, workout):
    bench, squat, stretch, pushup = workout["entries"]
    with conn:
        core_sets.log_set(conn, bench, 1, reps=6, weight=60)
        assert core_sets.log_as_planned(conn, workout["id"]) == 2
    sets = core_sets.sets_for(conn, workout["entries"])
    assert len(sets[bench]) == 1                       # already logged: left alone
    assert [s["reps"] for s in sets[squat]] == [5, 5, 5]
    assert sets[stretch] == [dict(sets[stretch][0], duration=30, set_number=1)]
    assert sets[pushup] == []                          # nothing planned, nothing invented


def test_last_performance_uses_latest_completed_other_workout(conn, workout):
    with conn:
        for day, weight in (("2026-01-01", 40), ("2026-01-05", 45)):
            past = core.create_workout(conn, 1, "Past", day, status="completed", completed_at=f"{day}T10:00:00")
            entry = core.add_entry(conn, past, 1)
            core_sets.replace_sets(conn, entry, 3, reps=10, weight=weight)
        theirs = core.create_workout(conn, 2, "Bob", "2026-01-06", status="completed", completed_at="2026-01-06T10:00:00")
        core_sets.replace_sets(conn, core.add_entry(conn, theirs, 1), 1, reps=1, weight=200)
    last = core_sets.last_performance(conn, 1, [1, 2], exclude_workout_id=workout["id"])
    assert last[1]["text"] == "3 × 10 @ 45 kg" and last[1]["date"] == "2026-01-05"
    assert 2 not in last


def test_delete_workout_leaves_nothing_behind(conn, workout):
    with conn:
        core_sets.log_set(conn, workout["entries"][0], 1, reps=10)
        core.delete_workout(conn, workout["id"])
    assert conn.execute("SELECT COUNT(*) FROM workout_exercises").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM workout_sets").fetchone()[0] == 0


def test_foreign_keys_are_enforced(conn):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO workout_exercises (workout_id, exercise_id, order_position) VALUES (999, 1, 1)")


def test_template_round_trip_keeps_supersets_and_access_rules(conn, workout):
    a, b, _, _ = workout["entries"]
    with conn:
        core.create_superset(conn, workout["id"], [a, b])
        core.set_superset_reps(conn, workout["id"], 1, target_reps=4)
        template = core.save_as_template(conn, 1, workout["id"])
    with pytest.raises(core.NotFound):
        core.create_from_template(conn, 2, template)   # private template of another user
    with conn:
        core.update_workout(conn, template, is_public=1)
        copy = core.create_from_template(conn, 2, template, "2026-02-01")
    entries = core.list_entries(conn, copy)
    assert [e["exercise_id"] for e in entries] == [1, 2, 3, 4]
    assert entries[0]["superset_group_id"] == entries[1]["superset_group_id"] is not None
    assert entries[0]["superset_target_reps"] == 4
    assert entries[0]["actual_sets"] is None
    assert conn.execute("SELECT usage_count FROM workouts WHERE id = ?", (template,)).fetchone()[0] == 1


def test_complete_fills_times_once(conn, workout):
    with conn:
        core.update_workout(conn, workout["id"], scheduled_time="10:00")
        core.complete_workout(conn, workout["id"], duration_minutes=45)
    row = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout["id"],)).fetchone()
    assert row["status"] == "completed" and row["started_at"] == "2026-01-10T10:00:00"
    assert row["duration_minutes"] == 45 and row["completed_at"]
    with conn:
        core.complete_workout(conn, workout["id"])
    again = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout["id"],)).fetchone()
    assert again["completed_at"] == row["completed_at"]


def test_complete_handles_old_utc_timestamps(conn, workout):
    with conn:
        core.update_workout(conn, workout["id"], started_at="2026-01-10T09:00:00+00:00")
        core.complete_workout(conn, workout["id"])  # must not raise naive/aware TypeError


def test_migrations_backfill_and_clean_up(tmp_path):
    from pathlib import Path
    import gymcore

    path = str(tmp_path / "legacy.db")
    legacy = connect(path)
    legacy.executescript((Path(gymcore.__file__).parent / "schema.sql").read_text())
    legacy.execute("PRAGMA foreign_keys = OFF")
    legacy.execute("INSERT INTO users (id, username, email, password_hash) VALUES (1, 'a', 'a@x', 'h')")
    legacy.execute("INSERT INTO exercises (id, name) VALUES (1, 'Bench')")
    legacy.execute("INSERT INTO workouts (id, user_id, name) VALUES (1, 1, 'Done')")
    legacy.execute(
        """INSERT INTO workout_exercises (id, workout_id, exercise_id, order_position,
                                          actual_sets, actual_reps, actual_weight)
           VALUES (1, 1, 1, 1, 3, 10, 50), (2, 1, 1, 2, NULL, 12, NULL), (3, 1, 1, 3, NULL, NULL, NULL),
                  (4, 77, 1, 1, 3, 10, 50)"""
    )
    legacy.commit()
    legacy.close()

    conn = connect(path)
    conn.isolation_level = None
    assert migrate(conn, dry_run=True, log=lambda m: None) == [3, 4, 5]
    assert current_version(conn) == 2                      # dry run rolled back
    assert migrate(conn, log=lambda m: None) == [3, 4, 5]
    assert migrate(conn, log=lambda m: None) == []          # idempotent
    counts = dict(conn.execute(
        "SELECT workout_exercise_id, COUNT(*) FROM workout_sets GROUP BY 1").fetchall())
    assert counts == {1: 3, 2: 1}
    assert conn.execute("SELECT COUNT(*) FROM workout_exercises WHERE workout_id = 77").fetchone()[0] == 0
