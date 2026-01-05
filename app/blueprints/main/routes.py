from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import date
from app.models import Workout, StravaConnection, get_db

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
    """User dashboard"""
    # Get today's workouts
    today = date.today()
    todays_workouts = Workout.get_by_date(current_user.id, today)

    # Get recent workouts
    recent_workouts = Workout.get_recent_by_user(current_user.id, limit=5)

    # Get workout stats
    all_workouts = Workout.get_by_user(current_user.id, limit=1000)
    total_workouts = len(all_workouts)
    completed_workouts = len([w for w in all_workouts if w.status == 'completed'])

    # Get exercise count from database
    db = get_db()
    cursor = db.execute('SELECT COUNT(*) FROM exercises')
    total_exercises = cursor.fetchone()[0]

    # Check Strava connection
    strava_connected = StravaConnection.is_connected(current_user.id)
    strava_username = None
    if strava_connected:
        connection = StravaConnection.get_by_user_id(current_user.id)
        strava_username = connection.get('athlete_username') if connection else None

    return render_template('main/dashboard.html',
                         todays_workouts=todays_workouts,
                         recent_workouts=recent_workouts,
                         total_workouts=total_workouts,
                         completed_workouts=completed_workouts,
                         total_exercises=total_exercises,
                         today=today,
                         strava_connected=strava_connected,
                         strava_username=strava_username)
