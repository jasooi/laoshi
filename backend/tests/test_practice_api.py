"""Integration tests for practice session API endpoints."""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from models import User, Word, UserSession, SessionWord, SessionWordAttempt, Deck


class TestPracticeSessionAPI:
    """Tests for practice session API endpoints."""

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and return auth headers."""
        # Register a user
        resp = client.post('/api/users', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        # Login
        resp = client.post('/api/token', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        token = data['access_token']

        return {'Authorization': f'Bearer {token}'}

    @pytest.fixture
    def user_with_words(self, db, auth_headers, client):
        """Create a user with a deck and vocabulary words."""
        user = User.query.filter_by(username='testuser').first()

        deck = Deck(name='Test Deck', user_id=user.id, language='ZH')
        deck.add()

        words = [
            Word(user_id=user.id, deck_id=deck.id, word='你好', reading='ni hao', meaning='hello'),
            Word(user_id=user.id, deck_id=deck.id, word='谢谢', reading='xie xie', meaning='thank you'),
            Word(user_id=user.id, deck_id=deck.id, word='再见', reading='zai jian', meaning='goodbye'),
        ]
        for word in words:
            word.add()

        return user, words, deck

    def test_post_practice_session_requires_auth(self, client):
        """Should return 401 without authentication."""
        resp = client.post('/api/practice/sessions')
        assert resp.status_code == 401

    def test_post_practice_session_creates_session(self, client, auth_headers, user_with_words):
        """Should create a new practice session."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            # Mock the agent response
            mock_result = Mock()
            mock_result.final_output = "Welcome! Let's practice."
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)

            assert resp.status_code == 201
            data = json.loads(resp.data)
            assert 'session' in data
            assert 'current_word' in data
            assert 'greeting_message' in data
            assert data['greeting_message'] == "Welcome! Let's practice."
            assert data['words_total'] > 0

    def test_post_practice_session_no_eligible_words(self, client, auth_headers, db):
        """Should return 400 when no eligible words exist."""
        # Create user without words but with an empty deck
        resp = client.post('/api/users', json={
            'username': 'nowordsuser',
            'email': 'nowords@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        resp = client.post('/api/token', json={
            'username': 'nowordsuser',
            'password': 'TestPass123'
        })
        data = json.loads(resp.data)
        token = data['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # Create an empty deck
        user = User.query.filter_by(username='nowordsuser').first()
        empty_deck = Deck(name='Empty Deck', user_id=user.id, language='ZH')
        empty_deck.add()

        resp = client.post('/api/practice/sessions', json={'deck_id': empty_deck.id}, headers=headers)
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'no words' in data['error'].lower() or 'no eligible' in data['error'].lower()

    def test_post_practice_session_with_word_count(self, client, auth_headers, user_with_words):
        """Should respect words_count parameter."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id, 'words_count': 2}, headers=auth_headers)

            assert resp.status_code == 201
            data = json.loads(resp.data)
            assert data['words_total'] == 2

    def test_post_message_to_session(self, client, auth_headers, user_with_words):
        """Should process message and return response."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            # Create session
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_result.raw_responses = []
            mock_result.new_items = []
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)
            data = json.loads(resp.data)
            session_id = data['session']['id']

            # Send message
            mock_result.final_output = "Good try!"
            resp = client.post(
                f'/api/practice/sessions/{session_id}/messages',
                headers=auth_headers,
                json={'message': '你好世界'}
            )

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'laoshi_response' in data
            assert data['laoshi_response'] == "Good try!"

    def test_post_message_missing_body(self, client, auth_headers, user_with_words):
        """Should return 400 when message is missing."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)
            data = json.loads(resp.data)
            session_id = data['session']['id']

            resp = client.post(
                f'/api/practice/sessions/{session_id}/messages',
                headers=auth_headers,
                json={}
            )
            assert resp.status_code == 400

    def test_post_next_word(self, client, auth_headers, user_with_words):
        """Should advance to next word."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_result.raw_responses = []
            mock_result.new_items = []
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)
            data = json.loads(resp.data)
            session_id = data['session']['id']

            # Send a message first to create an attempt
            resp = client.post(
                f'/api/practice/sessions/{session_id}/messages',
                headers=auth_headers,
                json={'message': '你好世界'}
            )

            # Advance to next word
            mock_result.final_output = "Next word!"
            resp = client.post(f'/api/practice/sessions/{session_id}/next-word', headers=auth_headers)

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'laoshi_response' in data

    def test_get_session_summary(self, client, auth_headers, user_with_words):
        """Should return session summary."""
        user, words, deck = user_with_words
        with patch('ai_layer.practice_runner.run_async') as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_result.raw_responses = []
            mock_result.new_items = []
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)
            data = json.loads(resp.data)
            session_id = data['session']['id']

            # Complete all words to finish session
            for _ in range(3):
                client.post(
                    f'/api/practice/sessions/{session_id}/messages',
                    headers=auth_headers,
                    json={'message': 'Test sentence'}
                )
                client.post(f'/api/practice/sessions/{session_id}/next-word', headers=auth_headers)

            # Get summary
            resp = client.get(f'/api/practice/sessions/{session_id}/summary', headers=auth_headers)
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'word_results' in data
            assert 'words_practiced' in data
            assert 'words_skipped' in data


class TestPracticeSessionErrors:
    """Tests for error handling in practice session API."""

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and return auth headers."""
        resp = client.post('/api/users', json={
            'username': 'erroruser',
            'email': 'error@example.com',
            'password': 'TestPass123'
        })
        assert resp.status_code == 201

        resp = client.post('/api/token', json={
            'username': 'erroruser',
            'password': 'TestPass123'
        })
        data = json.loads(resp.data)
        token = data['access_token']
        return {'Authorization': f'Bearer {token}'}

    def test_message_to_completed_session(self, client, auth_headers, db):
        """Should return 400 when messaging a completed session."""
        # Create user with words
        user = User.query.filter_by(username='erroruser').first()
        deck = Deck(name='Error Test Deck', user_id=user.id, language='ZH')
        deck.add()
        word = Word(user_id=user.id, deck_id=deck.id, word='测试', reading='ce shi', meaning='test')
        word.add()

        with patch('ai_layer.practice_runner.run_async') as mock_run:
            mock_result = Mock()
            mock_result.final_output = "Welcome!"
            mock_result.raw_responses = []
            mock_result.new_items = []
            mock_run.return_value = mock_result

            resp = client.post('/api/practice/sessions', json={'deck_id': deck.id}, headers=auth_headers)
            data = json.loads(resp.data)
            session_id = data['session']['id']
        
            # Complete the session
            client.post(
                f'/api/practice/sessions/{session_id}/messages',
                headers=auth_headers,
                json={'message': 'Test'}
            )
            client.post(f'/api/practice/sessions/{session_id}/next-word', headers=auth_headers)
        
            # Try to send message to completed session
            resp = client.post(
                f'/api/practice/sessions/{session_id}/messages',
                headers=auth_headers,
                json={'message': 'Another message'}
            )
            assert resp.status_code == 400
