from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

login_manager = LoginManager()
bcrypt = Bcrypt()


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

    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    bcrypt.init_app(app)

    # Database teardown
    from app.models import close_db
    app.teardown_appcontext(close_db)

    # Register template filters
    from app.utils import get_exercem_url
    app.jinja_env.filters['exercem_url'] = get_exercem_url

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

    return app


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    from app.models import User
    return User.get_by_id(int(user_id))
