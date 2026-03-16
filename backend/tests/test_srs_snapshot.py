"""Tests for SRS snapshot saving in advance_word (T-7.27).

Tests that advance_word() saves the word's SRS state to
SessionWord.srs_snapshot before applying the quality rating.
"""
import pytest
import json
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock

from models import User, Word, UserSession, SessionWord, SessionWordAttempt


class TestSrsSnapshotSaving:
    """Tests that advance_word saves SRS snapshot before updating SRS."""

    @pytest.fixture
    def user_with_practice_session(self, db):
        """Create a user with a word, active session, and session word with an attempt."""
        user = User(username='snapshotuser', email='snapshot@example.com')
        user.password = 'hashed'
        user.add()

        word = Word(
            user_id=user.id,
            word='你好',
            pinyin='ni hao',
            meaning='hello',
            repetitions=1,
            interval_days=3,
            ease_factor=2.5,
            next_review_date=date(2026, 3, 16),
            last_quality=3,
            is_mastered=False,
        )
        word.add()

        session = UserSession(user_id=user.id)
        session.add()

        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=0,  # pending (active word)
        )
        sw.add()

        # Create an attempt so advance_word processes it (not skip)
        attempt = SessionWordAttempt(
            word_id=word.id,
            session_id=session.id,
            attempt_number=1,
            sentence='你好世界',
            grammar_score=8.0,
            usage_score=8.0,
            naturalness_score=7.0,
            is_correct=True,
        )
        attempt.add()

        # Add a second word so session doesn't complete when first word advances
        word2 = Word(
            user_id=user.id,
            word='谢谢',
            pinyin='xie xie',
            meaning='thank you',
            repetitions=0,
            interval_days=1,
            ease_factor=2.5,
        )
        word2.add()

        sw2 = SessionWord(
            word_id=word2.id,
            session_id=session.id,
            word_order=1,
            status=0,  # pending
        )
        sw2.add()

        return user, word, session, sw

    @patch('ai_layer.practice_runner.run_async')
    @patch('ai_layer.practice_runner.get_user_agent')
    def test_advance_word_saves_snapshot_with_quality(
        self, mock_get_agent, mock_run, db, user_with_practice_session
    ):
        """advance_word with quality should save snapshot before SRS update."""
        from ai_layer.practice_runner import advance_word

        user, word, session, sw = user_with_practice_session

        # Mock the AI agent call for next word introduction
        mock_agent = Mock()
        mock_get_agent.return_value = (mock_agent, Mock(), None, None)
        mock_result = Mock()
        mock_result.final_output = "Next word!"
        mock_run.return_value = mock_result

        # Record pre-rating SRS state
        pre_reps = word.repetitions
        pre_interval = word.interval_days
        pre_ease = float(word.ease_factor)
        pre_review = str(word.next_review_date) if word.next_review_date else None
        pre_mastered = word.is_mastered
        pre_quality = word.last_quality

        # Call advance_word with quality rating
        result, err = advance_word(session.id, user.id, quality=4)

        # Refresh from DB
        db.session.expire_all()
        sw_after = SessionWord.get_by_session_word_id(word.id, session.id)

        # Snapshot should have been saved
        assert sw_after.srs_snapshot is not None
        snapshot = sw_after.srs_snapshot

        # Verify snapshot matches pre-rating state
        assert snapshot['repetitions'] == pre_reps
        assert snapshot['interval_days'] == pre_interval
        assert snapshot['ease_factor'] == pre_ease
        assert snapshot['next_review_date'] == pre_review
        assert snapshot['is_mastered'] == pre_mastered
        assert snapshot['last_quality'] == pre_quality

    @patch('ai_layer.practice_runner.run_async')
    @patch('ai_layer.practice_runner.get_user_agent')
    def test_snapshot_has_all_required_keys(
        self, mock_get_agent, mock_run, db, user_with_practice_session
    ):
        """Snapshot should contain all required SRS state keys."""
        from ai_layer.practice_runner import advance_word

        user, word, session, sw = user_with_practice_session

        mock_agent = Mock()
        mock_get_agent.return_value = (mock_agent, Mock(), None, None)
        mock_result = Mock()
        mock_result.final_output = "Next word!"
        mock_run.return_value = mock_result

        advance_word(session.id, user.id, quality=3)

        db.session.expire_all()
        sw_after = SessionWord.get_by_session_word_id(word.id, session.id)

        required_keys = {
            'repetitions', 'interval_days', 'ease_factor',
            'next_review_date', 'is_mastered', 'last_quality'
        }
        assert set(sw_after.srs_snapshot.keys()) == required_keys

    @patch('ai_layer.practice_runner.run_async')
    @patch('ai_layer.practice_runner.get_user_agent')
    def test_advance_word_no_snapshot_without_quality(
        self, mock_get_agent, mock_run, db, user_with_practice_session
    ):
        """advance_word without quality should NOT save snapshot."""
        from ai_layer.practice_runner import advance_word

        user, word, session, sw = user_with_practice_session

        mock_agent = Mock()
        mock_get_agent.return_value = (mock_agent, Mock(), None, None)
        mock_result = Mock()
        mock_result.final_output = "Next word!"
        mock_run.return_value = mock_result

        # Call without quality
        advance_word(session.id, user.id, quality=None)

        db.session.expire_all()
        sw_after = SessionWord.get_by_session_word_id(word.id, session.id)

        # No snapshot should be saved
        assert sw_after.srs_snapshot is None

    @patch('ai_layer.practice_runner.run_async')
    @patch('ai_layer.practice_runner.get_user_agent')
    def test_srs_actually_updates_after_snapshot(
        self, mock_get_agent, mock_run, db, user_with_practice_session
    ):
        """SRS state should change AFTER snapshot is saved (snapshot != current state)."""
        from ai_layer.practice_runner import advance_word

        user, word, session, sw = user_with_practice_session

        mock_agent = Mock()
        mock_get_agent.return_value = (mock_agent, Mock(), None, None)
        mock_result = Mock()
        mock_result.final_output = "Next word!"
        mock_run.return_value = mock_result

        pre_reps = word.repetitions  # 1

        advance_word(session.id, user.id, quality=4)

        db.session.expire_all()
        sw_after = SessionWord.get_by_session_word_id(word.id, session.id)
        word_after = Word.get_by_id(word.id)

        # Snapshot should have old rep count
        assert sw_after.srs_snapshot['repetitions'] == pre_reps  # 1

        # Word should have updated rep count (SM-2: quality>=3 increments)
        assert word_after.repetitions == pre_reps + 1  # 2


