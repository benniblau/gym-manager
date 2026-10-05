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

# Apply pending schema migrations (versioned, idempotent; see gymcore/migrations.py)
python migrations/migrate.py [--dry-run]

# One-off data scripts (additive, idempotent)
python migrations/<script_name>.py

# Create .webp copies of exercise images (needs cwebp; originals are kept)
python migrations/convert_images_to_webp.py [--dry-run]

# Tests (pip install -r requirements-dev.txt)
python -m pytest

# MCP server — HTTP streaming transport (port 8085)
GM_MCP_TRANSPORT=http python -m mcp_server.server

# MCP server — stdio transport (for Claude Desktop)
GM_API_KEY=gm_<key> python -m mcp_server.server
```

No linter is configured yet.

## Architecture

**App factory:** `create_app(config_name)` in `app/__init__.py`. Dev uses `'development'` (port 5001, DEBUG=True), production uses `'production'` via `wsgi.py`. `TestingConfig` uses in-memory SQLite and disables CSRF.

**Database:** Raw SQLite, no ORM. `gymcore.db.connect()` opens every connection (row access by name, foreign keys ON, WAL). Flask stores one per request on `g` via `get_db()`. The app refuses to start if the database is behind `gymcore/migrations.py`.

**Shared data layer (`gymcore/`):** All writes to workouts, templates, exercise entries and logged sets go through `gymcore/workouts.py` and `gymcore/sets.py`. Both the Flask routes and the MCP tools call these, so ownership checks and behavior cannot drift. Functions take a connection, check ownership when given a user id (`owned_workout`, `owned_entry` raise `NotFound`), and never commit — callers wrap them in `with db:`. Timestamps are naive local time (`gymcore.db.now()`, `parse_dt()`).

**Models:** `app/models.py` keeps `User`, `Invitation`, `Exercise` (read-only library), Strava models, and a thin `Workout` read model that delegates writes to `gymcore`.

**Blueprints:**
- `auth` → `/auth` — login, register, logout (POST), settings, invitations
- `main` → `/` — dashboard, `/sw.js`, `/manifest.webmanifest`, `/offline`
- `workouts` → `/workouts` — workout CRUD, set logging, and ALL exercise-entry and superset routes
- `exercises` → `/exercises` — browse, detail, `/picker` (paged search for the edit pages)
- `templates` → `/templates` — template pages, public sharing, privacy toggle
- `strava` → `/strava` — OAuth connect, upload, disconnect

**Shared entry routes:** A template is a workout row, so both edit pages call `/workouts/<id>/exercises/...` and `/workouts/<id>/superset/...` (the routes only require ownership). They return `{success, count, html}` where `html` is the re-rendered list (`workouts/_exercise_list.html`), which the page swaps in place — no reloads. Name/notes/schedule are saved by one form to `/workouts/<id>/update-details`.

**Logging:** `/workouts/<id>/log` shows one row per set. Ticking a set POSTs to `/workouts/<id>/exercises/<entry>/sets/<n>` (idempotent; `{"done": false}` removes it). Nothing is stored until a set is ticked. Rows are pre-filled from the plan, else from the last completed session (`gymcore.sets.last_performance`).

**CSRF:** `CSRFProtect` is on for every POST except the `/mcp` proxy. Hand-written forms use `{{ csrf_field() }}`; page scripts go through the `fetch` wrapper in `app/static/js/app.js`, which adds `X-CSRFToken` and `X-Requested-With: fetch` (the latter makes error handlers answer in JSON).

**Frontend JS (`app/static/js/`):**
- `app.js` — loaded on every page: fetch wrapper, `gm.post`, `gm.toast`, `gm.confirm` (also `<form data-confirm="...">`), `gm.queue` (localStorage-backed retry queue for saves), service worker registration. Use these instead of `alert()`/`confirm()`.
- `workout-edit.js` — both edit pages: delegated handlers on `#exercise-list-container`, SortableJS reorder, superset selection, exercise picker sheet.
- `workout-log.js` — logging page: set rows, rest timer, progress, finish flow.
- `sw.js` — service worker; caches static files only, never pages.

**Styling:** `app/static/css/custom.css` starts with the color tokens. Brand purples are fills only; text and outlines on dark surfaces use the `--gm-*-text` tints (contrast-checked). Phones get a bottom tab bar; edit and log pages replace it with a sticky action bar (`body_class` block: `has-actionbar no-tabbar`). Bootstrap and SortableJS are vendored in `app/static/vendor/`.

