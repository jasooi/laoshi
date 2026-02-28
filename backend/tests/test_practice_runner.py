"""Unit tests for practice_runner.py functions."""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from ai_layer.practice_runner import (
    validate_feedback,
    validate_summary,
    hydrate_context,
    update_confidence,
    extract_feedback_from_result,
    get_session,
)
from ai_layer.context import UserSessionContext, WordContext


class TestValidateFeedback:
    """Tests for validate_feedback function."""

    def test_valid_feedback_returns_data(self):
        """Should return cleaned data for valid feedback."""
        data = {
            'grammarScore': 8,
            'usageScore': 9,
            'naturalnessScore': 7,
            'isCorrect': True,
            'feedback': 'Good job!'
        }
        result = validate_feedback(data)
        assert result == data

    def test_missing_required_key_returns_none(self):
        """Should return None if required key is missing."""
        data = {
            'grammarScore': 8,
            'usageScore': 9,
            'naturalnessScore': 7,
            # missing 'isCorrect'
        }
        result = validate_feedback(data)
        assert result is None

    def test_score_below_range_returns_none(self):
        """Should return None if score is below 1."""
        data = {
            'grammarScore': 0,
            'usageScore': 9,
            'naturalnessScore': 7,
            'isCorrect': False
        }
        result = validate_feedback(data)
        assert result is None

    def test_score_above_range_returns_none(self):
        """Should return None if score is above 10."""
        data = {
            'grammarScore': 11,
            'usageScore': 9,
            'naturalnessScore': 7,
            'isCorrect': False
        }
        result = validate_feedback(data)
        assert result is None

    def test_non_numeric_score_returns_none(self):
        """Should return None if score is not a number."""
        data = {
            'grammarScore': 'eight',
            'usageScore': 9,
            'naturalnessScore': 7,
            'isCorrect': False
        }
        result = validate_feedback(data)
        assert result is None


class TestValidateSummary:
    """Tests for validate_summary function."""

    def test_valid_summary_returns_data(self):
        """Should return cleaned data for valid summary."""
        data = {
            'summary_text': 'Great session!',
            'mem0_updates': ['Student struggles with tones']
        }
        result = validate_summary(data)
        assert result == data

    def test_missing_summary_text_returns_none(self):
        """Should return None if summary_text is missing."""
        data = {
            'mem0_updates': ['Student struggles with tones']
        }
        result = validate_summary(data)
        assert result is None

    def test_non_string_summary_text_returns_none(self):
        """Should return None if summary_text is not a string."""
        data = {
            'summary_text': 123,
            'mem0_updates': []
        }
        result = validate_summary(data)
        assert result is None

    def test_missing_mem0_updates_adds_empty_list(self):
        """Should add empty mem0_updates if missing."""
        data = {
            'summary_text': 'Great session!'
        }
        result = validate_summary(data)
        assert result['mem0_updates'] == []


class TestHydrateContext:
    """Tests for hydrate_context function."""

    def test_hydrates_basic_context(self):
        """Should hydrate context from DB objects."""
        # Mock user
        user = Mock()
        user.id = 1
        user.username = "testuser"
        # Mock profile with preferred_name
        user.profile = Mock()
        user.profile.preferred_name = "TestUser"

        # Mock session
        session = Mock()
        session.id = 10
        session.words_per_session = 3

        # Mock session words
        word1 = Mock()
        word1.id = 101
        word1.word = "你好"
        word1.pinyin = "ni hao"
        word1.meaning = "hello"

        sw1 = Mock()
        sw1.word_id = 101
        sw1.word = word1
        sw1.word_order = 0
        sw1.status = 0  # pending

        session_words = [sw1]

        ctx = hydrate_context(user, session, session_words)

        assert ctx.user_id == 1
        assert ctx.session_id == 10
        assert ctx.preferred_name == "TestUser"
        assert ctx.words_total == 3
        assert ctx.current_word.word_id == 101
        assert ctx.current_word.word == "你好"

    def test_counts_practiced_and_skipped_words(self):
        """Should correctly count practiced and skipped words."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.profile = Mock()
        user.profile.preferred_name = "TestUser"

        session = Mock()
        session.id = 10
        session.words_per_session = 3

        word1 = Mock()
        word1.id = 101
        word1.word = "A"
        word1.pinyin = "a"
        word1.meaning = "A"

        word2 = Mock()
        word2.id = 102
        word2.word = "B"
        word2.pinyin = "b"
        word2.meaning = "B"

        word3 = Mock()
        word3.id = 103
        word3.word = "C"
        word3.pinyin = "c"
        word3.meaning = "C"

        sw1 = Mock()
        sw1.word_id = 101
        sw1.word = word1
        sw1.word_order = 0
        sw1.status = 1  # completed

        sw2 = Mock()
        sw2.word_id = 102
        sw2.word = word2
        sw2.word_order = 1
        sw2.status = -1  # skipped

        sw3 = Mock()
        sw3.word_id = 103
        sw3.word = word3
        sw3.word_order = 2
        sw3.status = 0  # pending

        session_words = [sw1, sw2, sw3]

        ctx = hydrate_context(user, session, session_words)

        assert ctx.words_practiced == 1
        assert ctx.words_skipped == 1
        assert ctx.session_complete is False

    def test_session_complete_when_all_words_processed(self):
        """Should mark session_complete when all words are processed."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.profile = Mock()
        user.profile.preferred_name = "TestUser"

        session = Mock()
        session.id = 10
        session.words_per_session = 2

        word1 = Mock()
        word1.id = 101
        word1.word = "A"
        word1.pinyin = "a"
        word1.meaning = "A"

        word2 = Mock()
        word2.id = 102
        word2.word = "B"
        word2.pinyin = "b"
        word2.meaning = "B"

        sw1 = Mock()
        sw1.word_id = 101
        sw1.word = word1
        sw1.word_order = 0
        sw1.status = 1  # completed

        sw2 = Mock()
        sw2.word_id = 102
        sw2.word = word2
        sw2.word_order = 1
        sw2.status = -1  # skipped

        session_words = [sw1, sw2]

        ctx = hydrate_context(user, session, session_words)

        assert ctx.session_complete is True
        assert ctx.current_word is None


