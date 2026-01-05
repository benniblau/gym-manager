"""Strava integration utility functions"""
import secrets
import time
import requests
from flask import session, current_app
from datetime import datetime, time as dt_time
from app.models import get_db


def generate_state_token(user_id):
    """Generate state token for OAuth flow (CSRF protection)"""
    token = secrets.token_urlsafe(32)
    session['strava_state'] = {
        'token': token,
        'user_id': user_id,
        'timestamp': time.time()
    }
    return token


def verify_state_token(token, user_id):
    """Verify state token"""
    state_data = session.get('strava_state')

    if not state_data:
        return False

    # Check token matches
    if state_data.get('token') != token:
        return False

    # Check user_id matches
    if state_data.get('user_id') != user_id:
        return False

    # Check token age (max 10 minutes)
    if time.time() - state_data.get('timestamp', 0) > 600:
        return False

    # Clear state after verification
    session.pop('strava_state', None)
    return True


def get_valid_access_token(user_id):
    """Get valid access token, refreshing if needed"""
    db = get_db()
    connection = db.execute(
        'SELECT access_token, expires_at, refresh_token FROM strava_connections WHERE user_id = ?',
        (user_id,)
    ).fetchone()

    if not connection:
        return None

    # Check if expires within 1 hour
    if connection['expires_at'] < (time.time() + 3600):
        return refresh_access_token(user_id, connection['refresh_token'])

    return connection['access_token']


def refresh_access_token(user_id, refresh_token):
    """Refresh expired access token"""
    db = get_db()

    data = {
        'client_id': current_app.config['STRAVA_CLIENT_ID'],
        'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    try:
        response = requests.post(
            current_app.config['STRAVA_TOKEN_URL'],
            data=data,
            timeout=10
        )
        response.raise_for_status()
        token_data = response.json()

        # Update database
        db.execute('''
            UPDATE strava_connections
            SET access_token = ?, refresh_token = ?, expires_at = ?, updated_at = ?
            WHERE user_id = ?
        ''', (
            token_data['access_token'],
            token_data['refresh_token'],
            token_data['expires_at'],
            datetime.now(),
            user_id
        ))
        db.commit()

        return token_data['access_token']
    except Exception as e:
        current_app.logger.error(f"Token refresh failed: {e}")
        return None


def get_category_emoji(category_name):
    """Get emoji based on exercise category"""
    category_emojis = {
        'strength': '💪',
        'stretching': '🧘',
        'plyometrics': '🦘',
        'strongman': '🏋️',
        'cardio': '🏃',
        'olympic weightlifting': '🏋️‍♀️',
        'crossfit': '🔥',
        'calisthenics': '🤸'
    }
    return category_emojis.get(category_name.lower() if category_name else '', '🏋️')


def format_workout_description(workout, exercises):
    """Format workout exercises into Strava description with emojis"""
    lines = []

    # Header with emoji
    lines.append('💪 Gym Workout')
    lines.append('')

    # Add workout notes if present
    if workout.notes:
        lines.append(workout.notes)
        lines.append('')

    # Add each exercise
    for exercise in exercises:
        # Get category-specific emoji
        category_name = exercise.get('category_name')
        emoji = get_category_emoji(category_name)
        parts = [emoji, exercise['exercise_name']]

        # Use actual values if available, otherwise target values
        sets = exercise.get('actual_sets') or exercise.get('target_sets')
        reps = exercise.get('actual_reps') or exercise.get('target_reps')
        weight = exercise.get('actual_weight') or exercise.get('target_weight')

        if sets or reps or weight:
            details = []
            if sets and reps:
                details.append(f"{sets}x{reps}")
            elif sets:
                details.append(f"{sets} sets")
            elif reps:
                details.append(f"{reps} reps")

            if weight:
                details.append(f"@{weight}kg")

            if details:
                parts.append(' '.join(details))

        lines.append(' '.join(parts))

    # Add footer with stats
    lines.append('')
    elapsed_seconds = calculate_elapsed_time(workout)
    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60

    if hours > 0:
        duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = f"{minutes}m"

    lines.append(f'⏱️ Duration: {duration_str}')
    lines.append(f'📊 {len(exercises)} exercises completed')

    return '\n'.join(lines)


def calculate_elapsed_time(workout):
    """Calculate workout duration in seconds from explicit start/end times"""
    # Parse started_at
    if isinstance(workout.started_at, str):
        started = datetime.fromisoformat(workout.started_at)
    else:
        started = workout.started_at

    # Parse completed_at
    if isinstance(workout.completed_at, str):
        completed = datetime.fromisoformat(workout.completed_at)
    else:
        completed = workout.completed_at

    # Calculate elapsed time
    elapsed = (completed - started).total_seconds()

    # Return duration in seconds (minimum 60 seconds)
    return int(max(elapsed, 60))


def format_strava_datetime(workout):
    """Format workout start time for Strava API (ISO 8601)"""
    # Parse started_at
    if isinstance(workout.started_at, str):
        dt = datetime.fromisoformat(workout.started_at)
    else:
        dt = workout.started_at

    # Return ISO 8601 format (Strava expects local time without timezone)
    return dt.strftime('%Y-%m-%dT%H:%M:%S')
