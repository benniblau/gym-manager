# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server (port 5001)
source venv/bin/activate
python run.py

# Production server
./start-production.sh
# or: gunicorn --config gunicorn_config.py wsgi:app

# Verify app starts (smoke test)
python -c "from app import create_app; app = create_app()"

# Initialize database from scratch (reads exercises.json)
python database.py

# Run migration scripts (additive, idempotent)
python migrations/<script_name>.py

# MCP server — HTTP streaming transport (port 8085)
GM_MCP_TRANSPORT=http python -m mcp_server.server

# MCP server — stdio transport (for Claude Desktop)
GM_API_KEY=gm_<key> python -m mcp_server.server
```

No test suite or linter is configured yet.

## Architecture

**App factory:** `create_app(config_name)` in `app/__init__.py`. Dev uses `'development'` (port 5001, DEBUG=True), production uses `'production'` via `wsgi.py`. `TestingConfig` uses in-memory SQLite and disables CSRF.

**Database:** Raw SQLite via `get_db()` — stored on Flask's `g` per request. No ORM. `sqlite3.Row` factory enables column-by-name access. Models in `app/models.py` are plain Python classes with `@staticmethod` query methods.

**Blueprints:**
- `auth` → `/auth` — login, register, logout, settings, invitations
- `main` → `/` — dashboard
- `workouts` → `/workouts` — workout CRUD, exercise add/remove/reorder, superset management, rep logging
- `exercises` → `/exercises` — browse, search, filter, detail
- `templates` → `/templates` — template CRUD, public sharing, privacy toggle
- `strava` → `/strava` — OAuth connect, upload, disconnect

**Cross-blueprint URL pattern:** Template edit pages rewrite exercise CRUD form actions from `/templates/` to `/workouts/`. Both blueprints have their own superset create/dissolve routes, but `update-reps` only exists under `/workouts/`.

**Frontend JS:** `app/static/js/workout-edit.js` handles all workout and template edit page interactivity (~400 lines). Uses event delegation on `#current-exercises` and `#exercise-list` — no need to re-attach handlers after DOM updates. Detects current page via `window.location.pathname` to construct correct API URLs.

**Template reuse:** `includes/exercise_card.html` defines Jinja2 macros used by both `workouts/edit.html` and `templates/edit.html`. Exercise details modal (`includes/exercise_details_modal.html`) uses a single delegated `document.addEventListener('click')` handler.

**Authentication:** Flask-Login with invitation-only registration (except first user). All protected routes use `@login_required`.

**Production:** `ProxyFix` middleware with `x_for=2, x_proto=2, x_host=2, x_prefix=2` for Pangolin → Traefik → Flask topology.

## MCP Server

Standalone FastMCP server exposing gym data over HTTP streaming (MCP spec 2025-03-26). Entry point: `python -m mcp_server.server`.

**Module layout:** `mcp_server/server.py` (entry), `mcp_server/db.py` (SQLite), `mcp_server/auth.py` (AuthContext + resolve_auth), `mcp_server/middleware.py` (ASGI auth), `mcp_server/api_key_repository.py` (key CRUD), `mcp_server/tools/` (exercises, workouts, templates, progress).

**API keys:** Generated per-user from `/auth/settings` → MCP API Keys. Stored hashed in the `api_keys` table. Raw key shown once; prefix stored for identification. Key format: `gm_<32 hex chars>`. Two scopes: `read` and `readwrite`.

**Auth:** HTTP transport uses `Authorization: Bearer gm_<key>` or `X-API-Key: gm_<key>` header per request (ASGI middleware). Stdio transport validates `GM_API_KEY` env var once at startup. Each key is scoped to one user — tools only return that user's data.

**Transport env vars:** `GM_MCP_TRANSPORT` (`http`/`stdio`), `GM_MCP_HTTP_HOST`, `GM_MCP_HTTP_PORT` (default 8085), `DATABASE_PATH`.

**`/mcp` proxy:** `app/mcp_proxy/routes.py` — Flask blueprint that issues a 307 redirect from `<appurl>/mcp` to `GM_MCP_URL/mcp` (default `http://127.0.0.1:8085`). In production set `GM_MCP_URL` to the publicly reachable MCP server URL so clients can follow the redirect.

## Database Schema Notes

Key tables: `users`, `workouts` (also stores templates via `is_template=1`), `workout_exercises`, `exercises`, `categories`, `muscles`, `equipment`, `invitations`, `strava_connections`, `strava_uploads`, `api_keys`.

- `workouts.status`: `planned` / `in_progress` / `completed`
- `workouts.is_template`: `0` = workout, `1` = template
- Supersets: exercises share a `superset_group_id` (integer scoped per workout); `_consolidate_superset_order` ensures consecutive `order_position`
- Muscle names: `abdominals` (not `core`), `glutes` (not `gluteals`)
- Equipment: `box` (not `plyo box`), `Strap` (ID 26) for TRX/suspension
- Categories: strength, stretching, plyometrics, strongman, cardio, olympic weightlifting, crossfit, calisthenics, suspension (ID 9)
- Image URLs: local filenames get `/static/images/` prefix at read time in `Exercise.get_by_id`; URLs starting with `/` or `http` are used as-is

## Testing Without a Test Suite

```python
# Manual test client pattern
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['_user_id'] = '1'
    # user ID 1 exists; workout ID 1 and template ID 2 available for testing
    # workout ID 2 has supersets

# Smoke test
python -c "from app import create_app; app = create_app()"
```

## Migration Scripts

Located in `migrations/`. Always support `--dry-run`, use `exercise_exists()` for idempotency, and check both old and new image filenames (images may already be renamed if migration ran locally first).
