"""
Unit tests for the report_card_service module.

Tests cover the four pure business-logic functions:
  - get_topline_metrics
  - get_daily_chart_data
  - get_rolling_scores
  - get_score_description

generate_report_card_feedback is intentionally excluded here because it
requires AI/agent mocking and is covered in integration tests instead.

Test categories per function:
  get_topline_metrics  -- empty state, completed sessions, incomplete sessions,
                          skipped words, session duration capping
  get_daily_chart_data -- empty state, attempts on various days, gap-filling,
                          length guarantee, user isolation
  get_rolling_scores   -- empty state, fewer than 5 sessions, more than 5
                          sessions, skipped-word exclusion, NULL-score exclusion,
                          rounding
  get_score_description -- each score type at every range boundary, None input,
                           fractional scores
"""

import sys
import os

# Ensure the backend package root is on the path so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timedelta, timezone

from models import User, UserProfile, UserSession, SessionWord, SessionWordAttempt, Word
from report_card_service import (
    get_topline_metrics,
    get_daily_chart_data,
    get_rolling_scores,
    get_score_description,
    MAX_SESSION_HOURS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(db, username='testuser', email='test@example.com'):
    """Insert a user and return the committed User object."""
    from utils import hash_password
    user = User(
        username=username,
        email=email,
        password=hash_password('TestPass123'),
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_word(db, user, word_text='hello', pinyin='ni hao', meaning='hello'):
    """Insert a single Word for *user* and return it."""
    word = Word(
        word=word_text,
        pinyin=pinyin,
        meaning=meaning,
        user_id=user.id,
    )
    db.session.add(word)
    db.session.commit()
    return word


def _create_session(db, user, start, end=None, summary_text=None):
    """Insert a UserSession and return it.  *end* can be None for incomplete sessions."""
    session = UserSession(
        user_id=user.id,
        session_start_ds=start,
        session_end_ds=end,
        summary_text=summary_text,
    )
    db.session.add(session)
    db.session.commit()
    return session


def _create_session_word(db, word, session, status=0,
                         grammar_score=None, usage_score=None,
                         naturalness_score=None, word_order=0):
    """Insert a SessionWord and return it."""
    sw = SessionWord(
        word_id=word.id,
        session_id=session.id,
        status=status,
        grammar_score=grammar_score,
        usage_score=usage_score,
        naturalness_score=naturalness_score,
        word_order=word_order,
    )
    db.session.add(sw)
    db.session.commit()
    return sw


def _create_attempt(db, word, session, attempt_number, is_correct,
                    created_ds=None, sentence='test sentence'):
    """Insert a SessionWordAttempt and return it."""
    attempt = SessionWordAttempt(
        word_id=word.id,
        session_id=session.id,
        attempt_number=attempt_number,
        sentence=sentence,
        is_correct=is_correct,
        created_ds=created_ds or datetime.now(timezone.utc),
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


# ---------------------------------------------------------------------------
# get_topline_metrics
# ---------------------------------------------------------------------------

class TestGetToplineMetrics:

    def test_no_sessions_returns_all_zeros(self, db, app):
        """With no sessions at all, every metric should be zero."""
        with app.app_context():
            user = _create_user(db)
            result = get_topline_metrics(user.id)

            assert result['time_practiced_hours'] == 0
            assert result['sessions_completed'] == 0
            assert result['words_practiced'] == 0

    def test_completed_sessions_time_and_count(self, db, app):
        """Two 30-minute completed sessions should yield 1.0 hour and count 2."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            _create_session(db, user,
                            start=now,
                            end=now + timedelta(minutes=30))
            _create_session(db, user,
                            start=now + timedelta(hours=2),
                            end=now + timedelta(hours=2, minutes=30))

            result = get_topline_metrics(user.id)

            assert result['time_practiced_hours'] == 1.0
            assert result['sessions_completed'] == 2

    def test_incomplete_sessions_excluded_from_time_and_count(self, db, app):
        """Sessions with session_end_ds=None must not count."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            # One completed, one incomplete
            _create_session(db, user, start=now, end=now + timedelta(minutes=45))
            _create_session(db, user, start=now + timedelta(hours=3), end=None)

            result = get_topline_metrics(user.id)

            assert result['time_practiced_hours'] == 0.8  # 45 min = 0.75, rounded to 1 decimal
            assert result['sessions_completed'] == 1

    def test_session_duration_capped_at_max_hours(self, db, app):
        """A session lasting 5 hours should be capped at MAX_SESSION_HOURS (2.0)."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            _create_session(db, user, start=now, end=now + timedelta(hours=5))

            result = get_topline_metrics(user.id)

            assert result['time_practiced_hours'] == MAX_SESSION_HOURS

    def test_multiple_sessions_with_cap(self, db, app):
        """Mix of short and long sessions: long ones are individually capped."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            # 1 hour session (uncapped)
            _create_session(db, user,
                            start=now,
                            end=now + timedelta(hours=1))
            # 10 hour session (capped to 2)
            _create_session(db, user,
                            start=now + timedelta(days=1),
                            end=now + timedelta(days=1, hours=10))

            result = get_topline_metrics(user.id)

            # 1 + 2 = 3.0
            assert result['time_practiced_hours'] == 3.0
            assert result['sessions_completed'] == 2

    def test_words_practiced_counts_distinct_completed_words(self, db, app):
        """Only distinct word_ids with status=1 should be counted."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')
            w3 = _create_word(db, user, 'w3', 'p3', 'm3')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            _create_session_word(db, w1, sess, status=1)  # completed
            _create_session_word(db, w2, sess, status=1)  # completed
            _create_session_word(db, w3, sess, status=0)  # pending -- excluded

            result = get_topline_metrics(user.id)

            assert result['words_practiced'] == 2

    def test_skipped_words_excluded(self, db, app):
        """Words with status=-1 (skipped) should not count as practiced."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            _create_session_word(db, w1, sess, status=1)   # completed
            _create_session_word(db, w2, sess, status=-1)  # skipped

            result = get_topline_metrics(user.id)

            assert result['words_practiced'] == 1

    def test_same_word_across_sessions_counted_once(self, db, app):
        """If the same word_id appears completed in two sessions, count it once."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')

            sess1 = _create_session(db, user, start=now, end=now + timedelta(hours=1))
            sess2 = _create_session(db, user,
                                    start=now + timedelta(days=1),
                                    end=now + timedelta(days=1, hours=1))

            _create_session_word(db, w1, sess1, status=1)
            _create_session_word(db, w1, sess2, status=1)

            result = get_topline_metrics(user.id)

            assert result['words_practiced'] == 1

    def test_time_rounding_to_one_decimal(self, db, app):
        """15-minute session = 0.25 hours, which is 0.2 or 0.3? Exact: 0.25 -> 0.2 (banker's) or 0.3.
        Python round(0.25, 1) = 0.2 due to banker's rounding. Let's verify with 20 min = 0.333... -> 0.3."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            _create_session(db, user, start=now, end=now + timedelta(minutes=20))

            result = get_topline_metrics(user.id)

            # 20 min / 60 = 0.3333... -> round to 1 decimal = 0.3
            assert result['time_practiced_hours'] == 0.3


# ---------------------------------------------------------------------------
# get_daily_chart_data
# ---------------------------------------------------------------------------

class TestGetDailyChartData:

    def test_no_attempts_returns_seven_zero_entries(self, db, app):
        """With no attempts, should return 7 entries each with correct=0, incorrect=0."""
        with app.app_context():
            user = _create_user(db)
            result = get_daily_chart_data(user.id)

            assert len(result) == 7
            for entry in result:
                assert entry['correct'] == 0
                assert entry['incorrect'] == 0
                assert 'date' in entry

    def test_always_returns_exactly_seven_entries(self, db, app):
        """Even with data, the output list must have exactly 7 elements."""
        with app.app_context():
            user = _create_user(db)
            now = datetime.now(timezone.utc)

            w = _create_word(db, user, 'w1', 'p1', 'm1')
            sess = _create_session(db, user, start=now - timedelta(hours=2), end=now)
            _create_session_word(db, w, sess, status=1)
            _create_attempt(db, w, sess, 1, True, created_ds=now)

            result = get_daily_chart_data(user.id)
            assert len(result) == 7

    def test_correct_and_incorrect_counts(self, db, app):
        """Attempts today should show up in the last entry with correct counts."""
        with app.app_context():
            user = _create_user(db)
            today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

            w = _create_word(db, user, 'w1', 'p1', 'm1')
            sess = _create_session(db, user,
                                   start=today - timedelta(hours=2),
                                   end=today)
            _create_session_word(db, w, sess, status=1)

            # 3 correct, 2 incorrect today
            _create_attempt(db, w, sess, 1, True, created_ds=today)
            _create_attempt(db, w, sess, 2, False, created_ds=today)
            _create_attempt(db, w, sess, 3, True, created_ds=today)
            _create_attempt(db, w, sess, 4, True, created_ds=today)
            _create_attempt(db, w, sess, 5, False, created_ds=today)

            result = get_daily_chart_data(user.id)

            # Today is the last entry in the list
            today_entry = result[-1]
            assert today_entry['correct'] == 3
            assert today_entry['incorrect'] == 2

    def test_missing_days_filled_with_zeros(self, db, app):
        """Days without attempts should have correct=0, incorrect=0."""
        with app.app_context():
            user = _create_user(db)
            today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

            w = _create_word(db, user, 'w1', 'p1', 'm1')
            sess = _create_session(db, user,
                                   start=today - timedelta(hours=2),
                                   end=today)
            _create_session_word(db, w, sess, status=1)

            # Only add attempts for today
            _create_attempt(db, w, sess, 1, True, created_ds=today)

            result = get_daily_chart_data(user.id)

            # All entries except today should be zero
            for entry in result[:-1]:
                assert entry['correct'] == 0
                assert entry['incorrect'] == 0

    def test_attempts_on_multiple_days(self, db, app):
        """Attempts spread over several days should appear in their respective entries."""
        with app.app_context():
            user = _create_user(db)
            today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')
            sess = _create_session(db, user,
                                   start=today - timedelta(days=7),
                                   end=today)
            _create_session_word(db, w1, sess, status=1)
            _create_session_word(db, w2, sess, status=1)

            # Attempts 3 days ago
            three_days_ago = today - timedelta(days=3)
            _create_attempt(db, w1, sess, 1, True, created_ds=three_days_ago)
            _create_attempt(db, w1, sess, 2, False, created_ds=three_days_ago)

            # Attempts today
            _create_attempt(db, w2, sess, 1, True, created_ds=today)

            result = get_daily_chart_data(user.id)

            # Entry at index 3 (7 - 1 - 3 = 3) should be 3 days ago
            three_days_ago_entry = result[6 - 3]  # index = 6 - days_ago
            assert three_days_ago_entry['correct'] == 1
            assert three_days_ago_entry['incorrect'] == 1

            today_entry = result[-1]
            assert today_entry['correct'] == 1
            assert today_entry['incorrect'] == 0

    def test_only_includes_own_user_data(self, db, app):
        """User A's chart should not contain User B's attempts."""
        with app.app_context():
            user_a = _create_user(db, username='usera', email='a@example.com')
            user_b = _create_user(db, username='userb', email='b@example.com')
            today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

            # Words for each user
            wa = _create_word(db, user_a, 'wa', 'pa', 'ma')
            wb = _create_word(db, user_b, 'wb', 'pb', 'mb')

            # Sessions for each user
            sess_a = _create_session(db, user_a,
                                     start=today - timedelta(hours=2),
                                     end=today)
            sess_b = _create_session(db, user_b,
                                     start=today - timedelta(hours=2),
                                     end=today)

            _create_session_word(db, wa, sess_a, status=1)
            _create_session_word(db, wb, sess_b, status=1)

            # Attempts for user B only
            _create_attempt(db, wb, sess_b, 1, True, created_ds=today)
            _create_attempt(db, wb, sess_b, 2, True, created_ds=today)

            result_a = get_daily_chart_data(user_a.id)

            # User A should see all zeros
            for entry in result_a:
                assert entry['correct'] == 0
                assert entry['incorrect'] == 0

    def test_dates_are_iso_formatted_strings(self, db, app):
        """Each entry's 'date' field should be a valid ISO date string."""
        with app.app_context():
            user = _create_user(db)
            result = get_daily_chart_data(user.id)

            for entry in result:
                # Should parse without error
                parsed = datetime.fromisoformat(entry['date']).date()
                assert parsed is not None

    def test_dates_cover_last_seven_days(self, db, app):
        """The returned dates should span from 6 days ago to today."""
        with app.app_context():
            user = _create_user(db)
            result = get_daily_chart_data(user.id)

            today = datetime.now(timezone.utc).date()
            expected_dates = [(today - timedelta(days=6 - i)).isoformat() for i in range(7)]

            returned_dates = [entry['date'] for entry in result]
            assert returned_dates == expected_dates


# ---------------------------------------------------------------------------
# get_rolling_scores
# ---------------------------------------------------------------------------

class TestGetRollingScores:

    def test_no_sessions_returns_all_none(self, db, app):
        """Without any sessions, all three scores should be None."""
        with app.app_context():
            user = _create_user(db)
            result = get_rolling_scores(user.id)

            assert result['grammar'] is None
            assert result['usage'] is None
            assert result['naturalness'] is None

    def test_fewer_than_five_sessions_uses_all(self, db, app):
        """With 2 completed sessions, both should contribute to the average."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            sess1 = _create_session(db, user, start=now, end=now + timedelta(hours=1))
            sess2 = _create_session(db, user,
                                    start=now + timedelta(days=1),
                                    end=now + timedelta(days=1, hours=1))

            _create_session_word(db, w1, sess1, status=1,
                                 grammar_score=8.0, usage_score=6.0, naturalness_score=7.0)
            _create_session_word(db, w2, sess2, status=1,
                                 grammar_score=6.0, usage_score=8.0, naturalness_score=5.0)

            result = get_rolling_scores(user.id)

            # (8+6)/2=7, (6+8)/2=7, (7+5)/2=6
            assert result['grammar'] == 7.0
            assert result['usage'] == 7.0
            assert result['naturalness'] == 6.0

    def test_more_than_five_sessions_only_uses_last_five(self, db, app):
        """With 7 sessions, only the 5 most recent (by session_end_ds) matter."""
        with app.app_context():
            user = _create_user(db)
            base = datetime(2025, 1, 1, 12, 0, 0)

            words = []
            for i in range(7):
                w = _create_word(db, user, f'w{i}', f'p{i}', f'm{i}')
                words.append(w)

            sessions = []
            for i in range(7):
                s = _create_session(db, user,
                                    start=base + timedelta(days=i),
                                    end=base + timedelta(days=i, hours=1))
                sessions.append(s)

            # Older sessions (index 0, 1) get high scores that should be excluded
            for i in range(7):
                if i < 2:
                    grammar, usage, nat = 10.0, 10.0, 10.0
                else:
                    grammar, usage, nat = 4.0, 4.0, 4.0
                _create_session_word(db, words[i], sessions[i], status=1,
                                     grammar_score=grammar,
                                     usage_score=usage,
                                     naturalness_score=nat)

            result = get_rolling_scores(user.id)

            # Last 5 sessions (index 2-6) all have score 4.0
            assert result['grammar'] == 4.0
            assert result['usage'] == 4.0
            assert result['naturalness'] == 4.0

    def test_skipped_words_excluded(self, db, app):
        """Words with status != 1 should not contribute to score averages."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            # w1 completed with grammar=8, w2 skipped with grammar=2
            _create_session_word(db, w1, sess, status=1,
                                 grammar_score=8.0, usage_score=8.0, naturalness_score=8.0)
            _create_session_word(db, w2, sess, status=-1,
                                 grammar_score=2.0, usage_score=2.0, naturalness_score=2.0)

            result = get_rolling_scores(user.id)

            # Only w1 should count
            assert result['grammar'] == 8.0
            assert result['usage'] == 8.0
            assert result['naturalness'] == 8.0

    def test_null_scores_excluded(self, db, app):
        """Words with NULL grammar_score should not contribute to averages."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            _create_session_word(db, w1, sess, status=1,
                                 grammar_score=6.0, usage_score=6.0, naturalness_score=6.0)
            _create_session_word(db, w2, sess, status=1,
                                 grammar_score=None, usage_score=None, naturalness_score=None)

            result = get_rolling_scores(user.id)

            # Only w1 contributes
            assert result['grammar'] == 6.0
            assert result['usage'] == 6.0
            assert result['naturalness'] == 6.0

    def test_all_words_null_scores_returns_none(self, db, app):
        """If every completed word has NULL scores, result should be all None."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w = _create_word(db, user, 'w1', 'p1', 'm1')
            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            _create_session_word(db, w, sess, status=1,
                                 grammar_score=None, usage_score=None, naturalness_score=None)

            result = get_rolling_scores(user.id)

            assert result['grammar'] is None
            assert result['usage'] is None
            assert result['naturalness'] is None

    def test_scores_rounded_to_one_decimal(self, db, app):
        """Averages that produce long decimals should be rounded to 1 place."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')
            w3 = _create_word(db, user, 'w3', 'p3', 'm3')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            # Average of 7, 8, 9 = 8.0  (clean)
            # Average of 7, 8, 6 = 7.0  (clean)
            # Average of 7, 5, 6 = 6.0  (clean)
            # Let's use values that create non-round averages:
            # 7 + 8 + 9 = 24/3 = 8.0
            # Let's use 7, 8, 8 = 23/3 = 7.666... -> 7.7
            _create_session_word(db, w1, sess, status=1,
                                 grammar_score=7.0, usage_score=7.0, naturalness_score=7.0)
            _create_session_word(db, w2, sess, status=1,
                                 grammar_score=8.0, usage_score=8.0, naturalness_score=8.0)
            _create_session_word(db, w3, sess, status=1,
                                 grammar_score=8.0, usage_score=8.0, naturalness_score=8.0)

            result = get_rolling_scores(user.id)

            assert result['grammar'] == 7.7
            assert result['usage'] == 7.7
            assert result['naturalness'] == 7.7

    def test_incomplete_sessions_excluded(self, db, app):
        """Sessions without session_end_ds should not be in the rolling window."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            # Complete session with score 6
            sess1 = _create_session(db, user, start=now, end=now + timedelta(hours=1))
            _create_session_word(db, w1, sess1, status=1,
                                 grammar_score=6.0, usage_score=6.0, naturalness_score=6.0)

            # Incomplete session with score 10 (should be excluded)
            sess2 = _create_session(db, user,
                                    start=now + timedelta(days=1), end=None)
            _create_session_word(db, w2, sess2, status=1,
                                 grammar_score=10.0, usage_score=10.0, naturalness_score=10.0)

            result = get_rolling_scores(user.id)

            # Only sess1 counts
            assert result['grammar'] == 6.0
            assert result['usage'] == 6.0
            assert result['naturalness'] == 6.0

    def test_multiple_words_per_session_averaged(self, db, app):
        """Multiple completed words in one session should all contribute to the average."""
        with app.app_context():
            user = _create_user(db)
            now = datetime(2025, 1, 10, 12, 0, 0)

            w1 = _create_word(db, user, 'w1', 'p1', 'm1')
            w2 = _create_word(db, user, 'w2', 'p2', 'm2')

            sess = _create_session(db, user, start=now, end=now + timedelta(hours=1))

            _create_session_word(db, w1, sess, status=1,
                                 grammar_score=4.0, usage_score=6.0, naturalness_score=8.0)
            _create_session_word(db, w2, sess, status=1,
                                 grammar_score=8.0, usage_score=4.0, naturalness_score=6.0)

            result = get_rolling_scores(user.id)

            # avg grammar = (4+8)/2 = 6, usage = (6+4)/2 = 5, nat = (8+6)/2 = 7
            assert result['grammar'] == 6.0
            assert result['usage'] == 5.0
            assert result['naturalness'] == 7.0


# ---------------------------------------------------------------------------
# get_score_description
# ---------------------------------------------------------------------------

class TestGetScoreDescription:

    # -- None input --

    def test_none_score_returns_none_for_grammar(self, db, app):
        with app.app_context():
            assert get_score_description('grammar', None) is None

    def test_none_score_returns_none_for_usage(self, db, app):
        with app.app_context():
            assert get_score_description('usage', None) is None

    def test_none_score_returns_none_for_naturalness(self, db, app):
        with app.app_context():
            assert get_score_description('naturalness', None) is None

    # -- Grammar ranges --

    def test_grammar_score_1(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 1.0)
            assert 'significant work' in desc.lower()

    def test_grammar_score_3(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 3.0)
            assert 'significant work' in desc.lower()

    def test_grammar_score_4(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 4.0)
            assert 'developing' in desc.lower()

    def test_grammar_score_5(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 5.0)
            assert 'developing' in desc.lower()

    def test_grammar_score_6(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 6.0)
            assert 'solid' in desc.lower()

    def test_grammar_score_7(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 7.0)
            assert 'solid' in desc.lower()

    def test_grammar_score_8(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 8.0)
            assert 'strong' in desc.lower()

    def test_grammar_score_9(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 9.0)
            assert 'strong' in desc.lower()

    def test_grammar_score_10(self, db, app):
        with app.app_context():
            desc = get_score_description('grammar', 10.0)
            assert 'excellent' in desc.lower()

    # -- Usage ranges --

    def test_usage_score_2(self, db, app):
        with app.app_context():
            desc = get_score_description('usage', 2.0)
            assert 'significant work' in desc.lower()

    def test_usage_score_5(self, db, app):
        with app.app_context():
            desc = get_score_description('usage', 5.0)
            assert 'developing' in desc.lower()

    def test_usage_score_6(self, db, app):
        with app.app_context():
            desc = get_score_description('usage', 6.0)
            assert 'good' in desc.lower()

    def test_usage_score_9(self, db, app):
        with app.app_context():
            desc = get_score_description('usage', 9.0)
            assert 'strong' in desc.lower()

    def test_usage_score_10(self, db, app):
        with app.app_context():
            desc = get_score_description('usage', 10.0)
            assert 'excellent' in desc.lower()

    # -- Naturalness ranges --

    def test_naturalness_score_1(self, db, app):
        with app.app_context():
            desc = get_score_description('naturalness', 1.0)
            assert 'translated' in desc.lower()

    def test_naturalness_score_4(self, db, app):
        with app.app_context():
            desc = get_score_description('naturalness', 4.0)
            assert 'developing' in desc.lower()

    def test_naturalness_score_7(self, db, app):
        with app.app_context():
            desc = get_score_description('naturalness', 7.0)
            assert 'reasonably natural' in desc.lower()

    def test_naturalness_score_8(self, db, app):
        with app.app_context():
            desc = get_score_description('naturalness', 8.0)
            assert 'strong' in desc.lower()

    def test_naturalness_score_10(self, db, app):
        with app.app_context():
            desc = get_score_description('naturalness', 10.0)
            # The 10 description contains Chinese characters; check for the English part
            assert "can't be more natural" in desc.lower() or "natural" in desc.lower()

    # -- Fractional scores that round to boundary values --

    def test_fractional_score_3_4_rounds_to_3(self, db, app):
        """3.4 rounds to 3 -> (1,3) range."""
        with app.app_context():
            desc = get_score_description('grammar', 3.4)
            assert 'significant work' in desc.lower()

    def test_fractional_score_3_5_rounds_to_4(self, db, app):
        """3.5 rounds to 4 -> (4,5) range."""
        with app.app_context():
            desc = get_score_description('grammar', 3.5)
            assert 'developing' in desc.lower()

    def test_fractional_score_5_5_rounds_to_6(self, db, app):
        """5.5 rounds to 6 -> (6,7) range."""
        with app.app_context():
            desc = get_score_description('grammar', 5.5)
            assert 'solid' in desc.lower()

    def test_fractional_score_6_7_rounds_to_7(self, db, app):
        """6.7 rounds to 7 -> (6,7) range."""
        with app.app_context():
            desc = get_score_description('grammar', 6.7)
            assert 'solid' in desc.lower()

    def test_fractional_score_7_5_rounds_to_8(self, db, app):
        """7.5 rounds to 8 -> (8,9) range."""
        with app.app_context():
            desc = get_score_description('grammar', 7.5)
            assert 'strong' in desc.lower()

    def test_fractional_score_9_5_rounds_to_10(self, db, app):
        """9.5 rounds to 10 -> (10,10) range."""
        with app.app_context():
            desc = get_score_description('grammar', 9.5)
            assert 'excellent' in desc.lower()

    def test_fractional_score_9_4_rounds_to_9(self, db, app):
        """9.4 rounds to 9 -> (8,9) range."""
        with app.app_context():
            desc = get_score_description('grammar', 9.4)
            assert 'strong' in desc.lower()

    # -- Edge: exact boundary values return correct description --

    def test_each_score_type_returns_string(self, db, app):
        """Every score type and a mid-range value should produce a non-empty string."""
        with app.app_context():
            for score_type in ('grammar', 'usage', 'naturalness'):
                desc = get_score_description(score_type, 5.0)
                assert isinstance(desc, str)
                assert len(desc) > 0
