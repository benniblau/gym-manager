import os

from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException

login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()


def create_app(config_name='development'):
    """Flask application factory"""
    app = Flask(__name__)

    # Load config
    if config_name == 'development':
        app.config.from_object('app.config.DevelopmentConfig')
    elif config_name == 'production':
        app.config.from_object('app.config.ProductionConfig')
    else:
        app.config.from_object('app.config.TestingConfig')

    if config_name == 'production' and not os.environ.get('SECRET_KEY'):
        raise RuntimeError(
            'SECRET_KEY is not set. Generate one with '
            '`python3 -c "import secrets; print(secrets.token_hex(32))"` and add it to .env'
        )

    # Configure for reverse proxy (production)
    # Pangolin -> Traefik -> Flask = 2 proxies
    if config_name == 'production':
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=2,
            x_proto=2,
            x_host=2,
            x_prefix=2
        )

    _check_schema(app.config['DATABASE_PATH'])

    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    bcrypt.init_app(app)
    csrf.init_app(app)

    # Database teardown
    from app.models import close_db
    app.teardown_appcontext(close_db)

    # Register template filters
    from app import utils
    app.jinja_env.filters['exercem_url'] = utils.get_exercem_url
    app.jinja_env.filters['nice_date'] = utils.nice_date
    app.jinja_env.filters['nice_time'] = utils.nice_time
    app.jinja_env.filters['nice_datetime'] = utils.nice_datetime
    app.jinja_env.filters['duration_text'] = utils.duration_text
    app.jinja_env.filters['status_label'] = utils.status_label
    app.jinja_env.filters['plan_text'] = utils.plan_text
    app.jinja_env.globals['csrf_field'] = utils.csrf_field

    # Register blueprints
    from app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.blueprints.main.routes import main_bp
    app.register_blueprint(main_bp)

    from app.blueprints.workouts.routes import workouts_bp
    app.register_blueprint(workouts_bp, url_prefix='/workouts')

    from app.blueprints.exercises.routes import exercises_bp
    app.register_blueprint(exercises_bp, url_prefix='/exercises')

    from app.blueprints.strava import strava_bp
    app.register_blueprint(strava_bp, url_prefix='/strava')

    from app.blueprints.templates import templates_bp
    app.register_blueprint(templates_bp, url_prefix='/templates')

    from app.mcp_proxy import mcp_proxy_bp
    app.register_blueprint(mcp_proxy_bp)  # MCP proxy at /mcp
    csrf.exempt(mcp_proxy_bp)  # authenticated by API key, not by session cookie

    register_error_handlers(app)

    return app


def _check_schema(db_path):
    """Fail at startup, with the fix, if the database is behind the code."""
    if not os.path.isfile(db_path):
        return
    from gymcore.db import connect
    from gymcore.migrations import pending
    conn = connect(db_path)
    try:
        behind = [str(version) for version, _, _ in pending(conn)]
    finally:
        conn.close()
    if behind:
        raise RuntimeError(
            f"Database needs migrations {', '.join(behind)}. "
            'Back it up, then run: python migrations/migrate.py'
        )


def wants_json():
    """True for requests made by the page scripts (see the fetch wrapper in base.html)."""
    return request.headers.get('X-Requested-With') == 'fetch' or request.is_json


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = 'Your session expired. Reload the page and try again.'
        if wants_json():
            return jsonify({'error': message}), 400
        return render_template('errors/error.html', code=400, title='Session expired', message=message), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/mcp'):
            return error
        if wants_json():
            return jsonify({'error': error.description or error.name}), error.code
        messages = {
            404: "That page doesn't exist, or it isn't yours to see.",
            403: "You don't have access to this.",
        }
        return render_template('errors/error.html', code=error.code, title=error.name,
                               message=messages.get(error.code, error.description)), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception('Unhandled error on %s', request.path)
        if wants_json():
            return jsonify({'error': 'Something went wrong on the server.'}), 500
        return render_template('errors/error.html', code=500, title='Something went wrong',
                               message='The error was logged. Please try again.'), 500


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    from app.models import User
    return User.get_by_id(int(user_id))
