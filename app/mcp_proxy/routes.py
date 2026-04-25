"""Redirect /mcp to the standalone MCP server.

The standalone MCP server runs independently on port 8085 and handles its own
bearer token authentication. Flask simply redirects clients here so they only
need to know the main app URL to discover the MCP endpoint.

Configure the MCP server's public base URL via GM_MCP_URL
(default: http://127.0.0.1:8085).
"""

import os

from flask import Blueprint, redirect

mcp_proxy_bp = Blueprint("mcp_proxy", __name__)


def _mcp_url() -> str:
    return os.environ.get("GM_MCP_URL", "http://127.0.0.1:8085").rstrip("/")


@mcp_proxy_bp.route("/mcp", methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"], strict_slashes=False)
def mcp():
    return redirect(f"{_mcp_url()}/mcp", code=307)
