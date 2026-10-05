"""Shared data layer for the Flask app and the MCP server.

Functions here take a sqlite3 connection, never touch Flask, and never commit:
the caller owns the transaction (``with conn:`` commits or rolls back).
"""
