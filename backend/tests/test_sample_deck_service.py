"""Tests for sample deck seeding service."""
import pytest
from unittest.mock import patch

from models import User, Deck, Word
from sample_deck_service import (
    seed_sample_deck_for_user,
    user_has_sample_deck,
    load_sample_words_from_csv,
    SAMPLE_DECK_NAME,
)


class TestLoadSampleWordsFromCsv:
    """Tests for CSV loading."""

    def test_loads_words_from_csv(self, db):
        words = load_sample_words_from_csv()
        assert len(words) == 129
        assert words[0]['word'] == '文档'
        assert words[0]['pinyin'] == 'Wéndàng'
        assert words[0]['meaning'] == 'documentation'

    def test_returns_empty_list_if_csv_missing(self, db):
        with patch('sample_deck_service.get_sample_csv_path', return_value='/nonexistent/path.csv'):
            words = load_sample_words_from_csv()
            assert words == []


class TestSeedSampleDeckForUser:
    """Tests for the main seeding function."""

    @pytest.fixture
    def user(self, db):
        user = User(username='testuser', email='test@example.com')
        user.password = 'hashed'
        user.add()
        return user

    def test_creates_deck_with_all_words(self, db, user):
        deck = seed_sample_deck_for_user(user.id)

        assert deck is not None
        assert deck.name == SAMPLE_DECK_NAME
        assert deck.user_id == user.id

        words = Word.query.filter_by(deck_id=deck.id).all()
        assert len(words) == 129

        # Verify SRS defaults
        for w in words:
            assert w.user_id == user.id
            assert w.repetitions == 0
            assert w.interval_days == 1
            assert w.ease_factor == 2.5
            assert w.next_review_date is None
            assert w.is_mastered is False

    def test_idempotent_does_not_create_duplicate(self, db, user):
        deck1 = seed_sample_deck_for_user(user.id)
        deck2 = seed_sample_deck_for_user(user.id)

        assert deck1 is not None
        assert deck2 is None

        decks = Deck.query.filter_by(user_id=user.id, name=SAMPLE_DECK_NAME).all()
        assert len(decks) == 1

    def test_returns_none_if_csv_missing(self, db, user):
        with patch('sample_deck_service.get_sample_csv_path', return_value='/nonexistent/path.csv'):
            result = seed_sample_deck_for_user(user.id)
            assert result is None

        # No deck should have been created
        decks = Deck.query.filter_by(user_id=user.id).all()
        assert len(decks) == 0


class TestUserHasSampleDeck:
    """Tests for the idempotency check."""

    @pytest.fixture
    def user(self, db):
        user = User(username='checkuser', email='check@example.com')
        user.password = 'hashed'
        user.add()
        return user

    def test_returns_false_for_new_user(self, db, user):
        assert user_has_sample_deck(user.id) is False

    def test_returns_true_after_seeding(self, db, user):
        seed_sample_deck_for_user(user.id)
        assert user_has_sample_deck(user.id) is True
