"""Tests for password reset flow."""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from models import User, PasswordResetToken
from utils import hash_password, check_password


@pytest.fixture
def user(db):
    user = User(
        username='resetuser',
        email='reset@example.com',
        password=hash_password('OldPassword1'),
        created_ds=datetime.utcnow(),
    )
    user.add()
    return user


class TestPasswordResetRequest:
    """POST /api/password-reset/request"""

    @patch('password_reset_resources.send_password_reset_email', return_value=True)
    def test_request_with_registered_email(self, mock_email, client, user):
        resp = client.post('/api/password-reset/request', json={
            'email': 'reset@example.com',
        })
        assert resp.status_code == 200
        assert resp.json['registered'] is True
        mock_email.assert_called_once()

    def test_request_with_unregistered_email(self, client, db):
        resp = client.post('/api/password-reset/request', json={
            'email': 'nonexistent@example.com',
        })
        assert resp.status_code == 200
        assert resp.json['registered'] is False

    def test_request_with_missing_email(self, client, db):
        resp = client.post('/api/password-reset/request', json={})
        assert resp.status_code == 400
        assert 'error' in resp.json

    @patch('password_reset_resources.send_password_reset_email', return_value=True)
    def test_creates_token_in_db(self, mock_email, client, user, db):
        client.post('/api/password-reset/request', json={
            'email': 'reset@example.com',
        })
        tokens = PasswordResetToken.query.filter_by(user_id=user.id).all()
        assert len(tokens) == 1
        assert tokens[0].used is False
        assert tokens[0].expires_ds > datetime.utcnow()

    @patch('password_reset_resources.send_password_reset_email', return_value=True)
    def test_invalidates_old_tokens_on_new_request(self, mock_email, client, user, db):
        # First request
        client.post('/api/password-reset/request', json={'email': 'reset@example.com'})
        # Second request
        client.post('/api/password-reset/request', json={'email': 'reset@example.com'})

        tokens = PasswordResetToken.query.filter_by(user_id=user.id).order_by(
            PasswordResetToken.id
        ).all()
        assert len(tokens) == 2
        assert tokens[0].used is True  # old token invalidated
        assert tokens[1].used is False  # new token active

    @patch('password_reset_resources.send_password_reset_email', return_value=True)
    def test_case_insensitive_email_lookup(self, mock_email, client, user):
        resp = client.post('/api/password-reset/request', json={
            'email': 'RESET@EXAMPLE.COM',
        })
        assert resp.status_code == 200
        assert resp.json['registered'] is True


class TestPasswordReset:
    """POST /api/password-reset/reset"""

    @pytest.fixture
    def valid_token(self, user, db):
        """Create a valid reset token and return the raw token string."""
        import hashlib
        import secrets
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_ds=datetime.utcnow() + timedelta(hours=1),
        )
        token.add()
        return raw

    def test_reset_with_valid_token(self, client, user, valid_token, db):
        resp = client.post('/api/password-reset/reset', json={
            'token': valid_token,
            'new_password': 'NewPassword1',
        })
        assert resp.status_code == 200
        assert 'message' in resp.json

        # Verify password was changed
        updated_user = User.get_by_id(user.id)
        assert check_password('NewPassword1', updated_user.password)

    def test_reset_marks_token_as_used(self, client, user, valid_token, db):
        client.post('/api/password-reset/reset', json={
            'token': valid_token,
            'new_password': 'NewPassword1',
        })
        tokens = PasswordResetToken.query.filter_by(user_id=user.id).all()
        assert all(t.used for t in tokens)

    def test_cannot_reuse_token(self, client, user, valid_token, db):
        # Use token once
        client.post('/api/password-reset/reset', json={
            'token': valid_token,
            'new_password': 'NewPassword1',
        })
        # Try to use it again
        resp = client.post('/api/password-reset/reset', json={
            'token': valid_token,
            'new_password': 'AnotherPass1',
        })
        assert resp.status_code == 400
        assert 'expired' in resp.json['error'].lower() or 'used' in resp.json['error'].lower()

    def test_expired_token_rejected(self, client, user, db):
        import hashlib
        import secrets
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_ds=datetime.utcnow() - timedelta(hours=1),  # expired
        )
        token.add()

        resp = client.post('/api/password-reset/reset', json={
            'token': raw,
            'new_password': 'NewPassword1',
        })
        assert resp.status_code == 400

    def test_invalid_token_rejected(self, client, db):
        resp = client.post('/api/password-reset/reset', json={
            'token': 'totally-fake-token',
            'new_password': 'NewPassword1',
        })
        assert resp.status_code == 400

    def test_weak_password_rejected(self, client, user, valid_token, db):
        resp = client.post('/api/password-reset/reset', json={
            'token': valid_token,
            'new_password': 'weak',
        })
        assert resp.status_code == 400
        assert 'error' in resp.json

    def test_missing_token_rejected(self, client, db):
        resp = client.post('/api/password-reset/reset', json={
            'new_password': 'NewPassword1',
        })
        assert resp.status_code == 400
