"""Strava integration routes"""
from flask import request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from urllib.parse import urlencode
import requests

from app.blueprints.strava import strava_bp
from app.models import Workout, StravaConnection, StravaUpload
from app.blueprints.strava.utils import (
    generate_state_token,
    verify_state_token,
    get_valid_access_token,
    format_workout_description,
    calculate_elapsed_time,
    format_strava_datetime
)


@strava_bp.route('/connect')
@login_required
def connect():
    """Redirect user to Strava for authorization"""
    # Build authorization URL
    params = {
        'client_id': current_app.config['STRAVA_CLIENT_ID'],
        'redirect_uri': current_app.config['STRAVA_REDIRECT_URI'],
        'response_type': 'code',
        'scope': 'activity:write,activity:read',
        'approval_prompt': 'auto',
        'state': generate_state_token(current_user.id)
    }

    auth_url = f"{current_app.config['STRAVA_AUTHORIZE_URL']}?{urlencode(params)}"
    return redirect(auth_url)


@strava_bp.route('/callback')
@login_required
def callback():
    """Handle OAuth callback and exchange code for tokens"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    # Verify state token (CSRF protection)
    if not verify_state_token(state, current_user.id):
        flash('Invalid authorization request', 'danger')
        return redirect(url_for('main.dashboard'))

    if error:
        flash(f'Strava authorization failed: {error}', 'danger')
        return redirect(url_for('main.dashboard'))

    # Exchange code for tokens
    data = {
        'client_id': current_app.config['STRAVA_CLIENT_ID'],
        'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
        'code': code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.post(
            current_app.config['STRAVA_TOKEN_URL'],
            data=data,
            timeout=10
        )
        response.raise_for_status()
        token_data = response.json()

        # Save connection to database
        StravaConnection.create_or_update(current_user.id, token_data)

        flash('Successfully connected to Strava!', 'success')
    except Exception as e:
        current_app.logger.error(f"Strava connection failed: {e}")
        flash('Failed to connect to Strava. Please try again.', 'danger')

    return redirect(url_for('main.dashboard'))


@strava_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Remove Strava connection"""
    StravaConnection.delete(current_user.id)
    flash('Strava disconnected successfully', 'info')
    return redirect(url_for('main.dashboard'))


@strava_bp.route('/upload/<int:workout_id>', methods=['POST'])
@login_required
def upload_workout(workout_id):
    """Upload a completed workout to Strava"""
    # Verify workout ownership and completion
    workout = Workout.get_by_id(workout_id)
    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Workout not found'}), 404

    if workout.status != 'completed':
        return jsonify({'error': 'Only completed workouts can be uploaded'}), 400

    # Get valid access token
    access_token = get_valid_access_token(current_user.id)
    if not access_token:
        return jsonify({'error': 'Not connected to Strava. Please connect your Strava account first.'}), 401

    # Check that workout has start and end times set
    if not workout.started_at or not workout.completed_at:
        return jsonify({
            'error': 'Please set start and end times for the workout before uploading to Strava. You can edit these in the workout edit page.'
        }), 400

    # Get workout exercises
    exercises = workout.get_exercises()

    if not exercises:
        return jsonify({'error': 'Cannot upload workout without exercises'}), 400

    # Prepare activity data
    activity_data = {
        'name': workout.name,
        'sport_type': 'WeightTraining',  # Strava activity type for gym workouts
        'start_date_local': format_strava_datetime(workout),
        'elapsed_time': calculate_elapsed_time(workout),
        'description': format_workout_description(workout, exercises),
        'trainer': 1,  # Indoor activity
        'commute': 0
    }

    # Upload to Strava
    try:
        response = requests.post(
            f"{current_app.config['STRAVA_API_BASE_URL']}/activities",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json=activity_data,
            timeout=10
        )
        response.raise_for_status()
        strava_activity = response.json()

        # Record successful upload
        StravaUpload.record_upload(
            workout_id=workout_id,
            user_id=current_user.id,
            strava_activity_id=strava_activity['id'],
            status='success'
        )

        return jsonify({
            'success': True,
            'strava_activity_id': strava_activity['id'],
            'url': f"https://www.strava.com/activities/{strava_activity['id']}"
        })

    except requests.exceptions.HTTPError as e:
        error_msg = 'Upload failed'

        if e.response.status_code == 429:
            error_msg = 'Strava rate limit exceeded. Please try again later.'
        elif e.response.status_code == 401:
            error_msg = 'Strava authorization expired. Please reconnect your account.'
            # Delete invalid connection
            StravaConnection.delete(current_user.id)
        else:
            error_msg = f'Strava API error: {e.response.status_code}'

        current_app.logger.error(f"Strava upload error: {e}")

        # Record failed upload (allow retry)
        StravaUpload.record_upload(
            workout_id=workout_id,
            user_id=current_user.id,
            strava_activity_id=0,
            status='failed',
            error=error_msg
        )

        return jsonify({'error': error_msg}), 500

    except Exception as e:
        error_msg = f'Upload failed: {str(e)}'
        current_app.logger.error(f"Strava upload error: {e}")

        # Record failed upload
        StravaUpload.record_upload(
            workout_id=workout_id,
            user_id=current_user.id,
            strava_activity_id=0,
            status='failed',
            error=error_msg
        )

        return jsonify({'error': error_msg}), 500


@strava_bp.route('/status')
@login_required
def status():
    """Check Strava connection status (AJAX endpoint)"""
    connected = StravaConnection.is_connected(current_user.id)
    connection_data = None

    if connected:
        connection_data = StravaConnection.get_by_user_id(current_user.id)

    return jsonify({
        'connected': connected,
        'athlete_username': connection_data.get('athlete_username') if connection_data else None
    })
