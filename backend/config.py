# This file stores the configs for the Flask app
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')

class Config():
    # Database configs
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQL_ALCHEMY_TRACK_MODIFICATIONS = False

    # JWT configs
    SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ERROR_MESSAGE_KEY = 'message'

    # JWT Token Expiry
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # JWT Token Locations -- accept access tokens from headers, refresh from cookies
    JWT_TOKEN_LOCATION = ['headers', 'cookies']

    # JWT Cookie Settings
    JWT_REFRESH_COOKIE_PATH = '/api/token'
    JWT_COOKIE_SECURE = False               # Set True in production (requires HTTPS)
    JWT_COOKIE_SAMESITE = 'Strict'
    JWT_COOKIE_CSRF_PROTECT = False          # SameSite=Strict is sufficient for MVP

    # Flask configs
    DEBUG=True
    PROPAGATE_EXCEPTIONS = True

    # Practice session settings
    DEFAULT_WORDS_PER_SESSION = 10

    # Encryption for BYOK API keys
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    # Rate limiting - use memory storage to avoid Redis connection issues
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-secret-key'
    JWT_COOKIE_SECURE = False  # Allow HTTP in tests
    DEFAULT_WORDS_PER_SESSION = 5  # Smaller for faster tests
    # Valid Fernet key for deterministic tests (32 bytes base64-encoded)
    ENCRYPTION_KEY = 'dGVzdC1lbmNyeXB0aW9uLWtleS0xMjM0NTY3ODkwMTIzNDU2Nzg5MA=='
    RATELIMIT_ENABLED = False  # Disable rate limiting in tests

