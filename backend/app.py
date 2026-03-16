# Main app code for Flask + SQLAlchemy backend implementation

# Import libraries
import os
import logging
import sys
from flask import Flask
from flask_restful import Api
from flask_migrate import Migrate
from flask_cors import CORS
# Import from other files
from extensions import db, jwt, limiter
from resources import WordListResource, WordResource, WordMarkAsMasteredResource, RerateWordResource, UserListResource, UserResource, HomeResource, TokenResource, TokenRefreshResource, TokenRevokeResource, MeResource
from practice_resources import PracticeSessionResource, PracticeSessionDetailResource, PracticeMessageResource, PracticeNextWordResource, PracticeSummaryResource, PracticeEndSessionResource
from progress_resources import ProgressStatsResource
from settings_resources import UserSettingsResource, UserSettingsKeyResource, UserSettingsKeyValidateResource
from report_card_resources import ReportCardResource, GenerateFeedbackResource, StreakResource
from deck_resources import deck_bp
from models import TokenBlocklist
from config import Config


def register_extensions(app):
    db.init_app(app)
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migrate = Migrate(app, db, directory=migrations_dir)
    jwt.init_app(app)
    CORS(app)
    limiter.init_app(app)
    # Set default rate limits
    limiter.default_limits = ["200 per minute"]

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return TokenBlocklist.is_blocklisted(jti)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"error": "Rate limit exceeded. Try again later."}, 429
    

def register_resources(app):
    app.config['PROPAGATE_EXCEPTIONS'] = True
    api = Api(app, prefix='/api', errors={})

    # Register deck blueprint
    app.register_blueprint(deck_bp, url_prefix='/api')

    api.add_resource(WordListResource, '/words')
    api.add_resource(WordResource, '/words/<int:id>')
    api.add_resource(WordMarkAsMasteredResource, '/words/<int:word_id>/mark-as-mastered')
    api.add_resource(RerateWordResource, '/words/<int:id>/rerate')
    api.add_resource(UserListResource, '/users')
    api.add_resource(UserResource, '/users/<int:id>')
    api.add_resource(HomeResource, '/')
    api.add_resource(TokenResource, '/token')
    api.add_resource(TokenRefreshResource, '/token/refresh')
    api.add_resource(TokenRevokeResource, '/token/revoke')
    api.add_resource(MeResource, '/me')
    
    # Practice session endpoints
    api.add_resource(PracticeSessionResource, '/practice/sessions')
    api.add_resource(PracticeSessionDetailResource, '/practice/sessions/<int:id>')
    api.add_resource(PracticeMessageResource, '/practice/sessions/<int:id>/messages')
    api.add_resource(PracticeNextWordResource, '/practice/sessions/<int:id>/next-word')
    api.add_resource(PracticeEndSessionResource, '/practice/sessions/<int:id>/end')
    api.add_resource(PracticeSummaryResource, '/practice/sessions/<int:id>/summary')

    # Progress and settings endpoints
    api.add_resource(ProgressStatsResource, '/progress/stats')
    api.add_resource(UserSettingsResource, '/settings')
    api.add_resource(UserSettingsKeyResource, '/settings/keys/<string:provider>')
    api.add_resource(UserSettingsKeyValidateResource, '/settings/keys/<string:provider>/validate')

    # Report card endpoints
    api.add_resource(ReportCardResource, '/progress/report-card')
    api.add_resource(GenerateFeedbackResource, '/progress/generate-feedback')
    api.add_resource(StreakResource, '/progress/streak')

def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)

    # Configure logging to stdout so cloud platforms capture it
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    logger = logging.getLogger(__name__)

    # Validate required config
    if not app.config.get('ENCRYPTION_KEY'):
        logger.warning("ENCRYPTION_KEY is not set. API key encryption will fail.")

    register_extensions(app)
    register_resources(app)

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        logger.exception("Unhandled exception: %s", e)
        return {"error": "An internal error occurred"}, 500

    # Ensure all tables exist before first request
    with app.app_context():
        from flask_migrate import upgrade, stamp
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if not tables or tables == ['alembic_version']:
            # Fresh database: create all tables from current models, then
            # stamp migration head so Alembic knows no migrations need to run
            db.create_all()
            stamp(revision='head')
        else:
            # Existing database: apply any pending migrations
            upgrade()

    logger.info("App startup complete. Tables verified.")
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


