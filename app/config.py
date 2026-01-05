import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-7f8d9a6b5c4e3d2f1a0b9c8d7e6f5a4b'
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exercises.db')
    WTF_CSRF_ENABLED = True

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
    # In production, SECRET_KEY should be set via environment variable
    # If not set, this will use the default from Config base class (not recommended for production)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests
    WTF_CSRF_ENABLED = False