**Template reuse:** `includes/exercise_card.html` (edit list, picker), `includes/exercise_summary.html` (read-only lists), `includes/workout_row.html`. Exercise details modal (`includes/exercise_details_modal.html`) uses a single delegated `document.addEventListener('click')` handler on `.view-exercise-details`.

**Authentication:** Flask-Login with invitation-only registration (except first user). All protected routes use `@login_required`.

**Production:** `SECRET_KEY` must be set (startup fails otherwise). Gunicorn runs threaded workers (`gthread`) so the streaming `/mcp` proxy does not block a worker. `ProxyFix` middleware with `x_for=2, x_proto=2, x_host=2, x_prefix=2` for Pangolin → Traefik → Flask topology.

## MCP Server

Standalone FastMCP server exposing gym data over HTTP streaming (MCP spec 2025-03-26). Entry point: `python -m mcp_server.server`.

**Module layout:** `mcp_server/server.py` (entry), `mcp_server/db.py` (SQLite), `mcp_server/auth.py` (AuthContext + resolve_auth), `mcp_server/middleware.py` (ASGI auth), `mcp_server/api_key_repository.py` (key CRUD), `mcp_server/tools/` (exercises, workouts, templates, progress).

**API keys:** Generated per-user from `/auth/settings` → MCP API Keys. Stored hashed in the `api_keys` table. Raw key shown once; prefix stored for identification. Key format: `gm_<32 hex chars>`. Two scopes: `read` and `readwrite`.

**Auth:** HTTP transport uses `Authorization: Bearer gm_<key>` or `X-API-Key: gm_<key>` header per request (ASGI middleware). Stdio transport validates `GM_API_KEY` env var once at startup. Each key is scoped to one user — tools only return that user's data.

**Transport env vars:** `GM_MCP_TRANSPORT` (`http`/`stdio`), `GM_MCP_HTTP_HOST`, `GM_MCP_HTTP_PORT` (default 8085), `DATABASE_PATH`.

**`/mcp` proxy:** `app/mcp_proxy/routes.py` — Flask blueprint that reverse-proxies `<appurl>/mcp` to `GM_MCP_URL/mcp` (default `http://127.0.0.1:8085`). Streams the response back so SSE works. The MCP server does not need to be publicly exposed — all traffic goes Flask → MCP internally.

## Database Schema Notes

Key tables: `users`, `workouts` (also stores templates via `is_template=1`), `workout_exercises`, `workout_sets`, `exercises`, `categories`, `muscles`, `equipment`, `invitations`, `strava_connections`, `strava_uploads`, `api_keys`, `schema_version`.

- `workout_sets`: one row per performed set (`workout_exercise_id`, `set_number`, `reps`, `weight`, `duration`). Planned-but-not-done sets are not stored. The `actual_*` columns on `workout_exercises` are a derived summary kept in sync by `gymcore.sets.sync_summary` — never write them directly.
- `workouts.status`: `planned` / `in_progress` / `completed`
- `workouts.is_template`: `0` = workout, `1` = template
- Supersets: exercises share a `superset_group_id` (integer scoped per workout); ordering works on blocks (`gymcore.workouts.renumber`) so a superset always stays contiguous
- Exercise images: `.webp` copies next to the originals are served automatically when present (`Exercise._image_url`)
- Muscle names: `abdominals` (not `core`), `glutes` (not `gluteals`)
- Equipment: `box` (not `plyo box`), `Strap` (ID 26) for TRX/suspension
- Categories: strength, stretching, plyometrics, strongman, cardio, olympic weightlifting, crossfit, calisthenics, suspension (ID 9)
- Image URLs: local filenames get `/static/images/` prefix at read time in `Exercise.get_by_id`; URLs starting with `/` or `http` are used as-is

## Testing

`python -m pytest` — `tests/test_core.py` (data layer, migrations), `tests/test_web.py` (auth, CSRF, ownership, logging, every page renders), `tests/test_mcp.py` (tool ownership and scopes). Fixtures in `tests/conftest.py` build a fresh database from `gymcore/schema.sql` + migrations with two users (alice = 1, bob = 2).

```python
# Manual test client pattern against the real local database
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['_user_id'] = '1'
    # user ID 1 exists; workout ID 1 and template ID 2 available for testing
    # workout ID 11 has supersets
```

## Migration Scripts

Schema changes: add a numbered step to `MIGRATIONS` in `gymcore/migrations.py` (run by `migrations/migrate.py`, one transaction, tracked in `schema_version`). `gymcore/schema.sql` is the version-2 baseline and is not edited.

Data scripts are located in `migrations/`. Always support `--dry-run`, use `exercise_exists()` for idempotency, and check both old and new image filenames (images may already be renamed if migration ran locally first).
