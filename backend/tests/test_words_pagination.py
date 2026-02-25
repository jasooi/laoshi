"""
Integration tests for the paginated GET /api/words endpoint and POST /api/words
bulk-create endpoint in resources.py (WordListResource).

These tests exercise the full HTTP request/response cycle via Flask's test client
against a real in-memory SQLite database (provided by the `client` fixture from
conftest.py, which implicitly uses the `db` fixture).

Test categories:
  - Response format: envelope shape {"data": [...], "pagination": {...}}
  - Pagination params: page, per_page query string parameters
  - Search filtering: `search` query string parameter (ilike on word/pinyin/meaning)
  - Sorting: `sort_by` query string parameter
  - Empty vocabulary: user with no words
  - POST validation: non-array body, missing required fields, valid array
"""

import sys
import os

# Ensure the backend package root is on the path so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import pytest


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _register_and_get_token(client):
    """
    Register a fresh test user via POST /api/users, log in via POST /api/token,
    and return the access token string.
    """
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123',
    })
    resp = client.post('/api/token', json={
        'username': 'testuser',
        'password': 'TestPass123',
    })
    return json.loads(resp.data)['access_token']


def _auth_headers(token):
    """Return an Authorization header dict for bearer-token requests."""
    return {'Authorization': f'Bearer {token}'}


def _post_words(client, token, words):
    """
    POST a list of word dicts to /api/words and return the response.

    Each dict in `words` must contain 'word', 'pinyin', 'meaning'.
    Optional: 'source_name'.
    """
    return client.post(
        '/api/words',
        json=words,
        headers=_auth_headers(token),
        content_type='application/json',
    )


# ---------------------------------------------------------------------------
# GET /api/words – response format
# ---------------------------------------------------------------------------

