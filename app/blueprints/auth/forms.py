from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User


class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username',
                          validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                            validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password',
                             validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Check if username is already taken"""
        user = User.get_by_username(username.data)
        if user is not None:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        """Check if email is already registered"""
        user = User.get_by_email(email.data)
        if user is not None:
            raise ValidationError('Email already registered. Please use a different one.')


class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateEmailForm(FlaskForm):
    """Update email form"""
    email = StringField('New Email', validators=[DataRequired(), Email()])
    password = PasswordField('Current Password', validators=[DataRequired()])
    submit = SubmitField('Update Email')

    def __init__(self, current_user_id, *args, **kwargs):
        super(UpdateEmailForm, self).__init__(*args, **kwargs)
        self.current_user_id = current_user_id

    def validate_email(self, email):
        """Check if email is already registered by another user"""
        user = User.get_by_email(email.data)
        if user is not None and user.id != self.current_user_id:
            raise ValidationError('Email already registered. Please use a different one.')


class UpdatePasswordForm(FlaskForm):
    """Update password form"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password',
                                    validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Update Password')


class UpdateStravaCredentialsForm(FlaskForm):
    """Update Strava credentials form"""
    access_token = StringField('Access Token', validators=[DataRequired()])
    refresh_token = StringField('Refresh Token', validators=[DataRequired()])
    expires_at = StringField('Expires At (Unix timestamp)', validators=[DataRequired()])
    athlete_id = StringField('Athlete ID (optional)')
    athlete_username = StringField('Athlete Username (optional)')
    submit = SubmitField('Update Strava Credentials')
