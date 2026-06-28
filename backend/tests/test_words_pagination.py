"""
Integration tests for the paginated GET /api/decks/{deck_id}/words endpoint and
POST /api/decks/{deck_id}/words bulk-create endpoint in deck_resources.py.

These tests exercise the full HTTP request/response cycle via Flask's test client
against a real in-memory SQLite database (provided by the `client` fixture from
conftest.py, which implicitly uses the `db` fixture).

Test categories:
  - Response format: envelope shape {"data": [...], "pagination": {...}}
  - Pagination params: page, per_page query string parameters
  - Search filtering: `search` query string parameter (ilike on word/reading/meaning)
  - Sorting: `sort_by` query string parameter
  - Empty vocabulary: deck with no words
  - POST validation: missing words key, missing required fields, valid array
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


def _create_deck(client, token, name='Test Deck', language='ZH'):
    """
    Create a deck via POST /api/decks and return the deck_id.
    """
    resp = client.post(
        '/api/decks',
        json={'name': name, 'language': language},
        headers=_auth_headers(token),
    )
    body = json.loads(resp.data)
    return body['id']


def _post_words(client, token, words, deck_id=None):
    """
    POST a list of word dicts to /api/decks/{deck_id}/words and return
    (response, deck_id).

    If deck_id is not provided, a new deck is created first.
    Each dict in `words` must contain 'word', 'reading', 'meaning'.
    """
    if deck_id is None:
        deck_id = _create_deck(client, token)

    resp = client.post(
        f'/api/decks/{deck_id}/words',
        json={'words': words},
        headers=_auth_headers(token),
        content_type='application/json',
    )
    return resp, deck_id


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}/words - response format
# ---------------------------------------------------------------------------

class TestGetWordsResponseFormat:

    def test_response_has_data_and_pagination_keys(self, client):
        """
        Arrange: authenticated user, empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  response body has top-level keys 'data' and 'pagination'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert 'data' in body
        assert 'pagination' in body

    def test_pagination_object_contains_required_keys(self, client):
        """
        Arrange: authenticated user, empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  pagination object contains page, per_page, total, total_pages,
                 has_next, has_prev.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        for key in ('page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev'):
            assert key in pagination, f"Missing pagination key: {key}"

    def test_data_is_a_list(self, client):
        """
        Arrange: authenticated user, empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  'data' value is a JSON array.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        assert isinstance(body['data'], list)


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}/words - pagination parameters
# ---------------------------------------------------------------------------