class TestUpdateConfidence:
    """Tests for update_confidence function."""

    def test_correct_answer_increases_confidence(self):
        """Should increase confidence for correct answer with good scores."""
        word = Mock()
        word.confidence_score = 0.5

        update_confidence(word, 10, 9, 8, True)

        # correctness_factor = 1.0, quality_multiplier = (0.4*10 + 0.4*9 + 0.2*8)/10 = 0.92
        # new_score = 0.5 + 1.0 * 0.92 * 0.1 = 0.592
        assert word.update_confidence_score.called
        args = word.update_confidence_score.call_args[0]
        assert args[0] > 0.5  # Should be increased

    def test_incorrect_answer_decreases_confidence(self):
        """Should decrease confidence for incorrect answer."""
        word = Mock()
        word.confidence_score = 0.5

        update_confidence(word, 5, 5, 5, False)

        # correctness_factor = -0.5, quality_multiplier = (0.4*5 + 0.4*5 + 0.2*5)/10 = 0.5
        # new_score = 0.5 + (-0.5) * 0.5 * 0.1 = 0.475
        assert word.update_confidence_score.called
        args = word.update_confidence_score.call_args[0]
        assert args[0] < 0.5  # Should be decreased

    def test_confidence_clamped_to_maximum(self):
        """Should not exceed 1.0."""
        word = Mock()
        word.confidence_score = 0.99

        update_confidence(word, 10, 10, 10, True)

        assert word.update_confidence_score.called
        args = word.update_confidence_score.call_args[0]
        assert args[0] == 1.0

    def test_confidence_clamped_to_minimum(self):
        """Should not go below 0.0."""
        word = Mock()
        word.confidence_score = 0.01

        update_confidence(word, 1, 1, 1, False)

        assert word.update_confidence_score.called
        args = word.update_confidence_score.call_args[0]
        assert args[0] >= 0.0  # Should be clamped to at least 0


class TestExtractFeedbackFromResult:
    """Tests for extract_feedback_from_result function."""

    def test_extracts_from_tool_call(self):
        """Should extract feedback JSON from tool call output."""
        from agents.items import ToolCallOutputItem
        
        # Mock the result structure with ToolCallOutputItem
        mock_output = {
            'grammarScore': 8,
            'usageScore': 9,
            'naturalnessScore': 7,
            'isCorrect': True
        }
        
        mock_item = Mock(spec=ToolCallOutputItem)
        mock_item.output = mock_output

        result = Mock()
        result.new_items = [mock_item]

        feedback = extract_feedback_from_result(result)

        assert feedback is not None
        assert feedback['grammarScore'] == 8
        assert feedback['isCorrect'] is True

    def test_returns_none_for_non_tool_call_items(self):
        """Should return None if no ToolCallOutputItem found."""
        result = Mock()
        result.new_items = [Mock()]  # Non-tool-call item

        feedback = extract_feedback_from_result(result)

        assert feedback is None

    def test_returns_none_for_invalid_json(self):
        """Should return None if JSON parsing fails."""
        from agents.items import ToolCallOutputItem
        
        mock_item = Mock(spec=ToolCallOutputItem)
        mock_item.output = "invalid json"

        result = Mock()
        result.new_items = [mock_item]

        feedback = extract_feedback_from_result(result)

        assert feedback is None


class TestGetSession:
    """Tests for get_session function."""

    def test_returns_none_without_redis_url(self, monkeypatch):
        """Should return None when REDIS_URI is not set."""
        monkeypatch.delenv("REDIS_URI", raising=False)
        session = get_session(123)
        assert session is None

    def test_returns_redis_session_with_url(self, monkeypatch):
        """Should return RedisSession when REDIS_URI is set."""
        from agents.extensions.memory import RedisSession
        monkeypatch.setenv("REDIS_URI", "redis://localhost:6379/0")
        session = get_session(123)
        assert isinstance(session, RedisSession)
