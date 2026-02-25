from models import TokenBlocklist
from datetime import datetime


def test_add_to_blocklist(db):
    """TokenBlocklist.add() should persist a jti to the database."""
    entry = TokenBlocklist(jti='test-jti-123', created_ds=datetime.now())
    entry.add()
    assert TokenBlocklist.is_blocklisted('test-jti-123') is True


def test_is_blocklisted_returns_false_for_unknown_jti(db):
    """is_blocklisted should return False for a jti not in the table."""
    assert TokenBlocklist.is_blocklisted('nonexistent-jti') is False
