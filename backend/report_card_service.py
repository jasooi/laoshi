"""Report Card business logic -- topline metrics, charts, scores, feedback generation."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from extensions import db
from models import User, UserProfile, UserSession, SessionWord, SessionWordAttempt
from ai_layer.context import ReportCardContext
from ai_layer.chat_agents import build_report_card_agent
from ai_layer.mem0_setup import mem0_client
from ai_layer.practice_runner import _parse_json_from_string
from crypto_utils import decrypt_api_key

from agents import Runner

logger = logging.getLogger(__name__)

MAX_SESSION_HOURS = 2.0
FALLBACK_FEEDBACK = "Keep practicing! Check back after your next session for personalised feedback."


def get_topline_metrics(user_id: int) -> dict:
    """Returns {time_practiced_hours, sessions_completed, words_practiced}."""
    # time_practiced_hours (cap each session at 2 hours)
    sessions = UserSession.query.filter(
        UserSession.user_id == user_id,
        UserSession.session_end_ds.isnot(None)
    ).all()
    total_seconds = 0
    for s in sessions:
        duration = (s.session_end_ds - s.session_start_ds).total_seconds()
        total_seconds += min(duration, MAX_SESSION_HOURS * 3600)
    time_practiced_hours = round(total_seconds / 3600, 1)

    # sessions_completed
    sessions_completed = UserSession.query.filter(
        UserSession.user_id == user_id,
        UserSession.session_end_ds.isnot(None)
    ).count()

    # words_practiced (distinct word_ids with status=1)
    words_practiced = db.session.query(
        db.func.count(db.distinct(SessionWord.word_id))
    ).join(
        UserSession, SessionWord.session_id == UserSession.id
    ).filter(
        UserSession.user_id == user_id,
        SessionWord.status == 1
    ).scalar() or 0

    return {
        'time_practiced_hours': time_practiced_hours,
        'sessions_completed': sessions_completed,
        'words_practiced': words_practiced,
    }


def get_daily_chart_data(user_id: int) -> list[dict]:
    """Returns list of {date, correct, incorrect} for last 7 days."""
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)

    results = db.session.query(
        db.func.date(SessionWordAttempt.created_ds).label('attempt_date'),
        db.func.sum(db.case((SessionWordAttempt.is_correct == True, 1), else_=0)).label('correct'),
        db.func.sum(db.case((SessionWordAttempt.is_correct == False, 1), else_=0)).label('incorrect'),
    ).join(
        SessionWord,
        db.and_(
            SessionWordAttempt.word_id == SessionWord.word_id,
            SessionWordAttempt.session_id == SessionWord.session_id
        )
    ).join(
        UserSession, SessionWord.session_id == UserSession.id
    ).filter(
        UserSession.user_id == user_id,
        SessionWordAttempt.created_ds >= datetime.combine(seven_days_ago, datetime.min.time())
    ).group_by(
        db.func.date(SessionWordAttempt.created_ds)
    ).all()

    # Build lookup from query results
    data_map = {}
    for row in results:
        date_str = str(row.attempt_date)
        data_map[date_str] = {
            'correct': int(row.correct or 0),
            'incorrect': int(row.incorrect or 0),
        }

    # Fill all 7 days
    chart_data = []
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        date_str = d.isoformat()
        entry = data_map.get(date_str, {'correct': 0, 'incorrect': 0})
        chart_data.append({
            'date': date_str,
            'correct': entry['correct'],
            'incorrect': entry['incorrect'],
        })

    return chart_data


def get_rolling_scores(user_id: int) -> dict:
    """Returns {grammar, usage, naturalness} averages from last 5 completed sessions."""
    # Get last 5 completed session IDs
    session_ids = db.session.query(UserSession.id).filter(
        UserSession.user_id == user_id,
        UserSession.session_end_ds.isnot(None)
    ).order_by(UserSession.session_end_ds.desc()).limit(5).all()
    session_ids = [s.id for s in session_ids]

    if not session_ids:
        return {'grammar': None, 'usage': None, 'naturalness': None}

    result = db.session.query(
        db.func.avg(SessionWord.grammar_score),
        db.func.avg(SessionWord.usage_score),
        db.func.avg(SessionWord.naturalness_score)
    ).filter(
        SessionWord.session_id.in_(session_ids),
        SessionWord.status == 1,
        SessionWord.grammar_score.isnot(None)
    ).first()

    if not result or result[0] is None:
        return {'grammar': None, 'usage': None, 'naturalness': None}

    return {
        'grammar': round(float(result[0]), 1),
        'usage': round(float(result[1]), 1),
        'naturalness': round(float(result[2]), 1),
    }


SCORE_DESCRIPTIONS = {
    'grammar': {
        (1, 3): "Needs significant work on sentence structure, word order, and grammatical particles.",
        (4, 5): "Developing grammar skills. Common patterns are emerging but errors are frequent.",
        (6, 7): "Solid grammar with occasional mistakes in word order and particles.",
        (8, 9): "Strong grammar skills. Sentences are well-structured with rare errors.",
        (10, 10): "Excellent grammar. Native-level sentence structure and particle usage.",
    },
    'usage': {
        (1, 3): "Needs significant work on word meaning, context, and collocations.",
        (4, 5): "Developing word usage. Basic meanings understood but context often off.",
        (6, 7): "Good word usage with mostly appropriate context and collocations.",
        (8, 9): "Strong word usage with accurate meaning and natural collocations.",
        (10, 10): "Excellent word usage. Perfect meaning, context, and collocation choices.",
    },
    'naturalness': {
        (1, 3): "Sentences sound translated. Needs exposure to natural Chinese patterns.",
        (4, 5): "Developing expression capabilities. Some expressions sound reasonably natural but many do not.",
        (6, 7): "Reasonably natural expression approaching native-like fluency.",
        (8, 9): "Strong natural expression. Most sentences sound authentically Chinese.",
        (10, 10): "You can't be more natural at Chinese than this. \u4f60\u662f\u4e2d\u56fd\u4eba\u5417\uff1f",
    },
}


def get_score_description(score_type: str, score: float | None) -> str | None:
    """Return a descriptive string for the given score type and value."""
    if score is None:
        return None
    rounded = round(score)
    for (low, high), desc in SCORE_DESCRIPTIONS[score_type].items():
        if low <= rounded <= high:
            return desc
    return None


def generate_report_card_feedback(user_id: int) -> str:
    """Generate and store AI teacher feedback. Returns the feedback text."""
    try:
        user = User.get_by_id(user_id)
        if not user:
            return FALLBACK_FEEDBACK

        profile = UserProfile.get_by_user_id(user_id)
        if not profile:
            return FALLBACK_FEEDBACK

        preferred_name = (profile.preferred_name or user.username)

        # Fetch mem0 memories
        mem0_prefs = None
        try:
            memories = mem0_client.search(
                query="learning patterns and common mistakes",
                user_id=str(user_id)
            )
            if memories:
                mem0_prefs = str(memories)
        except Exception:
            pass  # mem0 failure should not block feedback

        # Fetch last 3 session summaries
        recent_sessions = UserSession.query.filter_by(user_id=user_id).filter(
            UserSession.session_end_ds.isnot(None)
        ).order_by(UserSession.session_end_ds.desc()).limit(3).all()
        summaries = [s.summary_text for s in recent_sessions if s.summary_text]
        recent_summaries = "\n---\n".join(summaries) if summaries else None

        # Get rolling scores
        scores = get_rolling_scores(user_id)
        avg_grammar = scores['grammar'] or 5.0
        avg_usage = scores['usage'] or 5.0
        avg_naturalness = scores['naturalness'] or 5.0

        # BYOK support
        gemini_key = None
        if profile.encrypted_gemini_api_key:
            try:
                gemini_key = decrypt_api_key(profile.encrypted_gemini_api_key)
            except Exception:
                pass
        agent = build_report_card_agent(gemini_api_key=gemini_key)

        # Build context and run agent
        ctx = ReportCardContext(
            user_id=user_id,
            preferred_name=preferred_name,
            mem0_preferences=mem0_prefs,
            recent_summaries=recent_summaries,
            avg_grammar=avg_grammar,
            avg_usage=avg_usage,
            avg_naturalness=avg_naturalness,
        )

        from agents import RunContextWrapper
        result = asyncio.run(Runner.run(agent, input="Generate report card feedback.", context=ctx))

        output_text = result.final_output if hasattr(result, 'final_output') else str(result)

        # Parse JSON response
        parsed = _parse_json_from_string(output_text)
        if parsed and 'feedback' in parsed:
            feedback = parsed['feedback']
        else:
            feedback = output_text  # Use raw text if JSON parse fails

        # Store feedback
        profile.report_card_feedback = feedback
        profile.update()

        return feedback

    except Exception as e:
        logger.exception("Report card feedback generation failed: %s", e)
        # Store fallback
        try:
            profile = UserProfile.get_by_user_id(user_id)
            if profile:
                profile.report_card_feedback = FALLBACK_FEEDBACK
                profile.update()
        except Exception:
            pass
        return FALLBACK_FEEDBACK
