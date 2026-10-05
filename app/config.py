import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration"""
    # Development fallback only; production refuses to start without SECRET_KEY (see create_app)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-7f8d9a6b5c4e3d2f1a0b9c8d7e6f5a4b'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exercises.db')
    WTF_CSRF_ENABLED = True
    # Tokens live as long as the session: a logging page stays open for a whole workout
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # External URL for generating absolute URLs (used in production)
    EXTERNAL_URL = os.environ.get('EXTERNAL_URL')

# Strava API Credentials
    STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
    STRAVA_ACCESS_TOKEN = os.environ.get('STRAVA_ACCESS_TOKEN')
    STRAVA_REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

    # Strava OAuth
    STRAVA_AUTHORIZE_URL = 'https://www.strava.com/oauth/authorize'
    STRAVA_TOKEN_URL = 'https://www.strava.com/oauth/token'
    STRAVA_API_BASE_URL = 'https://www.strava.com/api/v3'
    # Redirect URI built from HOST, or can be overridden directly
    STRAVA_REDIRECT_URI = os.environ.get('STRAVA_REDIRECT_URI') 

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests
    WTF_CSRF_ENABLED = False
