# Gym Manager

A Flask web application for planning, logging, and analyzing workouts. Built with Python, SQLite, and Bootstrap 5.

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
| `PORT` | No | Production port (default: 8000) |

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

## Production Deployment

The project includes a systemd service file (`gym-manager.service`) and Gunicorn config (`gunicorn_config.py`) for Linux deployments. The app uses `ProxyFix` middleware for deployments behind a reverse proxy (Traefik/nginx).

```bash
# Copy and edit the service file
sudo cp gym-manager.service /etc/systemd/system/
sudo systemctl enable --now gym-manager
```

## Project Structure

```
app/
├── __init__.py          # App factory (create_app)
├── config.py            # Dev / Production / Testing configs
├── models.py            # DB models (User, Workout, Exercise, etc.)
├── utils/               # TCX export, Jinja2 filters
├── blueprints/
│   ├── auth/            # Login, register, settings, invitations
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

migrations/              # Additive schema migration scripts
docs/                    # UI design system documentation
database.py              # DB initialization from exercises.json
```

## UI Design System

Before making UI changes, review [`docs/UI_DESIGN_SYSTEM.md`](docs/UI_DESIGN_SYSTEM.md) for color conventions, badge classes, button sizing standards, and component patterns.

## License

MIT — see [LICENSE](LICENSE).
