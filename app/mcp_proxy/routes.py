"""Reverse-proxy /mcp to the standalone MCP server.

The standalone MCP server runs on port 8085 (localhost only). Flask forwards
requests to it internally so the MCP server never needs to be publicly exposed
and there are no redirect loops behind a reverse proxy.

Configure the internal MCP server URL via GM_MCP_URL
(default: http://127.0.0.1:8085).
"""

import os

import requests
from flask import Blueprint, Response, request, stream_with_context

mcp_proxy_bp = Blueprint("mcp_proxy", __name__)

_HOP_BY_HOP = frozenset([
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    "content-encoding", "content-length",
])


def _mcp_url() -> str:
    return os.environ.get("GM_MCP_URL", "http://127.0.0.1:8085").rstrip("/")


@mcp_proxy_bp.route("/mcp", methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"], strict_slashes=False)
def mcp():
    # Always target /mcp/ with trailing slash — Starlette's Mount redirects /mcp
    # to /mcp/ with a 307; targeting /mcp/ directly skips that redirect entirely.
    target = f"{_mcp_url()}/mcp/"

    fwd_headers = {
        k: v for k, v in request.headers
        if k.lower() not in ("host", *_HOP_BY_HOP)
    }

    upstream = requests.request(
        method=request.method,
        url=target,
        headers=fwd_headers,
        data=request.get_data(),
        stream=True,
        allow_redirects=False,  # never follow upstream redirects — stream them as-is
        timeout=60,
    )

    resp_headers = [
        (k, v) for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP
    ]

    return Response(
        stream_with_context(upstream.iter_content(chunk_size=4096)),
        status=upstream.status_code,
        headers=resp_headers,
    )
