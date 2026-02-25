"""Practice session API endpoints."""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import User, UserSession, SessionWord
from ai_layer.practice_runner import initialize_session, handle_message, advance_word


class PracticeSessionResource(Resource):
    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        words_count = data.get('words_count')

        result, error = initialize_session(user_id, words_count)
        if error:
            return {'error': error}, 400
        return result, 201


class PracticeMessageResource(Resource):
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data or not data.get('message'):
            return {'error': 'Message is required'}, 400

        result, error = handle_message(id, user_id, data['message'])
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeNextWordResource(Resource):
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())

        result, error = advance_word(id, user_id)
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeSummaryResource(Resource):
    @jwt_required()
    def get(self, id):
        user_id = int(get_jwt_identity())
        user = User.get_by_id(user_id)
        session = UserSession.get_by_id(id)

        if not session or session.user_id != user_id:
            return {'error': 'Session not found'}, 404

        session_words = SessionWord.get_list_by_session_id(id)
        words_practiced = sum(1 for sw in session_words if sw.status == 1)
        words_skipped = sum(1 for sw in session_words if sw.status == -1)

        word_results = []
        for sw in sorted(session_words, key=lambda s: s.word_order):
            w = sw.word
            word_results.append({
                'word': w.word,
                'grammar_score': sw.grammar_score,
                'usage_score': sw.usage_score,
                'naturalness_score': sw.naturalness_score,
                'is_correct': sw.is_correct,
                'is_skipped': sw.is_skipped,
            })

        return {
            'session_id': id,
            'summary_text': session.summary_text,
            'words_practiced': words_practiced,
            'words_skipped': words_skipped,
            'word_results': word_results,
        }, 200
