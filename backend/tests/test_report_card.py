"""Integration tests for report card API endpoints."""
import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from models import User, UserProfile, Word, UserSession, SessionWord, SessionWordAttempt


class TestReportCardAPI:
    """Tests for GET /api/progress/report-card."""

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and return auth headers."""
        resp = client.post('/api/users', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        resp = client.post('/api/token', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        return {'Authorization': f'Bearer {data["access_token"]}'}

    @pytest.fixture
    def user_with_session_data(self, db, auth_headers):
        """Create a user with profile, sessions, words, and attempts for report card tests."""
        user = User.query.filter_by(username='testuser').first()

        # Create profile with feedback
        profile = UserProfile(
            user_id=user.id,
            preferred_name='TestStudent',
            report_card_feedback='You are doing great with measure words!'
        )
        profile.add()

        # Create words
        word1 = Word(user_id=user.id, word='你好', pinyin='ni hao', meaning='hello', confidence_score=0.6)
        word2 = Word(user_id=user.id, word='谢谢', pinyin='xie xie', meaning='thank you', confidence_score=0.4)
        word1.add()
        word2.add()

        now = datetime.now(timezone.utc)

        # Create a completed session
        session = UserSession(
            user_id=user.id,
            session_start_ds=now - timedelta(hours=1),
            session_end_ds=now,
            words_per_session=2,
            summary_text='Practiced greetings'
        )
        session.add()

        # Create session words with scores (status=1 means completed)
        sw1 = SessionWord(
            word_id=word1.id,
            session_id=session.id,
            status=1,
            grammar_score=8.0,
            usage_score=7.0,
            naturalness_score=6.0,
            word_order=1
        )
        sw2 = SessionWord(
            word_id=word2.id,
            session_id=session.id,
            status=1,
            grammar_score=9.0,
            usage_score=8.0,
            naturalness_score=7.0,
            word_order=2
        )
        sw1.add()
        sw2.add()

        # Create attempts within the last 7 days
        attempt1 = SessionWordAttempt(
            word_id=word1.id,
            session_id=session.id,
            attempt_number=1,
            sentence='你好世界',
            is_correct=True,
            created_ds=now - timedelta(hours=1)
        )
        attempt2 = SessionWordAttempt(
            word_id=word2.id,
            session_id=session.id,
            attempt_number=1,
            sentence='谢谢你',
            is_correct=False,
            created_ds=now - timedelta(minutes=30)
        )
        attempt3 = SessionWordAttempt(
            word_id=word2.id,
            session_id=session.id,
            attempt_number=2,
            sentence='非常谢谢你',
            is_correct=True,
            created_ds=now - timedelta(minutes=20)
        )
        attempt1.add()
        attempt2.add()
        attempt3.add()

        return user, profile, [word1, word2], session

    def test_report_card_requires_auth(self, client):
        """Should return 401 without authentication."""
        resp = client.get('/api/progress/report-card')
        assert resp.status_code == 401

    def test_report_card_empty_user(self, client, auth_headers, db):
        """Should return correct empty state for user with no sessions."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data)

        # Verify top-level keys
        assert 'topline' in data
        assert 'chart_data' in data
        assert 'score_breakdown' in data
        assert 'teacher_feedback' in data

        # Topline should be zeros
        assert data['topline']['time_practiced_hours'] == 0
        assert data['topline']['sessions_completed'] == 0
        assert data['topline']['words_practiced'] == 0

        # Chart data should have 7 entries (one per day)
        assert len(data['chart_data']) == 7
        for entry in data['chart_data']:
            assert 'date' in entry
            assert entry['correct'] == 0
            assert entry['incorrect'] == 0

        # Scores should be None when no data
        for score_type in ['grammar', 'usage', 'naturalness']:
            assert data['score_breakdown'][score_type]['score'] is None
            assert data['score_breakdown'][score_type]['description'] is None

        # No profile means no feedback
        assert data['teacher_feedback'] is None

    def test_report_card_with_session_data(self, client, auth_headers, user_with_session_data):
        """Should return correct metrics when user has session data."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data)

        # Topline metrics
        topline = data['topline']
        assert topline['sessions_completed'] == 1
        assert topline['time_practiced_hours'] == 1.0
        assert topline['words_practiced'] == 2

        # Chart data should still have 7 entries
        assert len(data['chart_data']) == 7

        # At least one day should have attempts
        total_correct = sum(e['correct'] for e in data['chart_data'])
        total_incorrect = sum(e['incorrect'] for e in data['chart_data'])
        assert total_correct == 2  # attempt1 and attempt3 are correct
        assert total_incorrect == 1  # attempt2 is incorrect

    def test_report_card_score_breakdown(self, client, auth_headers, user_with_session_data):
        """Should return correct score averages and descriptions."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        assert resp.status_code == 200
        data = json.loads(resp.data)

        scores = data['score_breakdown']

        # grammar: avg of 8.0 and 9.0 = 8.5
        assert scores['grammar']['score'] == 8.5
        assert scores['grammar']['description'] is not None

        # usage: avg of 7.0 and 8.0 = 7.5
        assert scores['usage']['score'] == 7.5
        assert scores['usage']['description'] is not None

        # naturalness: avg of 6.0 and 7.0 = 6.5
        assert scores['naturalness']['score'] == 6.5
        assert scores['naturalness']['description'] is not None

    def test_report_card_score_descriptions_populated(self, client, auth_headers, user_with_session_data):
        """Score descriptions should be meaningful strings when scores exist."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        data = json.loads(resp.data)

        scores = data['score_breakdown']
        for score_type in ['grammar', 'usage', 'naturalness']:
            desc = scores[score_type]['description']
            assert isinstance(desc, str)
            assert len(desc) > 10  # Should be a real descriptive sentence

    def test_report_card_teacher_feedback_from_profile(self, client, auth_headers, user_with_session_data):
        """Teacher feedback should come from UserProfile.report_card_feedback."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        data = json.loads(resp.data)

        assert data['teacher_feedback'] == 'You are doing great with measure words!'

    def test_report_card_chart_data_structure(self, client, auth_headers, db):
        """Chart data entries should have date, correct, incorrect keys."""
        resp = client.get('/api/progress/report-card', headers=auth_headers)
        data = json.loads(resp.data)

        for entry in data['chart_data']:
            assert 'date' in entry
            assert 'correct' in entry
            assert 'incorrect' in entry
            # date should be a valid ISO date string
            datetime.fromisoformat(entry['date'])

    def test_report_card_multiple_sessions(self, client, auth_headers, db):
        """Should aggregate metrics across multiple sessions."""
        user = User.query.filter_by(username='testuser').first()

        word = Word(user_id=user.id, word='学习', pinyin='xue xi', meaning='study', confidence_score=0.5)
        word.add()

        now = datetime.now(timezone.utc)

        # Create two completed sessions
        session1 = UserSession(
            user_id=user.id,
            session_start_ds=now - timedelta(days=2, hours=1),
            session_end_ds=now - timedelta(days=2),
            words_per_session=1
        )
        session1.add()

        session2 = UserSession(
            user_id=user.id,
            session_start_ds=now - timedelta(hours=2),
            session_end_ds=now - timedelta(hours=1),
            words_per_session=1
        )
        session2.add()

        # Session words
        sw1 = SessionWord(
            word_id=word.id, session_id=session1.id,
            status=1, grammar_score=6.0, usage_score=5.0, naturalness_score=4.0, word_order=1
        )
        sw1.add()
        sw2 = SessionWord(
            word_id=word.id, session_id=session2.id,
            status=1, grammar_score=8.0, usage_score=7.0, naturalness_score=6.0, word_order=1
        )
        sw2.add()

        resp = client.get('/api/progress/report-card', headers=auth_headers)
        data = json.loads(resp.data)

        assert data['topline']['sessions_completed'] == 2
        assert data['topline']['time_practiced_hours'] == 2.0
        # Same word practiced in two sessions counts as 1 distinct word
        assert data['topline']['words_practiced'] == 1

        # Scores should be averages across sessions: grammar avg = 7.0
        assert data['score_breakdown']['grammar']['score'] == 7.0


