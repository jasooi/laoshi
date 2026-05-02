"""Practice session API endpoints."""
import logging
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from openai import RateLimitError

from models import User, UserSession, SessionWord, Deck
from ai_layer.practice_runner import initialize_session, handle_message, advance_word, complete_session

logger = logging.getLogger(__name__)

RATE_LIMIT_RESPONSE = {
    'error': 'rate_limit',
    'message': 'AI provider rate limit exceeded. Add your own API key in Settings to continue.',
}

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

        try:
            result, error = initialize_session(user_id, deck_id, words_count)
        except RateLimitError as e:
            logger.warning(f"AI rate limit hit during session init: {e}")
            return RATE_LIMIT_RESPONSE, 429
        if error:
            return {'error': error}, 400
        return result, 201


class PracticeSessionDetailResource(Resource):
    @jwt_required()
    def get(self, id):
        """Get an existing practice session by ID."""
        user_id = int(get_jwt_identity())
        user = User.get_by_id(user_id)
        session = UserSession.get_by_id(id)

        if not session or session.user_id != user_id:
            return {'error': 'Session not found'}, 404

        session_words = SessionWord.get_list_by_session_id(id)
        words_practiced = sum(1 for sw in session_words if sw.status == 1)
        words_total = len(session_words)

        # Find current word (first pending word by order)
        current_word = None
        for sw in sorted(session_words, key=lambda sw: sw.word_order):
            if sw.status == 0:
                w = sw.word
                current_word = {
                    'word_id': w.id,
                    'word': w.word,
                    'pinyin': w.pinyin,
                    'meaning': w.meaning,
                }
                break

        # Get deck name
        deck_name = None
        if session.deck_id:
            deck = Deck.get_by_id(session.deck_id)
            if deck:
                deck_name = deck.name

        session_data = session.format_data(user)
        session_data['words_practiced'] = words_practiced
        session_data['words_total'] = words_total

        return {
            'session': session_data,
            'current_word': current_word,
            'deck_name': deck_name,
        }, 200


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

        try:
            print(f"[DEBUG] Processing message for session {id}, user {user_id}", flush=True)
            logger.info(f"Processing message for session {id}, user {user_id}")
            result, error = handle_message(id, user_id, message)
            print(f"[DEBUG] Message processed successfully for session {id}", flush=True)
            logger.info(f"Message processed successfully for session {id}")
        except RateLimitError as e:
            logger.warning(f"AI rate limit hit during message: {e}")
            return RATE_LIMIT_RESPONSE, 429
        except Exception as e:
            import traceback
            print(f"\n{'='*80}", flush=True)
            print(f"[ERROR] Exception in handle_message for session {id}, user {user_id}", flush=True)
            print(f"Error type: {type(e).__name__}", flush=True)
            print(f"Error message: {e}", flush=True)
            print("Full traceback:", flush=True)
            traceback.print_exc()
            print(f"{'='*80}\n", flush=True)
            logger.error(f"ERROR in handle_message for session {id}, user {user_id}: {e}", exc_info=True)
            return {'error': 'An internal error occurred'}, 500
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

        try:
            result, error = advance_word(id, user_id, quality)
        except RateLimitError as e:
            logger.warning(f"AI rate limit hit during advance_word: {e}")
            return RATE_LIMIT_RESPONSE, 429
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
        try:
            result, error = complete_session(id, user_id)
        except RateLimitError as e:
            logger.warning(f"AI rate limit hit during session end: {e}")
            return RATE_LIMIT_RESPONSE, 429
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
