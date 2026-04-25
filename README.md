# Gym Manager

A Flask web application for planning, logging, and analyzing workouts. Built with Python, SQLite, and Bootstrap 5.

<img width="1264" height="1067" alt="ARISE_templates" src="https://github.com/user-attachments/assets/7d84dfb0-c1c3-4e0d-8721-68f91f2fa3e1" />

## Features

- **Workout management** — Create, schedule, log, and complete workouts
- **Exercise library** — Browse 2000+ exercises filterable by category, muscle group, and equipment; each with instructions, illustrations, and difficulty info
- **Workout templates** — Build reusable templates; share publicly with the community or keep private; track usage statistics
- **Superset support** — Group exercises into supersets with independent rep tracking
- **Strava integration** — OAuth connection and activity upload; generate Strava-formatted post text without connecting
- **Invitation-only registration** — Users invite others via email; first registered user becomes admin
- **Responsive, mobile-first UI** — Bootstrap 5 dark theme, touch-friendly controls, auto-saving log values

## Tech Stack

- **Backend**: Flask 3, SQLite (raw queries, no ORM), Flask-Login, Flask-Bcrypt, Flask-WTF
- **Frontend**: Bootstrap 5 dark theme, FontAwesome 6 (CDN), Vanilla JS
- **MCP server**: FastMCP, Starlette, Uvicorn — HTTP streaming transport on port 8085
- **Production**: Gunicorn, systemd, Traefik reverse proxy

## Setup

### Prerequisites

- Python 3.8+

### Installation

```bash
# Clone and enter the project
git clone https://github.com/yourusername/gym-manager.git
cd gym-manager

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum; add Strava keys if needed
```

### Database

```bash
# Initialize database and load exercise library
python database.py
```

This creates `exercises.db` with the full schema and 2000+ exercises.

### Run

```bash
# Development (port 5001)
python run.py

# Production
./start-production.sh
```

## Configuration

All configuration is via `.env`. See `.env.example` for available variables.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret |
| `STRAVA_CLIENT_ID` | Strava only | Strava API client ID |
| `STRAVA_CLIENT_SECRET` | Strava only | Strava API client secret |
| `STRAVA_REDIRECT_URI` | Strava only | OAuth callback URL |
| `PORT` | No | Gunicorn port (default: 8000) |
| `GM_MCP_TRANSPORT` | No | MCP transport: `http` or `stdio` (default: `stdio`) |
| `GM_MCP_HTTP_HOST` | No | MCP bind host (default: `0.0.0.0`) |
| `GM_MCP_HTTP_PORT` | No | MCP bind port (default: `8085`) |
| `GM_MCP_URL` | No | Internal MCP server URL Flask proxies `/mcp` to (default: `http://127.0.0.1:8085`) |
| `DATABASE_PATH` | No | Path to `exercises.db` (default: `./exercises.db`) |

### Strava Setup

1. Create an app at [strava.com/settings/api](https://www.strava.com/settings/api)
2. Set Authorization Callback Domain to your domain (or `localhost`)
3. Copy Client ID and Client Secret to `.env`

## Database Migrations

Migrations are additive scripts in `migrations/`. Run them after upgrading:

```bash
python migrations/add_supersets.py
python migrations/add_superset_reps.py
python migrations/add_public_templates.py
python migrations/add_invitations.py
# etc.
```

Each migration is idempotent and supports `--dry-run`.

```bash
python migrations/add_api_keys_table.py   # MCP API key storage
```

## MCP Server

Gym Manager exposes a [Model Context Protocol](https://modelcontextprotocol.io) server so AI agents (Claude Code, Claude Desktop) can read and write your gym data directly.

**Generate an API key** — log in, go to Settings → MCP API Keys, and click Generate Key. The raw key (`gm_…`) is shown once; copy it immediately.

**Connect from Claude Code** — add to your MCP config:
```json
{
  "gym-manager": {
    "type": "http",
    "url": "http://localhost:8085/mcp",
    "headers": { "Authorization": "Bearer gm_<your-key>" }
  }
}
```

**Start the server:**
```bash
GM_MCP_TRANSPORT=http python -m mcp_server.server
```

**Available tools** (16 total):

| Domain | Tools |
|---|---|
| Exercises | `search_exercises`, `get_exercise`, `list_categories`, `list_muscles`, `list_equipment` |
| Workouts | `list_workouts`, `get_workout`, `create_workout`, `log_exercise`, `complete_workout` |
| Templates | `list_templates`, `get_template`, `create_workout_from_template` |
| Progress | `get_exercise_history`, `get_workout_stats`, `get_muscle_focus` |

Read-scope keys can call all read tools. `create_workout`, `log_exercise`, `complete_workout`, and `create_workout_from_template` require readwrite scope. Every tool is scoped to the key owner's data.

## Production Deployment

The project includes systemd service files in `deploy/` and a Gunicorn config (`gunicorn_config.py`) for Linux deployments. The app uses `ProxyFix` middleware for deployments behind a reverse proxy (Traefik/nginx).

```bash
# Run the migration to add the api_keys table
python migrations/add_api_keys_table.py

# Copy and enable both service files
sudo cp deploy/gym-manager.service /etc/systemd/system/
sudo cp deploy/gym-manager-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gym-manager gym-manager-mcp
```

## Project Structure

```
app/
├── __init__.py          # App factory (create_app)
├── config.py            # Dev / Production / Testing configs
├── models.py            # DB models (User, Workout, Exercise, etc.)
├── utils/               # TCX export, Jinja2 filters
├── blueprints/
│   ├── auth/            # Login, register, settings, invitations, API key management
│   ├── main/            # Dashboard
│   ├── workouts/        # Workout CRUD, logging, supersets
│   ├── exercises/       # Exercise browser
│   ├── templates/       # Template CRUD, public sharing
│   └── strava/          # OAuth, upload, disconnect
├── static/
│   ├── css/custom.css   # Design system overrides
│   ├── js/workout-edit.js  # Workout and template edit page JS
│   └── images/          # Local exercise images
└── templates/
    ├── base.html
    ├── includes/        # Shared macros and modals
    └── ...              # Per-blueprint templates

mcp_server/              # MCP server (FastMCP, HTTP streaming, port 8085)
├── server.py            # Entry point — HTTP or stdio transport
├── db.py                # Standalone SQLite connection
├── auth.py              # AuthContext, resolve_auth
├── middleware.py        # ASGI API key middleware
├── api_key_repository.py  # Key CRUD (shared with Flask routes)
└── tools/               # exercises, workouts, templates, progress

migrations/              # Additive schema migration scripts
deploy/                  # systemd service files
docs/                    # UI design system documentation
database.py              # DB initialization from exercises.json
```

## UI Design System

Before making UI changes, review [`docs/UI_DESIGN_SYSTEM.md`](docs/UI_DESIGN_SYSTEM.md) for color conventions, badge classes, button sizing standards, and component patterns.

## License

MIT — see [LICENSE](LICENSE).
