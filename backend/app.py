# Main app code for Flask + SQLAlchemy backend implementation

# Import libraries
from flask import Flask
from flask_restful import Api
from flask_migrate import Migrate
from flask_cors import CORS

# Import from other files
from extensions import db, jwt
from resources import WordListResource, WordResource, UserListResource, UserResource, SessionListResource, SessionResource, SessionWordListResource, SessionWordResource, HomeResource, TokenResource, TokenRefreshResource, TokenRevokeResource, MeResource 
from practice_resources import PracticeSessionResource, PracticeMessageResource, PracticeNextWordResource, PracticeSummaryResource
from models import TokenBlocklist
from config import Config


def register_extensions(app):
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app)
    CORS(app, supports_credentials=True)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return TokenBlocklist.is_blocklisted(jti)
    

def register_resources(app):
    api = Api(app, prefix='/api')
    api.add_resource(WordListResource, '/words')
    api.add_resource(WordResource, '/words/<int:id>')
    api.add_resource(UserListResource, '/users')
    api.add_resource(UserResource, '/users/<int:id>')
    api.add_resource(SessionListResource, '/sessions')
    api.add_resource(SessionResource, '/sessions/<int:id>')
    api.add_resource(SessionWordListResource, '/sessions/<int:session_id>/words')
    api.add_resource(SessionWordResource, '/sessions/<int:session_id>/words/<int:word_id>')   
    api.add_resource(HomeResource, '/')
    api.add_resource(TokenResource, '/token')
    api.add_resource(TokenRefreshResource, '/token/refresh')
    api.add_resource(TokenRevokeResource, '/token/revoke')
    api.add_resource(MeResource, '/me')
    
    # Practice session endpoints
    api.add_resource(PracticeSessionResource, '/practice/sessions')
    api.add_resource(PracticeMessageResource, '/practice/sessions/<int:id>/messages')
    api.add_resource(PracticeNextWordResource, '/practice/sessions/<int:id>/next-word')
    api.add_resource(PracticeSummaryResource, '/practice/sessions/<int:id>/summary')

def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)
    register_extensions(app)
    register_resources(app)
    return app



if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)