class TestSessionWordSrsSnapshotColumn:
    """Tests that SessionWord model has the srs_snapshot column (T-7.25)."""

    def test_session_word_has_srs_snapshot_column(self, db):
        """SessionWord should have a nullable srs_snapshot JSON column."""
        user = User(username='coluser', email='col@example.com')
        user.password = 'hashed'
        user.add()

        session = UserSession(user_id=user.id)
        session.add()

        word = Word(user_id=user.id, word='测试', pinyin='ce shi', meaning='test')
        word.add()

        # Create session word without snapshot (should be null)
        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=0,
        )
        sw.add()

        assert sw.srs_snapshot is None

    def test_session_word_can_store_snapshot(self, db):
        """SessionWord should be able to store JSON snapshot data."""
        user = User(username='storeuser', email='store@example.com')
        user.password = 'hashed'
        user.add()

        session = UserSession(user_id=user.id)
        session.add()

        word = Word(user_id=user.id, word='存储', pinyin='cun chu', meaning='store')
        word.add()

        snapshot = {
            'repetitions': 2,
            'interval_days': 7,
            'ease_factor': 2.5,
            'next_review_date': '2026-03-20',
            'is_mastered': False,
            'last_quality': 4,
        }

        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=1,
            srs_snapshot=snapshot,
        )
        sw.add()

        # Retrieve and verify
        db.session.expire_all()
        sw_retrieved = SessionWord.get_by_session_word_id(word.id, session.id)
        assert sw_retrieved.srs_snapshot is not None
        assert sw_retrieved.srs_snapshot['repetitions'] == 2
        assert sw_retrieved.srs_snapshot['ease_factor'] == 2.5

    def test_format_data_includes_srs_snapshot(self, db):
        """format_data() should include srs_snapshot in return dict."""
        user = User(username='fmtuser', email='fmt@example.com')
        user.password = 'hashed'
        user.add()

        session = UserSession(user_id=user.id)
        session.add()

        word = Word(user_id=user.id, word='格式', pinyin='ge shi', meaning='format')
        word.add()

        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            word_order=0,
            status=0,
            srs_snapshot={'repetitions': 1, 'interval_days': 1, 'ease_factor': 2.5,
                          'next_review_date': None, 'is_mastered': False, 'last_quality': None},
        )
        sw.add()

        data = sw.format_data(viewer=user)
        assert data is not None
        assert 'srs_snapshot' in data
        assert data['srs_snapshot']['repetitions'] == 1
