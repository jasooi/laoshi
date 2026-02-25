"""
Unit tests for the paginate_query utility function in utils.py.

These tests exercise the function directly against a real (in-memory) database
query to validate all pagination logic: clamping, page calculation, metadata
flags, and empty-result handling.

Test categories:
  - Happy path: normal multi-page result sets
  - Edge cases: last page, empty query, boundary page/per_page values
  - Clamping: per_page > max_per_page, page < 1, per_page < 1, page > total_pages
"""

import sys
import os

# Ensure the backend package root is on the path so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils import paginate_query


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _create_test_user(db):
    """Insert a single test user and return the committed User object."""
    from models import User
    from utils import hash_password

    user = User(
        username='testuser',
        email='test@example.com',
        password=hash_password('TestPass123'),
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_words(db, user, count):
    """Insert `count` Word rows owned by `user` and return the list."""
    from models import Word

    words = []
    for i in range(count):
        w = Word(
            word=f'字{i}',
            pinyin=f'zi{i}',
            meaning=f'meaning{i}',
            user_id=user.id,
        )
        words.append(w)
    db.session.add_all(words)
    db.session.commit()
    return words


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

class TestPaginateQueryHappyPath:

    def test_basic_pagination_returns_correct_item_count(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  10 items returned.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            items, pagination = paginate_query(query, page=1, per_page=10)

            assert len(items) == 10

    def test_basic_pagination_total_is_correct(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  pagination['total'] == 25.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['total'] == 25

    def test_basic_pagination_total_pages_is_correct(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  pagination['total_pages'] == 3.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['total_pages'] == 3

    def test_basic_pagination_has_next_true_on_first_page(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  has_next=True.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['has_next'] is True

    def test_basic_pagination_has_prev_false_on_first_page(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  has_prev=False.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['has_prev'] is False

    def test_basic_pagination_page_number_is_correct(self, db, app):
        """
        Arrange: 25 words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  pagination['page'] == 1.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['page'] == 1


# ---------------------------------------------------------------------------
# Last page tests
# ---------------------------------------------------------------------------

class TestPaginateQueryLastPage:

    def test_last_page_returns_remaining_items(self, db, app):
        """
        Arrange: 25 words, 3 pages of 10 → last page has 5.
        Act:     paginate page=3, per_page=10.
        Assert:  5 items returned.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            items, _ = paginate_query(query, page=3, per_page=10)

            assert len(items) == 5

    def test_last_page_has_next_false(self, db, app):
        """
        Arrange: 25 words.
        Act:     paginate page=3, per_page=10.
        Assert:  has_next=False.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=3, per_page=10)

            assert pagination['has_next'] is False

    def test_last_page_has_prev_true(self, db, app):
        """
        Arrange: 25 words.
        Act:     paginate page=3, per_page=10.
        Assert:  has_prev=True.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 25)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=3, per_page=10)

            assert pagination['has_prev'] is True


# ---------------------------------------------------------------------------
# Empty query tests
# ---------------------------------------------------------------------------

class TestPaginateQueryEmptyResult:

    def test_empty_query_returns_empty_list(self, db, app):
        """
        Arrange: no words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  items == [].
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)

            query = Word.query.filter_by(user_id=user.id)
            items, _ = paginate_query(query, page=1, per_page=10)

            assert items == []

    def test_empty_query_total_is_zero(self, db, app):
        """
        Arrange: no words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  pagination['total'] == 0.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['total'] == 0

    def test_empty_query_total_pages_is_one(self, db, app):
        """
        Arrange: no words in db.
        Act:     paginate page=1, per_page=10.
        Assert:  pagination['total_pages'] == 1 (floor of empty set is 1, not 0).
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=10)

            assert pagination['total_pages'] == 1


# ---------------------------------------------------------------------------
# Clamping tests
# ---------------------------------------------------------------------------

class TestPaginateQueryClamping:

    def test_per_page_exceeds_max_is_clamped_to_max(self, db, app):
        """
        Arrange: any query; per_page=200, max_per_page=100.
        Act:     paginate.
        Assert:  pagination['per_page'] == 100.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(
                query, page=1, per_page=200, max_per_page=100
            )

            assert pagination['per_page'] == 100

    def test_page_beyond_total_pages_is_clamped_to_last_valid_page(self, db, app):
        """
        Arrange: 5 words, per_page=10 → total_pages=1; request page=10.
        Act:     paginate.
        Assert:  pagination['page'] == 1 (clamped to total_pages).
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 5)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=10, per_page=10)

            assert pagination['page'] == 1

    def test_page_beyond_total_pages_still_returns_items(self, db, app):
        """
        Arrange: 5 words, per_page=10; page=10 clamped to 1.
        Act:     paginate.
        Assert:  5 items are returned (all items from the clamped first page).
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 5)

            query = Word.query.filter_by(user_id=user.id)
            items, _ = paginate_query(query, page=10, per_page=10)

            assert len(items) == 5

    def test_page_zero_is_clamped_to_one(self, db, app):
        """
        Arrange: any query; page=0.
        Act:     paginate.
        Assert:  pagination['page'] == 1.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 5)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=0, per_page=10)

            assert pagination['page'] == 1

    def test_per_page_zero_is_clamped_to_one(self, db, app):
        """
        Arrange: any query; per_page=0.
        Act:     paginate.
        Assert:  pagination['per_page'] == 1.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 5)

            query = Word.query.filter_by(user_id=user.id)
            _, pagination = paginate_query(query, page=1, per_page=0)

            assert pagination['per_page'] == 1

    def test_per_page_one_returns_single_item_per_page(self, db, app):
        """
        Arrange: 5 words; per_page clamped to 1.
        Act:     paginate page=1, per_page=0 (clamped to 1).
        Assert:  exactly 1 item returned on page 1.
        """
        with app.app_context():
            from models import Word
            user = _create_test_user(db)
            _create_words(db, user, 5)

            query = Word.query.filter_by(user_id=user.id)
            items, _ = paginate_query(query, page=1, per_page=0)

            assert len(items) == 1