class TestGetWordsPaginationParams:

    def test_page_2_per_page_10_returns_remaining_items(self, client):
        """
        Arrange: 15 words posted to a deck, request page=2&per_page=10.
        Act:     GET /api/decks/{deck_id}/words?page=2&per_page=10.
        Assert:  5 items returned (15 - 10 from page 1 = 5 on page 2).
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'reading': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _, deck_id = _post_words(client, token, words)

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body['data']) == 5

    def test_page_2_per_page_10_pagination_page_is_2(self, client):
        """
        Arrange: 15 words in a deck, request page=2&per_page=10.
        Act:     GET /api/decks/{deck_id}/words?page=2&per_page=10.
        Assert:  pagination['page'] == 2.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'reading': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _, deck_id = _post_words(client, token, words)

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        pagination = json.loads(resp.data)['pagination']
        assert pagination['page'] == 2

    def test_page_1_per_page_10_returns_first_10_items(self, client):
        """
        Arrange: 15 words in a deck, request page=1&per_page=10.
        Act:     GET /api/decks/{deck_id}/words?page=1&per_page=10.
        Assert:  10 items returned.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'reading': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _, deck_id = _post_words(client, token, words)

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'page': 1, 'per_page': 10},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 10

    def test_pagination_total_reflects_all_words(self, client):
        """
        Arrange: 15 words posted to a deck.
        Act:     GET /api/decks/{deck_id}/words?page=2&per_page=10.
        Assert:  pagination['total'] == 15.
        """
        token = _register_and_get_token(client)
        words = [
            {'word': f'字{i}', 'reading': f'zi{i}', 'meaning': f'meaning{i}'}
            for i in range(15)
        ]
        _, deck_id = _post_words(client, token, words)

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'page': 2, 'per_page': 10},
        )

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total'] == 15


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}/words - search filter
# ---------------------------------------------------------------------------

class TestGetWordsSearchFilter:

    def test_search_by_chinese_word_returns_matching_word(self, client):
        """
        Arrange: two words posted to a deck -- '苹果' (apple) and '书' (book).
        Act:     GET /api/decks/{deck_id}/words?search=苹果.
        Assert:  only the '苹果' entry is returned.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'search': '苹果'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['word'] == '苹果'

    def test_search_by_reading_returns_matching_word(self, client):
        """
        Arrange: two words in a deck -- reading 'pingguo' and reading 'shu'.
        Act:     GET /api/decks/{deck_id}/words?search=pingguo.
        Assert:  only the 'pingguo' entry is returned.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'search': 'pingguo'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['reading'] == 'pingguo'

    def test_search_by_meaning_returns_matching_word(self, client):
        """
        Arrange: two words in a deck with meanings 'apple' and 'book'.
        Act:     GET /api/decks/{deck_id}/words?search=apple.
        Assert:  only the 'apple' entry is returned.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'search': 'apple'},
        )

        body = json.loads(resp.data)
        assert len(body['data']) == 1
        assert body['data'][0]['meaning'] == 'apple'

    def test_search_with_no_match_returns_empty_data(self, client):
        """
        Arrange: two words posted to a deck.
        Act:     GET /api/decks/{deck_id}/words?search=nomatch.
        Assert:  data is [] and pagination['total'] == 0.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'search': 'nomatch'},
        )

        body = json.loads(resp.data)
        assert body['data'] == []
        assert body['pagination']['total'] == 0


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}/words - sorting
# ---------------------------------------------------------------------------

class TestGetWordsSorting:

    def test_sort_by_word_returns_data_sorted_by_chinese_column(self, client):
        """
        Arrange: post three words with known Chinese characters in non-sorted order.
        Act:     GET /api/decks/{deck_id}/words?sort_by=word.
        Assert:  returned data['word'] values are in the same order as a sorted
                 list of those characters (database/Unicode sort order).
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '猫', 'reading': 'mao', 'meaning': 'cat'},
            {'word': '爱', 'reading': 'ai', 'meaning': 'love'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
            query_string={'sort_by': 'word'},
        )

        body = json.loads(resp.data)
        returned_words = [item['word'] for item in body['data']]
        assert returned_words == sorted(returned_words), (
            f"Words not sorted by 'word' column. Got: {returned_words}"
        )

    def test_default_sort_is_by_word(self, client):
        """
        Arrange: post three words with word values in non-sorted order.
        Act:     GET /api/decks/{deck_id}/words (no sort_by param -> defaults to 'word').
        Assert:  returned data is sorted by the 'word' field.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '猫', 'reading': 'mao', 'meaning': 'cat'},
            {'word': '爱', 'reading': 'ai', 'meaning': 'love'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
        )

        body = json.loads(resp.data)
        returned_words = [item['word'] for item in body['data']]
        assert returned_words == sorted(returned_words), (
            f"Words not sorted by word by default. Got: {returned_words}"
        )


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}/words - empty deck (no words)
# ---------------------------------------------------------------------------

class TestGetWordsEmptyVocabulary:

    def test_empty_deck_returns_empty_data_list(self, client):
        """
        Arrange: authenticated user with an empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  data == [].
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token, name='Empty Deck')
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        body = json.loads(resp.data)
        assert body['data'] == []

    def test_empty_deck_returns_total_zero(self, client):
        """
        Arrange: authenticated user with an empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  pagination['total'] == 0.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token, name='Empty Deck')
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total'] == 0

    def test_empty_deck_returns_total_pages_one(self, client):
        """
        Arrange: authenticated user with an empty deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  pagination['total_pages'] == 1.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token, name='Empty Deck')
        resp = client.get(f'/api/decks/{deck_id}/words', headers=_auth_headers(token))

        pagination = json.loads(resp.data)['pagination']
        assert pagination['total_pages'] == 1


# ---------------------------------------------------------------------------
# POST /api/decks/{deck_id}/words - request validation
# ---------------------------------------------------------------------------

