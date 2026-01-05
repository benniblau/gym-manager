from flask import Blueprint

strava_bp = Blueprint('strava', __name__)

from app.blueprints.strava import routes
