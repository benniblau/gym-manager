from flask import Blueprint

templates_bp = Blueprint('templates', __name__)

from app.blueprints.templates import routes
