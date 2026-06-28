"""Report Card API endpoints."""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import UserProfile
from report_card_service import (
    get_topline_metrics,
    get_daily_chart_data,
    get_rolling_scores,
    get_score_description,
    generate_report_card_feedback,
)


class ReportCardResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())

        topline = get_topline_metrics(user_id)
        chart_data = get_daily_chart_data(user_id)
        scores = get_rolling_scores(user_id)

        score_breakdown = {}
        for score_type in ['grammar', 'usage', 'naturalness']:
            score_breakdown[score_type] = {
                'score': scores[score_type],
                'description': get_score_description(score_type, scores[score_type]),
            }

        profile = UserProfile.get_by_user_id(user_id)
        teacher_feedback = profile.report_card_feedback if profile else None

        return {
            'topline': topline,
            'chart_data': chart_data,
            'score_breakdown': score_breakdown,
            'teacher_feedback': teacher_feedback,
        }, 200


class GenerateFeedbackResource(Resource):
    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        language = data.get('language', 'ZH')
        feedback = generate_report_card_feedback(user_id, language=language)
        return {'feedback': feedback}, 200


class StreakResource(Resource):
    @jwt_required()
    def get(self):
        """Get user's current streak and last practice date."""
        user_id = int(get_jwt_identity())
        profile = UserProfile.get_by_user_id(user_id)

        if not profile:
            return {'error': 'User profile not found'}, 404

        return {
            'current_streak': profile.current_streak or 0,
            'last_practice_date': profile.last_practice_date.isoformat() if profile.last_practice_date else None,
        }, 200
