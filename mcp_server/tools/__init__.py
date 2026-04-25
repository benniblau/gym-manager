"""Tool registration for the Gym Manager MCP server."""

import sqlite3

from mcp_server.tools.exercises import register_exercise_tools
from mcp_server.tools.workouts import register_workout_tools
from mcp_server.tools.templates import register_template_tools
from mcp_server.tools.progress import register_progress_tools


def register_all_tools(mcp, conn: sqlite3.Connection) -> None:
    """Register all tool modules with the FastMCP instance."""
    register_exercise_tools(mcp, conn)
    register_workout_tools(mcp, conn)
    register_template_tools(mcp, conn)
    register_progress_tools(mcp, conn)
