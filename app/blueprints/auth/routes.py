from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from app.blueprints.auth.forms import RegistrationForm, LoginForm, UpdateEmailForm, UpdatePasswordForm, UpdateStravaCredentialsForm, InviteForm
from app.models import User, StravaConnection, Invitation, get_db
from mcp_server.api_key_repository import ApiKeyRepository

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration redirect - requires invitation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Check if this is the first user (bootstrap)
    if User.count() == 0:
        # Allow first user to register without invitation
        form = RegistrationForm()
        # Remove invitation token requirement for first user
        form.invitation_token.validators = []

        if form.validate_on_submit():
            user = User.create(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            flash('Registration successful! You are now logged in as the first user.', 'success')
            login_user(user)
            return redirect(url_for('main.dashboard'))

        return render_template('auth/register.html', form=form, first_user=True)

    # Not first user - require invitation
    flash('Registration requires an invitation. Please ask an existing user for an invite link.', 'info')
    return redirect(url_for('auth.login'))


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

    api_keys = ApiKeyRepository(get_db()).get_keys_for_user(current_user.id)
    new_api_key = session.pop('new_api_key', None)

    return render_template('auth/settings.html',
                         email_form=email_form,
                         password_form=password_form,
                         strava_form=strava_form,
                         strava_connection=strava_connection,
                         api_keys=api_keys,
                         new_api_key=new_api_key)


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


@auth_bp.route('/settings/api-keys/create', methods=['POST'])
@login_required
def create_api_key():
    """Generate a new MCP API key for the current user."""
    scope = request.form.get('scope', 'read')
    label = request.form.get('label', '').strip() or None

    if scope not in ('read', 'readwrite'):
        flash('Invalid scope.', 'danger')
        return redirect(url_for('auth.settings'))

    result = ApiKeyRepository(get_db()).create_key(current_user.id, scope=scope, label=label)
    session['new_api_key'] = result['raw_key']
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/api-keys/<int:key_id>/delete', methods=['POST'])
@login_required
def delete_api_key(key_id):
    """Revoke an MCP API key belonging to the current user."""
    deleted = ApiKeyRepository(get_db()).delete_key(key_id, current_user.id)
    if deleted:
        flash('API key revoked.', 'success')
    else:
        flash('Key not found.', 'danger')
    return redirect(url_for('auth.settings'))


@auth_bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite():
    """Send invitation (create token)"""
    form = InviteForm()

    if form.validate_on_submit():
        invitation = Invitation.create(
            sender_id=current_user.id,
            recipient_email=form.recipient_email.data,
            notes=form.notes.data
        )

        # Generate full URL
        invite_url = url_for('auth.accept_invite',
                            token=invitation.token,
                            _external=True)

        flash(f'Invitation created! Share this link: {invite_url}', 'success')
        return redirect(url_for('auth.invitations'))

    return render_template('auth/invite.html', form=form)


@auth_bp.route('/invitations')
@login_required
def invitations():
    """Manage user's invitations"""
    pending = Invitation.get_by_sender(current_user.id, status='pending')
    accepted = Invitation.get_by_sender(current_user.id, status='accepted')

    return render_template('auth/invitations.html',
                          pending=pending,
                          accepted=accepted)


@auth_bp.route('/invitations/<int:invitation_id>/revoke', methods=['POST'])
@login_required
def revoke_invite(invitation_id):
    """Revoke pending invitation"""
    invitation = Invitation.get_by_id(invitation_id)

    if not invitation or invitation.sender_id != current_user.id:
        abort(404)

    if invitation.status != 'pending':
        flash('Can only revoke pending invitations.', 'danger')
        return redirect(url_for('auth.invitations'))

    invitation.revoke()
    flash('Invitation revoked.', 'success')
    return redirect(url_for('auth.invitations'))


@auth_bp.route('/invite/<token>')
def accept_invite(token):
    """Preview/accept invitation"""
    invitation = Invitation.get_by_token(token)

    if not invitation:
        flash('Invalid invitation link.', 'danger')
        return redirect(url_for('auth.login'))

    if not invitation.is_valid():
        flash('This invitation has expired or is no longer valid.', 'warning')
        return redirect(url_for('auth.login'))

    # Get sender info
    sender = User.get_by_id(invitation.sender_id)

    return render_template('auth/accept_invite.html',
                          invitation=invitation,
                          sender=sender)


@auth_bp.route('/register/<token>', methods=['GET', 'POST'])
def register_with_invite(token):
    """Register with invitation token"""
    invitation = Invitation.get_by_token(token)

    if not invitation or not invitation.is_valid():
        flash('Invalid or expired invitation.', 'danger')
        return redirect(url_for('auth.login'))

    form = RegistrationForm()
    form.invitation_token.data = token

    # Pre-fill email if provided
    if invitation.recipient_email and not form.email.data:
        form.email.data = invitation.recipient_email

    if form.validate_on_submit():
        user = User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            invited_by=invitation.sender_id,
            invitation_id=invitation.id
        )

        # Mark invitation as accepted
        invitation.accept(user.id)

        flash('Registration successful! You are now logged in.', 'success')
        login_user(user)
        return redirect(url_for('main.dashboard'))

    sender = User.get_by_id(invitation.sender_id)
    return render_template('auth/register.html',
                          form=form,
                          invitation=invitation,
                          sender=sender)
