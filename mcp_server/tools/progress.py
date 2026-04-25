"""Progress and analytics tools for the MCP server."""

import json
import sqlite3
from typing import Optional

from mcp_server.auth import get_current_auth


def register_progress_tools(mcp, conn: sqlite3.Connection) -> None:
    """Register read-only progress and analytics tools."""

    @mcp.tool()
    def get_exercise_history(exercise_id: int, limit: int = 10) -> str:
        """Get the logged history for a specific exercise across the user's workouts.

        Args:
            exercise_id: The exercise ID to look up.
            limit: Max number of past sessions to return (most recent first).

        Returns:
            JSON array of session dicts with workout_id, workout_name,
            scheduled_date, actual_sets, actual_reps, actual_weight,
            actual_duration.
        """
        auth = get_current_auth()

        rows = conn.execute(
            """SELECT w.id AS workout_id, w.name AS workout_name,
                      w.scheduled_date, w.completed_at,
                      we.actual_sets, we.actual_reps, we.actual_weight, we.actual_duration,
                      we.target_sets, we.target_reps, we.target_weight
               FROM workout_exercises we
               JOIN workouts w ON w.id = we.workout_id
               WHERE we.exercise_id = ?
                 AND w.user_id = ?
                 AND w.is_template = 0
                 AND w.status = 'completed'
               ORDER BY w.completed_at DESC
               LIMIT ?""",
            (exercise_id, auth.user_id, min(limit, 100)),
        ).fetchall()

        return json.dumps([dict(r) for r in rows])

    @mcp.tool()
    def get_workout_stats(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Aggregate workout statistics for the current user in a date range.

        Args:
            start_date: ISO date string (YYYY-MM-DD), inclusive lower bound.
            end_date: ISO date string (YYYY-MM-DD), inclusive upper bound.

        Returns:
            Dict with total_workouts, completed_workouts, planned_workouts,
            in_progress_workouts, total_duration_minutes, avg_duration_minutes,
            completion_rate_pct.
        """
        auth = get_current_auth()

        where = ["user_id = ?", "is_template = 0"]
        params: list = [auth.user_id]

        if start_date:
            where.append("scheduled_date >= ?")
            params.append(start_date)
        if end_date:
            where.append("scheduled_date <= ?")
            params.append(end_date)

        sql = f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) AS planned,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(COALESCE(duration_minutes, 0)) AS total_duration
            FROM workouts
            WHERE {' AND '.join(where)}
        """
        row = conn.execute(sql, params).fetchone()

        total = row["total"] or 0
        completed = row["completed"] or 0
        total_duration = row["total_duration"] or 0

        return {
            "total_workouts": total,
            "completed_workouts": completed,
            "planned_workouts": row["planned"] or 0,
            "in_progress_workouts": row["in_progress"] or 0,
            "total_duration_minutes": total_duration,
            "avg_duration_minutes": round(total_duration / completed, 1) if completed else 0,
            "completion_rate_pct": round(completed / total * 100, 1) if total else 0,
        }

    @mcp.tool()
    def get_muscle_focus(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """Get muscle groups trained, ranked by frequency, across completed workouts.

        Args:
            start_date: ISO date string (YYYY-MM-DD), inclusive lower bound.
            end_date: ISO date string (YYYY-MM-DD), inclusive upper bound.

        Returns:
            JSON array of {muscle, exercise_count} dicts, sorted by exercise_count desc.
        """
        auth = get_current_auth()

        where = ["w.user_id = ?", "w.is_template = 0", "w.status = 'completed'"]
        params: list = [auth.user_id]

        if start_date:
            where.append("w.scheduled_date >= ?")
            params.append(start_date)
        if end_date:
            where.append("w.scheduled_date <= ?")
            params.append(end_date)

        sql = f"""
            SELECT m.name AS muscle, COUNT(we.id) AS exercise_count
            FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            JOIN exercise_primary_muscles epm ON epm.exercise_id = we.exercise_id
            JOIN muscles m ON m.id = epm.muscle_id
            WHERE {' AND '.join(where)}
            GROUP BY m.name
            ORDER BY exercise_count DESC
        """
        rows = conn.execute(sql, params).fetchall()
        return json.dumps([dict(r) for r in rows])