class TestPostWordsValidation:

    def test_no_words_key_returns_400(self, client):
        """
        Arrange: body is a dict without a 'words' key.
        Act:     POST /api/decks/{deck_id}/words with {"word": "hi"}.
        Assert:  400 status and error message 'No words provided'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'word': 'hi'},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'No words provided'

    def test_empty_words_list_returns_400(self, client):
        """
        Arrange: body has 'words' key but it is an empty list.
        Act:     POST /api/decks/{deck_id}/words with {"words": []}.
        Assert:  400 status and error message 'Words must be a non-empty list'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': []},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Words must be a non-empty list'

    def test_missing_reading_field_returns_400_with_index(self, client):
        """
        Arrange: words array with one item missing the 'reading' key.
        Act:     POST /api/decks/{deck_id}/words with {"words": [{"word": "hi", "meaning": "hello"}]}.
        Assert:  400 status and details mention 'index 0' and 'reading'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': [{'word': 'hi', 'meaning': 'hello'}]},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Validation errors'
        assert any('index 0' in detail and 'reading' in detail for detail in body['details'])

    def test_missing_word_field_returns_400_with_index(self, client):
        """
        Arrange: words array with one item missing the 'word' key.
        Act:     POST /api/decks/{deck_id}/words with {"words": [{"reading": "hi", "meaning": "hello"}]}.
        Assert:  400 status and details mention 'index 0' and 'word'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': [{'reading': 'hi', 'meaning': 'hello'}]},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Validation errors'
        assert any('index 0' in detail and 'word' in detail for detail in body['details'])

    def test_missing_meaning_field_returns_400_with_index(self, client):
        """
        Arrange: words array with one item missing the 'meaning' key.
        Act:     POST /api/decks/{deck_id}/words with {"words": [{"word": "hi", "reading": "hi"}]}.
        Assert:  400 status and details mention 'index 0' and 'meaning'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': [{'word': 'hi', 'reading': 'hi'}]},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Validation errors'
        assert any('index 0' in detail and 'meaning' in detail for detail in body['details'])

    def test_second_row_missing_field_reports_index_1(self, client):
        """
        Arrange: words array where first item is valid and second is missing 'meaning'.
        Act:     POST /api/decks/{deck_id}/words.
        Assert:  400 status and details mention 'index 1'.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': [
                {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
                {'word': '书', 'reading': 'shu'},
            ]},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert any('index 1' in detail for detail in body['details'])

    def test_empty_field_value_returns_400(self, client):
        """
        Arrange: words array with item where 'reading' is an empty string (falsy).
        Act:     POST /api/decks/{deck_id}/words.
        Assert:  400 status because empty string is falsy and treated as missing.
        """
        token = _register_and_get_token(client)
        deck_id = _create_deck(client, token)
        resp = client.post(
            f'/api/decks/{deck_id}/words',
            json={'words': [{'word': '书', 'reading': '', 'meaning': 'book'}]},
            headers=_auth_headers(token),
            content_type='application/json',
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body['error'] == 'Validation errors'
        assert any('reading' in detail for detail in body['details'])


# ---------------------------------------------------------------------------
# POST /api/decks/{deck_id}/words - successful creation
# ---------------------------------------------------------------------------

class TestPostWordsSuccess:

    def test_valid_array_returns_201(self, client):
        """
        Arrange: valid words array in a deck.
        Act:     POST /api/decks/{deck_id}/words.
        Assert:  201 Created.
        """
        token = _register_and_get_token(client)
        resp, _ = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        assert resp.status_code == 201

    def test_valid_array_response_contains_created(self, client):
        """
        Arrange: valid words array in a deck.
        Act:     POST /api/decks/{deck_id}/words.
        Assert:  response body contains 'created' key with 2 items.
        """
        token = _register_and_get_token(client)
        resp, _ = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        body = json.loads(resp.data)
        assert 'created' in body
        assert len(body['created']) == 2

    def test_created_words_appear_in_subsequent_get(self, client):
        """
        Arrange: POST two valid words to a deck.
        Act:     GET /api/decks/{deck_id}/words.
        Assert:  GET returns the two words just created.
        """
        token = _register_and_get_token(client)
        _, deck_id = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
            {'word': '书', 'reading': 'shu', 'meaning': 'book'},
        ])

        resp = client.get(
            f'/api/decks/{deck_id}/words',
            headers=_auth_headers(token),
        )

        body = json.loads(resp.data)
        assert body['pagination']['total'] == 2

    def test_each_created_word_has_expected_fields(self, client):
        """
        Arrange: POST one valid word to a deck.
        Act:     POST /api/decks/{deck_id}/words.
        Assert:  created item has 'id', 'word', 'reading', 'meaning', 'srs_status'.
        """
        token = _register_and_get_token(client)
        resp, _ = _post_words(client, token, [
            {'word': '苹果', 'reading': 'pingguo', 'meaning': 'apple'},
        ])

        body = json.loads(resp.data)
        created = body['created'][0]
        for field in ('id', 'word', 'reading', 'meaning', 'srs_status'):
            assert field in created, f"Missing field in created word: {field}"

    def test_post_without_auth_returns_401(self, client):
        """
        Arrange: no auth token, create a deck endpoint requires auth too.
        Act:     POST /api/decks/1/words with valid data but no auth.
        Assert:  401 Unauthorized.
        """
        resp = client.post(
            '/api/decks/1/words',
            json={'words': [{'word': '书', 'reading': 'shu', 'meaning': 'book'}]},
            content_type='application/json',
        )

        assert resp.status_code == 401
