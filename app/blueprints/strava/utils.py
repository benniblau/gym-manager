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


def format_exercise_line(exercise, number_prefix):
    """Format a single exercise line with emoji and details"""
    category_name = exercise.get('category_name')
    emoji = get_category_emoji(category_name)
    parts = [f"{number_prefix}.", emoji, exercise['exercise_name']]

    # Use actual values if available, otherwise target values
    sets = exercise.get('actual_sets') or exercise.get('target_sets')
    reps = exercise.get('actual_reps') or exercise.get('target_reps')
    weight = exercise.get('actual_weight') or exercise.get('target_weight')
    duration = exercise.get('actual_duration') or exercise.get('target_duration')

    if sets or reps or weight or duration:
        details = []
        if sets and reps:
            details.append(f"{sets}x{reps}")
        elif sets:
            details.append(f"{sets} sets")
        elif reps:
            details.append(f"{reps} reps")

        if weight:
            details.append(f"@{weight}kg")

        if duration:
            # Format duration in seconds to a readable format
            if duration >= 60:
                mins = duration // 60
                secs = duration % 60
                if secs > 0:
                    details.append(f"{mins}m{secs}s")
                else:
                    details.append(f"{mins}m")
            else:
                details.append(f"{duration}s")

        if details:
            parts.append(' '.join(details))

    return ' '.join(parts)


def format_workout_description(workout, exercises):
    """Format workout exercises into Strava description with emojis and superset grouping"""
    lines = []

    # Add workout notes/description if present
    if workout.notes:
        lines.append('📝 ' + workout.notes)
        lines.append('')
        lines.append('---')
        lines.append('')

    # Group exercises, tracking supersets
    display_num = 1
    processed_groups = set()
    superset_count = 0

    for exercise in exercises:
        superset_id = exercise.get('superset_group_id')

        if superset_id:
            # Check if we already processed this superset
            if superset_id in processed_groups:
                continue

            processed_groups.add(superset_id)

            # Collect all exercises in this superset
            superset_exercises = [e for e in exercises if e.get('superset_group_id') == superset_id]
            superset_count += 1

            # Get superset rounds (actual or target from first exercise)
            superset_rounds = superset_exercises[0].get('superset_actual_reps') or superset_exercises[0].get('superset_target_reps') if superset_exercises else None

            # Add superset header with rounds if available
            if superset_rounds:
                lines.append(f'🔗 SUPERSET x{superset_rounds} (no rest between):')
            else:
                lines.append(f'🔗 SUPERSET (no rest between):')

            # Add each exercise in the superset with letter suffix
            letters = 'abcdefghijklmnopqrstuvwxyz'
            for idx, ss_exercise in enumerate(superset_exercises):
                letter = letters[idx] if idx < len(letters) else str(idx + 1)
                line = format_exercise_line(ss_exercise, f"{display_num}{letter}")
                lines.append(f"   {line}")

            lines.append('')  # Blank line after superset
            display_num += 1
        else:
            # Standalone exercise
            line = format_exercise_line(exercise, str(display_num))
            lines.append(line)
            display_num += 1

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
    if superset_count > 0:
        lines.append(f'🔗 {superset_count} superset{"s" if superset_count > 1 else ""} performed')

    return '\n'.join(lines)


def calculate_elapsed_time(workout):
    """Calculate workout duration in seconds.

    Priority:
    1. Use duration_minutes if explicitly set
    2. Calculate from started_at and completed_at
    """
    # If duration_minutes is set, use it directly
    if workout.duration_minutes:
        return int(workout.duration_minutes * 60)

    # Otherwise calculate from start/end times
    if not workout.started_at or not workout.completed_at:
        return 60  # Default to 1 minute if no time data

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
