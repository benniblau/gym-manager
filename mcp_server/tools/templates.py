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
            id (the workout_exercises row id, e.g. for update/remove), exercise_id
            (the exercise library id, e.g. for add_workout_exercise), name, category,
            order_position, target_sets, target_reps, target_weight, target_duration,
            superset_group_id.
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
            """SELECT we.id, we.exercise_id, e.name, c.name AS category, we.order_position,
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
                      target_weight, target_duration, superset_group_id, notes
               FROM workout_exercises WHERE workout_id = ?
               ORDER BY order_position""",
            (template_id,),
        ).fetchall()

        for ex in template_exercises:
            conn.execute(
                """INSERT INTO workout_exercises
                   (workout_id, exercise_id, order_position, target_sets, target_reps,
                    target_weight, target_duration, superset_group_id, notes,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    workout_id, ex["exercise_id"], ex["order_position"],
                    ex["target_sets"], ex["target_reps"], ex["target_weight"],
                    ex["target_duration"], ex["superset_group_id"], ex["notes"], now, now,
                ),
            )

        conn.execute(
            "UPDATE workouts SET usage_count = usage_count + 1 WHERE id = ?",
            (template_id,),
        )
        conn.commit()

        return {"workout_id": workout_id}

    @mcp.tool()
    def create_template(
        name: str,
        notes: Optional[str] = None,
        is_public: bool = False,
    ) -> dict:
        """Create a new, empty workout template for the current user.

        A template is a reusable blueprint (is_template = 1). Add exercises to it
        with add_workout_exercise, then instantiate workouts from it with
        create_workout_from_template.

        Args:
            name: Template name.
            notes: Optional template notes.
            is_public: If True, other users can see and use this template.

        Returns:
            Dict with {template_id}.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO workouts (user_id, name, notes, status,
                                    is_template, is_public, created_at, updated_at)
               VALUES (?, ?, ?, 'planned', 1, ?, ?, ?)""",
            (auth.user_id, name, notes, 1 if is_public else 0, now, now),
        )
        conn.commit()
        return {"template_id": cursor.lastrowid}

    @mcp.tool()
    def update_template(
        template_id: int,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> dict:
        """Update a template's metadata (name, notes, visibility).

        Only the owner may update a template. To change its exercises, use
        add_workout_exercise / update_workout_exercise / remove_workout_exercise
        with the template_id as the workout_id.

        Args:
            template_id: The template ID.
            name: New name (omit to leave unchanged).
            notes: New notes (omit to leave unchanged).
            is_public: New visibility (omit to leave unchanged).

        Returns:
            Dict with {updated: true} on success.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        row = conn.execute(
            "SELECT id FROM workouts WHERE id = ? AND user_id = ? AND is_template = 1",
            (template_id, auth.user_id),
        ).fetchone()
        if not row:
            raise ValueError(f"Template {template_id} not found")

        updates, params = [], []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if is_public is not None:
            updates.append("is_public = ?")
            params.append(1 if is_public else 0)
        if not updates:
            raise ValueError("No fields provided to update")

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(template_id)

        conn.execute(
            f"UPDATE workouts SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()
        return {"updated": True}

    @mcp.tool()
    def delete_template(template_id: int) -> dict:
        """Delete a template and all of its exercises.

        Only the owner may delete a template. This does not affect workouts that
        were previously created from the template.

        Args:
            template_id: The template ID.

        Returns:
            Dict with {deleted: true} on success.
        """
        auth = get_current_auth()
        if not auth.can_write():
            raise PermissionError("readwrite scope required")

        row = conn.execute(
            "SELECT id FROM workouts WHERE id = ? AND user_id = ? AND is_template = 1",
            (template_id, auth.user_id),
        ).fetchone()
        if not row:
            raise ValueError(f"Template {template_id} not found")

        conn.execute("DELETE FROM workout_exercises WHERE workout_id = ?", (template_id,))
        conn.execute("DELETE FROM workouts WHERE id = ?", (template_id,))
        conn.commit()
        return {"deleted": True}
