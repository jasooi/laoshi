"""Progress stats API endpoints for home page."""
from datetime import datetime, timezone
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Word, UserSession, SessionWord
from extensions import db


class ProgressStatsResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())

        # Total words
        total_words = Word.query.filter_by(user_id=user_id).count()

        if total_words == 0:
            return {
                'words_practiced_today': 0,
                'mastery_percentage': 0,
                'words_ready_for_review': 0,
                'total_words': 0,
            }, 200

        # Words practiced today (distinct word_ids from completed session words in today's sessions)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        words_today = db.session.query(
            db.func.count(db.distinct(SessionWord.word_id))
        ).join(
            UserSession, SessionWord.session_id == UserSession.id
        ).filter(
            UserSession.user_id == user_id,
            SessionWord.status == 1,  # completed
            UserSession.session_start_ds >= today_start
        ).scalar() or 0

        # Mastery percentage (strictly > 0.9 to match Word.STATUS_THRESHOLDS)
        mastered_count = Word.query.filter_by(user_id=user_id).filter(
            Word.confidence_score > 0.9
        ).count()
        mastery_percentage = round(mastered_count / total_words * 100)

        # Words ready for review (confidence < 0.9, matches practice_runner word selection)
        words_ready = Word.query.filter_by(user_id=user_id).filter(
            Word.confidence_score < 0.9
        ).count()

        return {
            'words_practiced_today': words_today,
            'mastery_percentage': mastery_percentage,
            'words_ready_for_review': words_ready,
            'total_words': total_words,
        }, 200