class TestGetWordsResponseFormat:

    def test_response_has_data_and_pagination_keys(self, client):
        """
        Arrange: authenticated user, no words.
        Act:     GET /api/words.
        Assert:  response body has top-level keys 'data' and 'pagination'.
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert 'data' in body
        assert 'pagination' in body

    def test_pagination_object_contains_required_keys(self, client):
        """
        Arrange: authenticated user, no words.
        Act:     GET /api/words.
        Assert:  pagination object contains page, per_page, total, total_pages,
                 has_next, has_prev.
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        for key in ('page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev'):
            assert key in pagination, f"Missing pagination key: {key}"

    def test_data_is_a_list(self, client):
        """
        Arrange: authenticated user, no words.
        Act:     GET /api/words.
        Assert:  'data' value is a JSON array.
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        assert isinstance(body['data'], list)


# ---------------------------------------------------------------------------
# GET /api/words – pagination parameters
# ---------------------------------------------------------------------------

class TestGetWordsPaginationParams:

    def test_page_2_per_page_10_returns_remaining_items(self, client):
        """
        Arrange: 15 words posted, request page=2&per_page=10.
        Act:     GET /api/words?page=2&per_page=10.
        Assert:  5 items returned (15 - 10 from page 1 = 5 on page 2).
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'pinyin': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _post_words(client, token, words)

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body['data']) == 5

    def test_page_2_per_page_10_pagination_page_is_2(self, client):
        """
        Arrange: 15 words, request page=2&per_page=10.
        Act:     GET /api/words?page=2&per_page=10.
        Assert:  pagination['page'] == 2.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'pinyin': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _post_words(client, token, words)

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        pagination = json.loads(resp.data)['pagination']
        assert pagination['page'] == 2

    def test_page_1_per_page_10_returns_first_10_items(self, client):
        """
        Arrange: 15 words, request page=1&per_page=10.
        Act:     GET /api/words?page=1&per_page=10.
        Assert:  10 items returned.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'pinyin': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _post_words(client, token, words)

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'page': 1, 'per_page': 10},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 10

    def test_pagination_total_reflects_all_words(self, client):
        """
        Arrange: 15 words posted.
        Act:     GET /api/words?page=2&per_page=10.
        Assert:  pagination['total'] == 15.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'pinyin': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _post_words(client, token, words)

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total'] == 15


# ---------------------------------------------------------------------------
# GET /api/words – search filter
# ---------------------------------------------------------------------------

class TestGetWordsSearchFilter:

    def test_search_by_chinese_word_returns_matching_word(self, client):
        """
        Arrange: two words posted — '苹果' (apple) and '书' (book).
        Act:     GET /api/words?search=苹果.
        Assert:  only the '苹果' entry is returned.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'search': '苹果'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['word'] == '苹果'

    def test_search_by_pinyin_returns_matching_word(self, client):
        """
        Arrange: two words — pinyin 'pingguo' and pinyin 'shu'.
        Act:     GET /api/words?search=pingguo.
        Assert:  only the 'pingguo' entry is returned.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'search': 'pingguo'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['pinyin'] == 'pingguo'

    def test_search_by_meaning_returns_matching_word(self, client):
        """
        Arrange: two words with meanings 'apple' and 'book'.
        Act:     GET /api/words?search=apple.
        Assert:  only the 'apple' entry is returned.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'search': 'apple'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['meaning'] == 'apple'

    def test_search_with_no_match_returns_empty_data(self, client):
        """
        Arrange: two words posted.
        Act:     GET /api/words?search=nomatch.
        Assert:  data is [] and pagination['total'] == 0.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'search': 'nomatch'},
        )

        body = json.loads(resp.data)
        assert body['data'] == []
        assert body['pagination']['total'] == 0


# ---------------------------------------------------------------------------
# GET /api/words – sorting
# ---------------------------------------------------------------------------

class TestGetWordsSorting:

    def test_sort_by_word_returns_data_sorted_by_chinese_column(self, client):
        """
        Arrange: post three words with known Chinese characters in non-sorted order.
        Act:     GET /api/words?sort_by=word.
        Assert:  returned data['word'] values are in the same order as a sorted
                 list of those characters (database/Unicode sort order).
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '猫', 'pinyin': 'mao', 'meaning': 'cat'},
            {'word': '爱', 'pinyin': 'ai', 'meaning': 'love'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            '/api/words',
            headers=_auth_headers(token),
            query_string={'sort_by': 'word'},
        )

        body = json.loads(resp.data)
        returned_words = [item['word'] for item in body['data']]
        assert returned_words == sorted(returned_words), (
            f"Words not sorted by 'word' column. Got: {returned_words}"
        )

    def test_default_sort_is_by_pinyin(self, client):
        """
        Arrange: post three words with pinyin in non-sorted order.
        Act:     GET /api/words (no sort_by param → defaults to 'pinyin').
        Assert:  returned data is sorted by the 'pinyin' field.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '猫', 'pinyin': 'mao', 'meaning': 'cat'},
            {'word': '爱', 'pinyin': 'ai', 'meaning': 'love'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get('/api/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        returned_pinyins = [item['pinyin'] for item in body['data']]
        assert returned_pinyins == sorted(returned_pinyins), (
            f"Words not sorted by pinyin by default. Got: {returned_pinyins}"
        )


# ---------------------------------------------------------------------------
# GET /api/words – empty vocabulary list
# ---------------------------------------------------------------------------

class TestGetWordsEmptyVocabulary:

    def test_user_with_no_words_returns_empty_data_list(self, client):
        """
        Arrange: authenticated user with no words.
        Act:     GET /api/words.
        Assert:  data == [].
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        assert body['data'] == []

    def test_user_with_no_words_returns_total_zero(self, client):
        """
        Arrange: authenticated user with no words.
        Act:     GET /api/words.
        Assert:  pagination['total'] == 0.
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total'] == 0

    def test_user_with_no_words_returns_total_pages_one(self, client):
        """
        Arrange: authenticated user with no words.
        Act:     GET /api/words.
        Assert:  pagination['total_pages'] == 1.
        """
        token = _register_and_get_token(client)
        resp = client.get('/api/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total_pages'] == 1


# ---------------------------------------------------------------------------
# POST /api/words – request validation
# ---------------------------------------------------------------------------

class TestPostWordsValidation:

    def test_non_array_body_returns_400(self, client):
        """
        Arrange: body is a dict (not an array).
        Act:     POST /api/words with {"word": "hi"}.
        Assert:  400 status and error message 'Expected a JSON array of words'.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json={'word': 'hi'},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Expected a JSON array of words'

    def test_missing_pinyin_field_returns_400_with_field_name(self, client):
        """
        Arrange: array with one item missing the 'pinyin' key.
        Act:     POST /api/words with [{"word": "hi", "meaning": "hello"}].
        Assert:  400 status and error mentions 'pinyin' and 'Row 1'.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json=[{'word': 'hi', 'meaning': 'hello'}],
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert 'Row 1' in body['error']
        assert 'pinyin' in body['error']

    def test_missing_word_field_returns_400_with_field_name(self, client):
        """
        Arrange: array with one item missing the 'word' key.
        Act:     POST /api/words with [{"pinyin": "hi", "meaning": "hello"}].
        Assert:  400 status and error mentions 'word' and 'Row 1'.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json=[{'pinyin': 'hi', 'meaning': 'hello'}],
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert 'Row 1' in body['error']
        assert 'word' in body['error']

    def test_missing_meaning_field_returns_400_with_field_name(self, client):
        """
        Arrange: array with one item missing the 'meaning' key.
        Act:     POST /api/words with [{"word": "hi", "pinyin": "hi"}].
        Assert:  400 status and error mentions 'meaning' and 'Row 1'.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json=[{'word': 'hi', 'pinyin': 'hi'}],
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert 'Row 1' in body['error']
        assert 'meaning' in body['error']

    def test_second_row_missing_field_reports_row_2(self, client):
        """
        Arrange: array where first row is valid and second row is missing 'meaning'.
        Act:     POST /api/words.
        Assert:  400 status and error mentions 'Row 2'.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json=[
                {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
                {'word': '书', 'pinyin': 'shu'},
            ],
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert 'Row 2' in body['error']

    def test_empty_field_value_returns_400(self, client):
        """
        Arrange: array with item where 'pinyin' is an empty string (falsy).
        Act:     POST /api/words.
        Assert:  400 status because empty string is falsy and treated as missing.
        """
        token = _register_and_get_token(client)
        resp = client.post(
            '/api/words',
            json=[{'word': '书', 'pinyin': '', 'meaning': 'book'}],
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert 'pinyin' in body['error']


# ---------------------------------------------------------------------------
# POST /api/words – successful creation
# ---------------------------------------------------------------------------

class TestPostWordsSuccess:

    def test_valid_array_returns_201(self, client):
        """
        Arrange: valid array of two word objects.
        Act:     POST /api/words.
        Assert:  201 Created.
        """
        token = _register_and_get_token(client)
        resp = _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        assert resp.status_code == 201

    def test_valid_array_response_contains_created_data(self, client):
        """
        Arrange: valid array of two word objects.
        Act:     POST /api/words.
        Assert:  response body contains 'created_data' key with 2 items.
        """
        token = _register_and_get_token(client)
        resp = _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        body = json.loads(resp.data)
        assert 'created_data' in body
        assert len(body['created_data']) == 2

    def test_created_words_appear_in_subsequent_get(self, client):
        """
        Arrange: POST two valid words.
        Act:     GET /api/words.
        Assert:  GET returns the two words just created.
        """
        token = _register_and_get_token(client)
        _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'pinyin': 'shu', 'meaning': 'book'},
        ])

        resp = client.get('/api/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        assert body['pagination']['total'] == 2

    def test_each_created_word_has_expected_fields(self, client):
        """
        Arrange: POST one valid word.
        Act:     POST /api/words.
        Assert:  created_data item has 'id', 'word', 'pinyin', 'meaning',
                 'confidence_score', 'status'.
        """
        token = _register_and_get_token(client)
        resp = _post_words(client, token, [
            {'word': '苹果', 'pinyin': 'pingguo', 'meaning': 'apple'},
        ])

        body = json.loads(resp.data)
        created = body['created_data'][0]
        for field in ('id', 'word', 'pinyin', 'meaning', 'confidence_score', 'status'):
            assert field in created, f"Missing field in created word: {field}"

    def test_post_without_auth_returns_401(self, client):
        """
        Arrange: no auth token.
        Act:     POST /api/words with valid data.
        Assert:  401 Unauthorized.
        """
        resp = client.post(
            '/api/words',
            json=[{'word': '书', 'pinyin': 'shu', 'meaning': 'book'}],
            content_type='application/json',
        )

        assert resp.status_code == 401
