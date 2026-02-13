# This file stores the configs for the Flask app
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')

class Config():
    # Database configs
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQL_ALCHEMY_TRACK_MODIFICATIONS = False

    # JWT configs
    SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ERROR_MESSAGE_KEY = 'message'

    # Flask configs
    DEBUG=True
    PROPAGATE_EXCEPTIONS = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-secret-key'

