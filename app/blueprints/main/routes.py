from flask import Blueprint, current_app, render_template, redirect, send_from_directory, url_for
from flask_login import login_required, current_user
from datetime import date
from app.models import Workout, StravaConnection

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard: what to do today first, history and stats after"""
    today = date.today()
    open_workouts = Workout.get_open_by_user(current_user.id, limit=6)

    # The one workout to put in front of the user: in progress, else due today or overdue
    next_workout = next(
        (w for w in open_workouts
         if w.status == 'in_progress' or (w.scheduled_date and w.scheduled_date <= today.isoformat())),
        None,
    )
    upcoming = [w for w in open_workouts if w is not next_workout]

    recent = [w for w in Workout.get_by_user(current_user.id, limit=20) if w.status == 'completed'][:5]

    return render_template('main/dashboard.html',
                         today=today,
                         next_workout=next_workout,
                         upcoming=upcoming,
                         recent_workouts=recent,
                         counts=Workout.count_by_user(current_user.id),
                         templates=Workout.get_templates_by_user(current_user.id, limit=4),
                         strava_connected=StravaConnection.is_connected(current_user.id))


# ===== PWA FILES =====
# Served from the site root so the service worker can control every page.

@main_bp.route('/sw.js')
def service_worker():
    response = send_from_directory(current_app.static_folder, 'js/sw.js', mimetype='text/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response


@main_bp.route('/manifest.webmanifest')
def manifest():
    return send_from_directory(current_app.static_folder, 'fav/site.webmanifest',
                               mimetype='application/manifest+json')


@main_bp.route('/offline')
def offline():
    return render_template('errors/offline.html')
