"""Template tools for the MCP server."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from mcp_server.auth import get_current_auth


def register_template_tools(mcp, conn: sqlite3.Connection) -> None:
    """Register template tools."""

    @mcp.tool()
    def list_templates(include_public: bool = False) -> str:
        """List workout templates.

        Args:
            include_public: If True, also return public templates from other users.

        Returns:
            JSON array of template dicts with id, name, notes, is_public,
            usage_count, user_id, created_at.
        """
        auth = get_current_auth()

        if include_public:
            sql = """
                SELECT id, name, notes, is_public, usage_count, user_id, created_at
                FROM workouts
                WHERE is_template = 1 AND (user_id = ? OR is_public = 1)
                ORDER BY usage_count DESC, created_at DESC
            """
            rows = conn.execute(sql, (auth.user_id,)).fetchall()
        else:
            sql = """
                SELECT id, name, notes, is_public, usage_count, user_id, created_at
                FROM workouts
                WHERE is_template = 1 AND user_id = ?
                ORDER BY created_at DESC
            """
            rows = conn.execute(sql, (auth.user_id,)).fetchall()

        return json.dumps([dict(r) for r in rows])

    @mcp.tool()
    def get_template(template_id: int) -> dict:
        """Get a template with its full exercise list.

        Args:
            template_id: The template ID.

        Returns:
            Dict with template fields plus an 'exercises' list. Each exercise has:
            id, name, category, order_position, target_sets, target_reps,
            target_weight, target_duration, superset_group_id.
        """
        auth = get_current_auth()

        row = conn.execute(
            """SELECT id, name, notes, is_public, usage_count, user_id, created_at
               FROM workouts
               WHERE id = ? AND is_template = 1
                 AND (user_id = ? OR is_public = 1)""",
            (template_id, auth.user_id),
        ).fetchone()

        if not row:
            raise ValueError(f"Template {template_id} not found")

        result = dict(row)

        exercises = conn.execute(
            """SELECT we.id, e.name, c.name AS category, we.order_position,
                      we.target_sets, we.target_reps, we.target_weight, we.target_duration,
                      we.superset_group_id
               FROM workout_exercises we
               JOIN exercises e ON e.id = we.exercise_id
               JOIN categories c ON c.id = e.category_id
               WHERE we.workout_id = ?
               ORDER BY we.order_position""",
            (template_id,),
        ).fetchall()
        result["exercises"] = [dict(e) for e in exercises]

        return result

    @mcp.tool()
    def create_workout_from_template(
        template_id: int,
        scheduled_date: Optional[str] = None,
    ) -> dict:
        """Create a new workout from a template, copying all exercises.

        Args:
            template_id: The template ID to use.
            scheduled_date: Optional ISO date string (YYYY-MM-DD) for the new workout.

        Returns:
            Dict with {workout_id}.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        template = conn.execute(
            """SELECT id, name FROM workouts
               WHERE id = ? AND is_template = 1 AND (user_id = ? OR is_public = 1)""",
            (template_id, auth.user_id),
        ).fetchone()
        if not template:
            raise ValueError(f"Template {template_id} not found")

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO workouts (user_id, name, status, scheduled_date,
                                    is_template, created_at, updated_at)
               VALUES (?, ?, 'planned', ?, 0, ?, ?)""",
            (auth.user_id, template["name"], scheduled_date, now, now),
        )
        workout_id = cursor.lastrowid

        template_exercises = conn.execute(
            """SELECT exercise_id, order_position, target_sets, target_reps,
                      target_weight, target_duration, superset_group_id
               FROM workout_exercises WHERE workout_id = ?
               ORDER BY order_position""",
            (template_id,),
        ).fetchall()

        for ex in template_exercises:
            conn.execute(
                """INSERT INTO workout_exercises
                   (workout_id, exercise_id, order_position, target_sets, target_reps,
                    target_weight, target_duration, superset_group_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    workout_id, ex["exercise_id"], ex["order_position"],
                    ex["target_sets"], ex["target_reps"], ex["target_weight"],
                    ex["target_duration"], ex["superset_group_id"], now, now,
                ),
            )

        conn.execute(
            "UPDATE workouts SET usage_count = usage_count + 1 WHERE id = ?",
            (template_id,),
        )
        conn.commit()

        return {"workout_id": workout_id}
