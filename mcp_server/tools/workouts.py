"""Workout tools for the MCP server."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from mcp_server.auth import get_current_auth


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
            id, name, category, order_position, target_sets, target_reps,
            target_weight, target_duration, actual_sets, actual_reps,
            actual_weight, actual_duration, notes, superset_group_id.
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
            """SELECT we.id, e.name, c.name AS category, we.order_position,
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
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO workouts (user_id, name, status, scheduled_date, notes,
                                    is_template, created_at, updated_at)
               VALUES (?, ?, 'planned', ?, ?, 0, ?, ?)""",
            (auth.user_id, name, scheduled_date, notes, now, now),
        )
        conn.commit()
        return {"workout_id": cursor.lastrowid}

    @mcp.tool()
    def log_exercise(
        workout_exercise_id: int,
        actual_sets: Optional[int] = None,
        actual_reps: Optional[int] = None,
        actual_weight: Optional[float] = None,
        actual_duration: Optional[int] = None,
    ) -> dict:
        """Log actual values for an exercise in a workout.

        Args:
            workout_exercise_id: The workout_exercises row ID.
            actual_sets: Number of sets completed.
            actual_reps: Number of reps completed.
            actual_weight: Weight used (kg or lb, same unit as targets).
            actual_duration: Duration in seconds.

        Returns:
            Dict with {updated: true} on success.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        row = conn.execute(
            """SELECT we.id FROM workout_exercises we
               JOIN workouts w ON w.id = we.workout_id
               WHERE we.id = ? AND w.user_id = ? AND w.is_template = 0""",
            (workout_exercise_id, auth.user_id),
        ).fetchone()
        if not row:
            raise ValueError(f"WorkoutExercise {workout_exercise_id} not found")

        updates = []
        params = []
        if actual_sets is not None:
            updates.append("actual_sets = ?")
            params.append(actual_sets)
        if actual_reps is not None:
            updates.append("actual_reps = ?")
            params.append(actual_reps)
        if actual_weight is not None:
            updates.append("actual_weight = ?")
            params.append(actual_weight)
        if actual_duration is not None:
            updates.append("actual_duration = ?")
            params.append(actual_duration)

        if not updates:
            raise ValueError("No values provided to log")

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(workout_exercise_id)

        conn.execute(
            f"UPDATE workout_exercises SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()
        return {"updated": True}

    @mcp.tool()
    def complete_workout(
        workout_id: int,
        duration_minutes: Optional[int] = None,
    ) -> dict:
        """Mark a workout as completed.

        Args:
            workout_id: The workout ID.
            duration_minutes: Optional total duration in minutes.

        Returns:
            Dict with {workout_id, status: 'completed'}.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        row = conn.execute(
            "SELECT id FROM workouts WHERE id = ? AND user_id = ? AND is_template = 0",
            (workout_id, auth.user_id),
        ).fetchone()
        if not row:
            raise ValueError(f"Workout {workout_id} not found")

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """UPDATE workouts
               SET status = 'completed', completed_at = ?, duration_minutes = ?,
                   updated_at = ?
               WHERE id = ?""",
            (now, duration_minutes, now, workout_id),
        )
        conn.commit()
        return {"workout_id": workout_id, "status": "completed"}