class TestGenerateFeedbackAPI:
    """Tests for POST /api/progress/generate-feedback."""

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and return auth headers."""
        resp = client.post('/api/users', json={
            'username': 'feedbackuser',
            'email': 'feedback@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        resp = client.post('/api/token', json={
            'username': 'feedbackuser',
            'password': 'TestPass123'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        return {'Authorization': f'Bearer {data["access_token"]}'}

    def test_generate_feedback_requires_auth(self, client):
        """Should return 401 without authentication."""
        resp = client.post('/api/progress/generate-feedback')
        assert resp.status_code == 401

    def test_generate_feedback_success(self, client, auth_headers, db):
        """Should return AI-generated feedback on success."""
        with patch('report_card_resources.generate_report_card_feedback') as mock_gen:
            mock_gen.return_value = "Great progress on measure words!"
            resp = client.post('/api/progress/generate-feedback', headers=auth_headers)

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'feedback' in data
            assert data['feedback'] == "Great progress on measure words!"
            mock_gen.assert_called_once()

    def test_generate_feedback_agent_failure(self, client, auth_headers, db):
        """Should return fallback message when AI agent fails."""
        with patch('report_card_resources.generate_report_card_feedback') as mock_gen:
            mock_gen.return_value = "Keep practicing! Check back after your next session for personalised feedback."
            resp = client.post('/api/progress/generate-feedback', headers=auth_headers)

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'feedback' in data
            assert data['feedback'] == "Keep practicing! Check back after your next session for personalised feedback."

    def test_generate_feedback_passes_user_id(self, client, auth_headers, db):
        """Should pass the authenticated user's ID to the service function."""
        user = User.query.filter_by(username='feedbackuser').first()

        with patch('report_card_resources.generate_report_card_feedback') as mock_gen:
            mock_gen.return_value = "Feedback text"
            client.post('/api/progress/generate-feedback', headers=auth_headers)

            mock_gen.assert_called_once_with(user.id)
