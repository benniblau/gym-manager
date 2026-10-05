"""Workout tools for the MCP server."""

import json
import sqlite3
from typing import Optional

from gymcore import sets as core_sets
from gymcore import workouts as core
from mcp_server.auth import get_current_auth


def _writer():
    """The current auth context, which must carry the readwrite scope."""
    auth = get_current_auth()
    if not auth.can_write():
        raise PermissionError("readwrite scope required")
    return auth


def register_workout_tools(mcp, conn: sqlite3.Connection) -> None:
    """Register workout read and write tools."""

    @mcp.tool()
    def list_workouts(
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """List the current user's workouts (not templates).

        Args:
            status: Filter by status — 'planned', 'in_progress', or 'completed'.
            start_date: ISO date string (YYYY-MM-DD), inclusive lower bound on scheduled_date.
            end_date: ISO date string (YYYY-MM-DD), inclusive upper bound on scheduled_date.
            limit: Max results to return (capped at 100).
            offset: Number of results to skip for pagination.

        Returns:
            JSON array of workout dicts with id, name, status, scheduled_date,
            started_at, completed_at, duration_minutes, notes.
        """
        auth = get_current_auth()

        where = ["user_id = ?", "is_template = 0"]
        params: list = [auth.user_id]

        if status:
            where.append("status = ?")
            params.append(status)
        if start_date:
            where.append("scheduled_date >= ?")
            params.append(start_date)
        if end_date:
            where.append("scheduled_date <= ?")
            params.append(end_date)

        sql = f"""
            SELECT id, name, status, scheduled_date, scheduled_time,
                   started_at, completed_at, duration_minutes, notes,
                   created_at, updated_at
            FROM workouts
            WHERE {' AND '.join(where)}
            ORDER BY scheduled_date DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params += [min(limit, 100), offset]

        rows = conn.execute(sql, params).fetchall()
        return json.dumps([dict(r) for r in rows])

    @mcp.tool()
    def get_workout(workout_id: int) -> dict:
        """Get a single workout with its full exercise list and logged values.

        Args:
            workout_id: The workout ID.

        Returns:
            Dict with workout fields plus an 'exercises' list. Each exercise has:
            id (the workout_exercises row id, e.g. for log_exercise / update / remove),
            exercise_id (the exercise library id, e.g. for add_workout_exercise), name,
            category, order_position, target_sets, target_reps, target_weight,
            target_duration, actual_sets, actual_reps, actual_weight, actual_duration
            (a summary of the logged sets), notes, superset_group_id, and sets: the
            individual logged sets as {set_number, reps, weight, duration, logged_at}.
        """
        auth = get_current_auth()

        row = conn.execute(
            """SELECT id, name, status, scheduled_date, scheduled_time,
                      started_at, completed_at, duration_minutes, notes,
                      is_template, created_at, updated_at
               FROM workouts WHERE id = ? AND user_id = ? AND is_template = 0""",
            (workout_id, auth.user_id),
        ).fetchone()

        if not row:
            raise ValueError(f"Workout {workout_id} not found")

        result = dict(row)

        exercises = conn.execute(
            """SELECT we.id, we.exercise_id, e.name, c.name AS category, we.order_position,
                      we.target_sets, we.target_reps, we.target_weight, we.target_duration,
                      we.actual_sets, we.actual_reps, we.actual_weight, we.actual_duration,
                      we.notes, we.superset_group_id
               FROM workout_exercises we
               JOIN exercises e ON e.id = we.exercise_id
               JOIN categories c ON c.id = e.category_id
               WHERE we.workout_id = ?
               ORDER BY we.order_position""",
            (workout_id,),
        ).fetchall()
        result["exercises"] = [dict(e) for e in exercises]
        by_entry = core_sets.sets_for(conn, [e["id"] for e in result["exercises"]])
        for entry in result["exercises"]:
            entry["sets"] = by_entry[entry["id"]]

        return result

    @mcp.tool()
    def create_workout(
        name: str,
        scheduled_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Create a new planned workout for the current user.

        Args:
            name: Workout name.
            scheduled_date: Optional ISO date string (YYYY-MM-DD).
            notes: Optional workout notes.

        Returns:
            Dict with {workout_id}.
        """
        auth = _writer()
        with conn:
            workout_id = core.create_workout(conn, auth.user_id, name, scheduled_date, notes=notes)
        return {"workout_id": workout_id}

    @mcp.tool()
    def log_exercise(
        workout_exercise_id: int,
        actual_sets: Optional[int] = None,
        actual_reps: Optional[int] = None,
        actual_weight: Optional[float] = None,
        actual_duration: Optional[int] = None,
    ) -> dict:
        """Log an exercise as a number of identical sets (replaces any sets already logged).

        Use this when every set was the same. For sets that differ (e.g. rising
        weight), call log_set once per set instead. Omitted values keep what was
        previously logged for this exercise.

        Args:
            workout_exercise_id: The workout_exercises row ID.
            actual_sets: Number of sets completed.
            actual_reps: Reps per set.
            actual_weight: Weight used in kg.
            actual_duration: Duration per set in seconds.

        Returns:
            Dict with {updated: true, sets: <number of sets now logged>}.
        """
        auth = _writer()
        entry = core.owned_entry(conn, auth.user_id, workout_exercise_id, is_template=False)

        if all(v is None for v in (actual_sets, actual_reps, actual_weight, actual_duration)):
            raise ValueError("No values provided to log")

        def pick(value, column):
            return value if value is not None else entry[column]

        count = pick(actual_sets, "actual_sets") or 1
        with conn:
            core_sets.replace_sets(
                conn, workout_exercise_id, count,
                reps=pick(actual_reps, "actual_reps"),
                weight=pick(actual_weight, "actual_weight"),
                duration=pick(actual_duration, "actual_duration"),
            )
            core.start_workout(conn, entry["workout_id"])
        return {"updated": True, "sets": count}

    @mcp.tool()
    def log_set(
        workout_exercise_id: int,
        set_number: int,
        reps: Optional[int] = None,
        weight: Optional[float] = None,
        duration: Optional[int] = None,
    ) -> dict:
        """Log one performed set of an exercise (creates or overwrites that set number).

        Args:
            workout_exercise_id: The workout_exercises row ID.
            set_number: 1-based number of the set within the exercise.
            reps: Reps performed.
            weight: Weight used in kg.
            duration: Duration in seconds (time-based exercises).

        Returns:
            Dict with {updated: true}.
        """
        auth = _writer()
        entry = core.owned_entry(conn, auth.user_id, workout_exercise_id, is_template=False)
        with conn:
            core_sets.log_set(conn, workout_exercise_id, set_number, reps, weight, duration)
            core.start_workout(conn, entry["workout_id"])
        return {"updated": True}

    @mcp.tool()
    def remove_set(workout_exercise_id: int, set_number: int) -> dict:
        """Remove one logged set of an exercise.

        Args:
            workout_exercise_id: The workout_exercises row ID.
            set_number: The set number to remove.

        Returns:
            Dict with {deleted: true}.
        """
        auth = _writer()
        core.owned_entry(conn, auth.user_id, workout_exercise_id, is_template=False)
        with conn:
            core_sets.clear_set(conn, workout_exercise_id, set_number)
        return {"deleted": True}

    @mcp.tool()
    def add_workout_exercise(
        workout_id: int,
        exercise_id: int,
        order_position: Optional[int] = None,
        target_sets: Optional[int] = None,
        target_reps: Optional[int] = None,
        target_weight: Optional[float] = None,
        target_duration: Optional[int] = None,
        superset_group_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Add an exercise to a workout or template.

        Works for both workouts and templates — pass either one's ID as
        workout_id (both are rows in the workouts table). Only the owner may add
        exercises. If order_position is omitted, the exercise is appended to the end.

        Args:
            workout_id: The workout OR template ID to add the exercise to.
            exercise_id: The exercise library ID (from search_exercises / get_exercise).
            order_position: Position to insert at; omit to append after the last exercise.
            target_sets: Planned number of sets.
            target_reps: Planned reps per set.
            target_weight: Planned weight in kg.
            target_duration: Planned duration in seconds.
            superset_group_id: Group ID to link this exercise into a superset.
            notes: Optional per-exercise note.

        Returns:
            Dict with {workout_exercise_id, order_position}.
        """
        auth = _writer()
        core.owned_workout(conn, auth.user_id, workout_id)
        with conn:
            entry_id = core.add_entry(
                conn, workout_id, exercise_id, order_position=order_position,
                target_sets=target_sets, target_reps=target_reps, target_weight=target_weight,
                target_duration=target_duration, superset_group_id=superset_group_id, notes=notes,
            )
        position = conn.execute(
            "SELECT order_position FROM workout_exercises WHERE id = ?", (entry_id,)
        ).fetchone()["order_position"]
        return {"workout_exercise_id": entry_id, "order_position": position}

    @mcp.tool()
    def update_workout_exercise(
        workout_exercise_id: int,
        order_position: Optional[int] = None,
        target_sets: Optional[int] = None,
        target_reps: Optional[int] = None,
        target_weight: Optional[float] = None,
        target_duration: Optional[int] = None,
        superset_group_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Update an exercise entry's planned targets, order, or superset grouping.

        Works for entries in both workouts and templates. Only the owner may
        update. To log what was actually performed, use log_set or log_exercise.
        Omitted fields are left unchanged.

        Args:
            workout_exercise_id: The workout_exercises row ID.
            order_position: New position.
            target_sets: New planned sets.
            target_reps: New planned reps.
            target_weight: New planned weight.
            target_duration: New planned duration in seconds.
            superset_group_id: New superset group ID.
            notes: New per-exercise note.

        Returns:
            Dict with {updated: true} on success.
        """
        auth = _writer()
        core.owned_entry(conn, auth.user_id, workout_exercise_id)

        fields = {
            "order_position": order_position,
            "target_sets": target_sets,
            "target_reps": target_reps,
            "target_weight": target_weight,
            "target_duration": target_duration,
            "superset_group_id": superset_group_id,
            "notes": notes,
        }
        fields = {name: value for name, value in fields.items() if value is not None}
        if not fields:
            raise ValueError("No fields provided to update")

        with conn:
            core.update_entry(conn, workout_exercise_id, **fields)
        return {"updated": True}

    @mcp.tool()
    def remove_workout_exercise(workout_exercise_id: int) -> dict:
        """Remove an exercise entry from a workout or template.

        Works for entries in both workouts and templates. Only the owner may remove.

        Args:
            workout_exercise_id: The workout_exercises row ID.

        Returns:
            Dict with {deleted: true} on success.
        """
        auth = _writer()
        core.owned_entry(conn, auth.user_id, workout_exercise_id)
        with conn:
            core.remove_entry(conn, workout_exercise_id)
        return {"deleted": True}

    @mcp.tool()
    def complete_workout(
        workout_id: int,
        duration_minutes: Optional[int] = None,
    ) -> dict:
        """Mark a workout as completed.

        Start time, end time and duration are filled in where missing; values
        that are already set are kept.

        Args:
            workout_id: The workout ID.
            duration_minutes: Optional total duration in minutes.

        Returns:
            Dict with {workout_id, status: 'completed'}.
        """
        auth = _writer()
        core.owned_workout(conn, auth.user_id, workout_id, is_template=False)
        with conn:
            core.complete_workout(conn, workout_id, duration_minutes)
        return {"workout_id": workout_id, "status": "completed"}

    @mcp.tool()
    def delete_workout(workout_id: int) -> dict:
        """Delete a workout and all of its exercise entries.

        Only the owner may delete, and only workouts (not templates) — use
        delete_template to remove a template.

        Args:
            workout_id: The workout ID.

        Returns:
            Dict with {deleted: true} on success.
        """
        auth = _writer()
        core.owned_workout(conn, auth.user_id, workout_id, is_template=False)
        with conn:
            core.delete_workout(conn, workout_id)
        return {"deleted": True}
