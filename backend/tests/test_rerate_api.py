"""Tests for POST /api/words/:id/rerate endpoint (T-7.28).

Tests the retroactive rating editing feature that restores SRS state
from a snapshot and applies a new quality rating (true undo+redo).
"""
import pytest
import json
from datetime import date
from unittest.mock import Mock, patch

from models import User, Word, UserSession, SessionWord, SessionWordAttempt


class TestRerateEndpoint:
    """Integration tests for the rerate word endpoint."""

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and return auth headers."""
        resp = client.post('/api/users', json={
            'username': 'rerateuser',
            'email': 'rerate@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        resp = client.post('/api/token', json={
            'username': 'rerateuser',
            'password': 'TestPass123'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        return {'Authorization': f'Bearer {data["access_token"]}'}

    @pytest.fixture
    def user_with_session(self, db, auth_headers, client):
        """Create a user with a word, session, and session_word that has an SRS snapshot."""
        user = User.query.filter_by(username='rerateuser').first()

        # Create a word with known SRS state
        word = Word(
            user_id=user.id,
            word='你好',
            reading='ni hao',
            meaning='hello',
            repetitions=2,
            interval_days=7,
            ease_factor=2.5,
            next_review_date=date(2026, 3, 20),
            last_quality=4,
            is_mastered=False,
        )
        word.add()

        # Create a session
        session = UserSession(user_id=user.id)
        session.add()

        # Create a session word with SRS snapshot (pre-rating state)
        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=1,  # completed
            srs_snapshot={
                'repetitions': 1,
                'interval_days': 3,
                'ease_factor': 2.5,
                'next_review_date': '2026-03-16',
                'is_mastered': False,
                'last_quality': 3,
            }
        )
        sw.add()

        return user, word, session, sw

    def test_rerate_requires_auth(self, client):
        """Should return 401 without authentication."""
        resp = client.post('/api/words/1/rerate', json={
            'quality': 3,
            'session_id': 1,
        })
        assert resp.status_code == 401

    def test_rerate_missing_quality(self, client, auth_headers, user_with_session):
        """Should return 400 when quality is missing."""
        _, word, session, _ = user_with_session
        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'session_id': session.id}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'quality' in data['error'].lower() or 'required' in data['error'].lower()

    def test_rerate_missing_session_id(self, client, auth_headers, user_with_session):
        """Should return 400 when session_id is missing."""
        _, word, _, _ = user_with_session
        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 3}
        )
        assert resp.status_code == 400

    def test_rerate_invalid_quality_range(self, client, auth_headers, user_with_session):
        """Should return 400 when quality is outside 0-5."""
        _, word, session, _ = user_with_session
        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 6, 'session_id': session.id}
        )
        assert resp.status_code == 400

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': -1, 'session_id': session.id}
        )
        assert resp.status_code == 400

    def test_rerate_word_not_found(self, client, auth_headers):
        """Should return 404 for non-existent word."""
        resp = client.post(
            '/api/words/99999/rerate',
            headers=auth_headers,
            json={'quality': 3, 'session_id': 1}
        )
        assert resp.status_code == 404

    def test_rerate_word_belongs_to_other_user(self, client, db, auth_headers):
        """Should return 404 when word belongs to another user."""
        # Create another user with a word
        other_user = User(username='otheruser', email='other@example.com')
        other_user.password = 'hashed'
        other_user.add()

        other_word = Word(
            user_id=other_user.id,
            word='测试',
            reading='ce shi',
            meaning='test',
        )
        other_word.add()

        resp = client.post(
            f'/api/words/{other_word.id}/rerate',
            headers=auth_headers,
            json={'quality': 3, 'session_id': 1}
        )
        assert resp.status_code == 404

    def test_rerate_no_snapshot_returns_400(self, client, db, auth_headers):
        """Should return 400 when session word has no SRS snapshot."""
        user = User.query.filter_by(username='rerateuser').first()
        word = Word(user_id=user.id, word='再见', reading='zai jian', meaning='goodbye')
        word.add()

        session = UserSession(user_id=user.id)
        session.add()

        # Session word WITHOUT snapshot
        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=1,
        )
        sw.add()

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 3, 'session_id': session.id}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'snapshot' in data['error'].lower()

    def test_rerate_restores_snapshot_and_applies_new_quality(self, client, db, auth_headers, user_with_session):
        """Core test: rerate should restore SRS from snapshot, then apply new quality.

        The word currently has:
          repetitions=2, interval_days=7, ease_factor=2.5, last_quality=4

        The snapshot (pre-original-rating state) has:
          repetitions=1, interval_days=3, ease_factor=2.5, last_quality=3

        After rerate with quality=5:
          1. Restore to snapshot: repetitions=1, interval_days=3, ease_factor=2.5
          2. Apply quality=5: SM-2 progression from repetitions=1
             - repetitions becomes 2 (rep 1 -> increment)
             - interval_days becomes 3 (rep==1 -> 3 days... wait, rep is 1 before update_srs)
             Actually: after restore rep=1, update_srs with quality=5:
             rep==1 -> interval=3, then rep increments to 2
             ease_factor updates
          3. No double-counting of repetitions
        """
        _, word, session, _ = user_with_session

        # Verify word's current SRS state (post-original-rating)
        assert word.repetitions == 2
        assert word.interval_days == 7
        assert word.last_quality == 4

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 5, 'session_id': session.id}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'word' in data

        # Refresh from DB
        db.session.expire_all()
        word_after = Word.get_by_id(word.id)

        # After restoring snapshot (rep=1) and applying quality=5:
        # SM-2 with rep=1, quality=5: interval=3, rep becomes 2
        # (Not the fast-track because rep is 1 not 0)
        assert word_after.repetitions == 2
        assert word_after.interval_days == 3  # rep==1 -> 3 days
        assert word_after.last_quality == 5
        assert word_after.next_review_date is not None

    def test_rerate_no_double_counting_repetitions(self, client, db, auth_headers, user_with_session):
        """Rerate should not double-count repetitions.

        Original: snapshot rep=1, then original rating made rep=2.
        Rerate: restore rep=1, apply new quality -> rep=2 (not 3).
        """
        _, word, session, _ = user_with_session

        # Word currently at rep=2 (from original rating applied to snapshot rep=1)
        assert word.repetitions == 2

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 4, 'session_id': session.id}
        )
        assert resp.status_code == 200

        db.session.expire_all()
        word_after = Word.get_by_id(word.id)

        # Should be 2 (restored to 1, then incremented by quality>=3)
        assert word_after.repetitions == 2

    def test_rerate_with_failing_quality_resets(self, client, db, auth_headers, user_with_session):
        """Rerate with quality < 3 should reset repetitions to 0."""
        _, word, session, _ = user_with_session

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 1, 'session_id': session.id}
        )
        assert resp.status_code == 200

        db.session.expire_all()
        word_after = Word.get_by_id(word.id)

        # SM-2: quality < 3 resets repetitions to 0, interval to 1
        assert word_after.repetitions == 0
        assert word_after.interval_days == 1
        assert word_after.last_quality == 1

    def test_rerate_preserves_original_snapshot(self, client, db, auth_headers, user_with_session):
        """Multiple rerates should always restore from the ORIGINAL snapshot."""
        _, word, session, sw = user_with_session

        original_snapshot = sw.srs_snapshot.copy()

        # First rerate
        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 5, 'session_id': session.id}
        )
        assert resp.status_code == 200

        # Snapshot should still be the original
        db.session.expire_all()
        sw_after = SessionWord.get_by_session_word_id(word.id, session.id)
        assert sw_after.srs_snapshot['repetitions'] == original_snapshot['repetitions']
        assert sw_after.srs_snapshot['interval_days'] == original_snapshot['interval_days']

        # Second rerate - should still restore from the same original snapshot
        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 2, 'session_id': session.id}
        )
        assert resp.status_code == 200

        db.session.expire_all()
        word_final = Word.get_by_id(word.id)
        # quality=2 resets reps to 0 (regardless of what first rerate did)
        assert word_final.repetitions == 0
        assert word_final.interval_days == 1

    def test_rerate_returns_updated_word_data(self, client, auth_headers, user_with_session):
        """Should return the updated word data in the response."""
        _, word, session, _ = user_with_session

        resp = client.post(
            f'/api/words/{word.id}/rerate',
            headers=auth_headers,
            json={'quality': 4, 'session_id': session.id}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)

        assert 'word' in data
        word_data = data['word']
        assert word_data['id'] == word.id
        assert 'repetitions' in word_data
        assert 'interval_days' in word_data
        assert 'ease_factor' in word_data
