import pytest
import sys
import os

# Add backend directory to Python path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from extensions import db as _db
from config import TestConfig


@pytest.fixture(scope='session')
def app():
    """Create a Flask app configured for testing."""
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope='function')
def db(app):
    """Create fresh database tables for each test function."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """A Flask test client with a clean database."""
    return app.test_client()
