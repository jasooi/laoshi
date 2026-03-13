"""Practice session API endpoints."""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import User, UserSession, SessionWord
from ai_layer.practice_runner import initialize_session, handle_message, advance_word, complete_session

# Maximum message length to prevent abuse
MAX_MESSAGE_LENGTH = 2000


class PracticeSessionResource(Resource):
    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        words_count = data.get('words_count')
        deck_id = data.get('deck_id')

        # Validate deck_id is required
        if not deck_id:
            return {'error': 'deck_id is required'}, 400

        if not isinstance(deck_id, int):
            return {'error': 'deck_id must be an integer'}, 400

        # Validate words_count if provided
        if words_count is not None:
            if not isinstance(words_count, int) or words_count < 1 or words_count > 50:
                return {'error': 'words_count must be an integer between 1 and 50'}, 400

        result, error = initialize_session(user_id, deck_id, words_count)
        if error:
            return {'error': error}, 400
        return result, 201


class PracticeMessageResource(Resource):
    from extensions import limiter

    @limiter.limit("30 per minute")
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data or not data.get('message'):
            return {'error': 'Message is required'}, 400

        message = data['message']
        if len(message) > MAX_MESSAGE_LENGTH:
            return {'error': f'Message must be at most {MAX_MESSAGE_LENGTH} characters'}, 400

        result, error = handle_message(id, user_id, message)
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeNextWordResource(Resource):
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        quality = data.get('quality')

        # Validate quality if provided
        if quality is not None:
            if not isinstance(quality, int) or quality < 0 or quality > 5:
                return {'error': 'quality must be an integer between 0 and 5'}, 400

        result, error = advance_word(id, user_id, quality)
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeEndSessionResource(Resource):
    @jwt_required()
    def post(self, id):
        """End a practice session early, marking remaining words as skipped."""
        user_id = int(get_jwt_identity())
        user = User.get_by_id(user_id)
        session = UserSession.get_by_id(id)

        if not session or session.user_id != user_id:
            return {'error': 'Session not found'}, 404

        if session.session_end_ds is not None:
            return {'error': 'Session is already complete'}, 400

        # Mark all remaining pending words as skipped
        session_words = SessionWord.get_list_by_session_id(id)
        for sw in session_words:
            if sw.status == 0:  # pending
                sw.is_skipped = True
                sw.status = -1  # skipped
                sw.update()

        # Complete the session
        result, error = complete_session(id, user_id)
        if error:
            return {'error': error}, 400
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
