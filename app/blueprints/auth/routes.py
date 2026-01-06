from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from app.blueprints.auth.forms import RegistrationForm, LoginForm, UpdateEmailForm, UpdatePasswordForm, UpdateStravaCredentialsForm
from app.models import User, StravaConnection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():
        # Create user
        user = User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )

        flash('Registration successful! You are now logged in.', 'success')

        # Log user in automatically
        login_user(user)
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.get_by_username(form.username.data)

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)

        login_user(user, remember=form.remember_me.data)
        user.update_last_login()

        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')

        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """User settings page"""
    email_form = UpdateEmailForm(current_user.id)
    password_form = UpdatePasswordForm()
    strava_form = UpdateStravaCredentialsForm()

    # Get Strava connection info
    strava_connection = StravaConnection.get_by_user_id(current_user.id)

    # Pre-populate Strava form if connection exists
    if strava_connection:
        strava_form.access_token.data = strava_connection.get('access_token', '')
        strava_form.refresh_token.data = strava_connection.get('refresh_token', '')
        strava_form.expires_at.data = str(strava_connection.get('expires_at', ''))
        strava_form.athlete_id.data = str(strava_connection.get('athlete_id', '')) if strava_connection.get('athlete_id') else ''
        strava_form.athlete_username.data = strava_connection.get('athlete_username', '')

    return render_template('auth/settings.html',
                         email_form=email_form,
                         password_form=password_form,
                         strava_form=strava_form,
                         strava_connection=strava_connection)


@auth_bp.route('/settings/update-email', methods=['POST'])
@login_required
def update_email():
    """Update user email"""
    form = UpdateEmailForm(current_user.id)

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.password.data):
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('auth.settings'))

        # Update email
        current_user.update_email(form.email.data)
        flash('Email updated successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')

    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/update-password', methods=['POST'])
@login_required
def update_password():
    """Update user password"""
    form = UpdatePasswordForm()

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Incorrect current password. Please try again.', 'danger')
            return redirect(url_for('auth.settings'))

        # Update password
        current_user.update_password(form.new_password.data)
        flash('Password updated successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')

    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/update-strava-credentials', methods=['POST'])
@login_required
def update_strava_credentials():
    """Update Strava credentials manually"""
    form = UpdateStravaCredentialsForm()

    if form.validate_on_submit():
        try:
            # Validate expires_at is a number
            expires_at = int(form.expires_at.data)

            # Prepare token data
            token_data = {
                'access_token': form.access_token.data,
                'refresh_token': form.refresh_token.data,
                'expires_at': expires_at,
                'athlete': {
                    'id': int(form.athlete_id.data) if form.athlete_id.data else None,
                    'username': form.athlete_username.data if form.athlete_username.data else None
                }
            }

            # Create or update Strava connection
            StravaConnection.create_or_update(current_user.id, token_data)
            flash('Strava credentials updated successfully!', 'success')
        except ValueError:
            flash('Invalid expires_at timestamp. Please enter a Unix timestamp (e.g., 1704067200)', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')

    return redirect(url_for('auth.settings'))
