"""Exercise library tools for the MCP server."""

import json
import sqlite3
from typing import Optional

from mcp_server.auth import get_current_auth


def register_exercise_tools(mcp, conn: sqlite3.Connection) -> None:
    """Register exercise read tools. The exercise library is global (not user-scoped)."""

    @mcp.tool()
    def search_exercises(
        query: Optional[str] = None,
        category: Optional[str] = None,
        muscle: Optional[str] = None,
        equipment: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """Search and filter the exercise library.

        Args:
            query: Text search on exercise name and description (case-insensitive).
            category: Filter by category name (e.g. 'strength', 'cardio', 'plyometrics').
            muscle: Filter by primary muscle name (e.g. 'chest', 'glutes', 'abdominals').
            equipment: Filter by equipment name (e.g. 'barbell', 'dumbbell', 'box').
            limit: Max results to return (capped at 100).
            offset: Number of results to skip for pagination.

        Returns:
            JSON array of exercise dicts with id, name, category, difficulty, focus.
        """
        get_current_auth()

        params: list = []
        joins = ""
        where_clauses = ["1=1"]

        if query:
            where_clauses.append(
                "(e.name LIKE ? OR e.description LIKE ?)"
            )
            q = f"%{query}%"
            params += [q, q]

        if category:
            where_clauses.append("c.name = ?")
            params.append(category)

        if muscle:
            joins += """
            JOIN exercise_primary_muscles epm ON epm.exercise_id = e.id
            JOIN muscles m ON m.id = epm.muscle_id AND m.name = ?
            """
            params.insert(0, muscle)

        if equipment:
            joins += """
            JOIN exercise_equipment ee ON ee.exercise_id = e.id
            JOIN equipment eq ON eq.id = ee.equipment_id AND eq.name = ?
            """
            params.insert(0 if not muscle else 1, equipment)

        where = " AND ".join(where_clauses)
        sql = f"""
            SELECT DISTINCT e.id, e.name, c.name AS category, e.difficulty, e.focus
            FROM exercises e
            JOIN categories c ON c.id = e.category_id
            {joins}
            WHERE {where}
            ORDER BY e.name
            LIMIT ? OFFSET ?
        """
        params += [min(limit, 100), offset]

        rows = conn.execute(sql, params).fetchall()
        return json.dumps([dict(r) for r in rows])

    @mcp.tool()
    def get_exercise(exercise_id: int) -> dict:
        """Get full details for a single exercise.

        Args:
            exercise_id: The exercise ID.

        Returns:
            Dict with name, category, description, difficulty, focus, video,
            primary_muscles, secondary_muscles, equipment, instructions.
        """
        get_current_auth()

        row = conn.execute(
            """SELECT e.id, e.name, c.name AS category, e.description,
                      e.difficulty, e.focus, e.video, e.image1_url, e.image2_url
               FROM exercises e
               JOIN categories c ON c.id = e.category_id
               WHERE e.id = ?""",
            (exercise_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"Exercise {exercise_id} not found")

        result = dict(row)

        primary = conn.execute(
            """SELECT m.name FROM muscles m
               JOIN exercise_primary_muscles epm ON epm.muscle_id = m.id
               WHERE epm.exercise_id = ?""",
            (exercise_id,),
        ).fetchall()
        result["primary_muscles"] = [r["name"] for r in primary]

        secondary = conn.execute(
            """SELECT m.name FROM muscles m
               JOIN exercise_secondary_muscles esm ON esm.muscle_id = m.id
               WHERE esm.exercise_id = ?""",
            (exercise_id,),
        ).fetchall()
        result["secondary_muscles"] = [r["name"] for r in secondary]

        equip = conn.execute(
            """SELECT eq.name FROM equipment eq
               JOIN exercise_equipment ee ON ee.equipment_id = eq.id
               WHERE ee.exercise_id = ?""",
            (exercise_id,),
        ).fetchall()
        result["equipment"] = [r["name"] for r in equip]

        instructions = conn.execute(
            """SELECT step_number, instruction FROM instructions
               WHERE exercise_id = ?
               ORDER BY step_number""",
            (exercise_id,),
        ).fetchall()
        result["instructions"] = [dict(r) for r in instructions]

        return result

    @mcp.tool()
    def list_categories() -> str:
        """List all exercise categories.

        Returns:
            JSON array of category name strings.
        """
        get_current_auth()
        rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
        return json.dumps([r["name"] for r in rows])

    @mcp.tool()
    def list_muscles() -> str:
        """List all muscle groups in the exercise library.

        Returns:
            JSON array of muscle name strings.
        """
        get_current_auth()
        rows = conn.execute("SELECT name FROM muscles ORDER BY name").fetchall()
        return json.dumps([r["name"] for r in rows])

    @mcp.tool()
    def list_equipment() -> str:
        """List all equipment types in the exercise library.

        Returns:
            JSON array of equipment name strings.
        """
        get_current_auth()
        rows = conn.execute("SELECT name FROM equipment ORDER BY name").fetchall()
        return json.dumps([r["name"] for r in rows])
