"""
WSGI entry point for production deployment with Gunicorn.

Usage:
    gunicorn --config gunicorn_config.py wsgi:app

    Or with direct arguments:
    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
"""
import os
from app import create_app

# Create the Flask application in production mode
app = create_app('production')

if __name__ == '__main__':
    # This allows running with python wsgi.py for testing
    # In production, use Gunicorn instead
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
