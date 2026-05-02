"""Tests for account deletion."""
import pytest
from datetime import datetime, timezone

from flask_jwt_extended import create_access_token

from models import User, UserProfile, Deck, Word, UserSession, SessionWord, SessionWordAttempt
from utils import hash_password


@pytest.fixture
def user_with_data(db):
    """Create a user with profile, deck, words, and a practice session."""
    user = User(
        username='deleteuser',
        email='delete@example.com',
        password=hash_password('TestPassword1'),
        created_ds=datetime.now(timezone.utc),
    )
    user.add()

    profile = UserProfile(user_id=user.id, preferred_name='Delete Me')
    profile.add()

    deck = Deck(name='Test Deck', user_id=user.id)
    deck.add()

    word = Word(
        word='测试', pinyin='cèshì', meaning='test',
        user_id=user.id, deck_id=deck.id,
    )
    word.add()

    session = UserSession(
        user_id=user.id,
        deck_id=deck.id,
        session_start_ds=datetime.now(timezone.utc),
        words_per_session=1,
    )
    session.add()

    sw = SessionWord(
        word_id=word.id,
        session_id=session.id,
        session_word_load_ds=datetime.now(timezone.utc),
        word_order=0,
    )
    sw.add()

    attempt = SessionWordAttempt(
        word_id=word.id,
        session_id=session.id,
        attempt_number=1,
        sentence='这是测试',
        grammar_score=8.0,
        usage_score=7.0,
        naturalness_score=6.0,
        is_correct=True,
    )
    attempt.add()

    return user


class TestAccountDelete:
    """DELETE /api/account"""

    def _auth_header(self, user, app):
        with app.app_context():
            token = create_access_token(identity=str(user.id))
            return {'Authorization': f'Bearer {token}'}

    def test_deletes_account_with_correct_password(self, client, app, user_with_data, db):
        uid = user_with_data.id
        headers = self._auth_header(user_with_data, app)
        resp = client.delete('/api/account', json={
            'password': 'TestPassword1',
        }, headers=headers)

        assert resp.status_code == 200
        assert User.get_by_id(uid) is None

    def test_deletes_all_related_data(self, client, app, user_with_data, db):
        uid = user_with_data.id
        headers = self._auth_header(user_with_data, app)

        client.delete('/api/account', json={'password': 'TestPassword1'}, headers=headers)

        assert UserProfile.query.filter_by(user_id=uid).first() is None
        assert Deck.query.filter_by(user_id=uid).first() is None
        assert Word.query.filter_by(user_id=uid).first() is None
        assert UserSession.query.filter_by(user_id=uid).first() is None
        assert SessionWord.query.all() == []
        assert SessionWordAttempt.query.all() == []

    def test_rejects_wrong_password(self, client, app, user_with_data, db):
        headers = self._auth_header(user_with_data, app)
        resp = client.delete('/api/account', json={
            'password': 'WrongPassword1',
        }, headers=headers)

        assert resp.status_code == 403
        assert User.get_by_id(user_with_data.id) is not None

    def test_rejects_missing_password(self, client, app, user_with_data, db):
        headers = self._auth_header(user_with_data, app)
        resp = client.delete('/api/account', json={}, headers=headers)

        assert resp.status_code == 400

    def test_requires_authentication(self, client, db):
        resp = client.delete('/api/account', json={'password': 'anything'})
        assert resp.status_code == 401
