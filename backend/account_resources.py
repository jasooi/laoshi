"""Account management API endpoints."""

import logging

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import (
    User, UserProfile, Deck, Word, UserSession, SessionWord,
    SessionWordAttempt, PasswordResetToken, TokenBlocklist,
)
from utils import check_password

logger = logging.getLogger(__name__)


class AccountDeleteResource(Resource):
    """DELETE /api/account — Permanently delete the authenticated user's account."""

    @jwt_required()
    def delete(self):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        password = data.get('password', '')

        if not password:
            return {"error": "Password is required to confirm account deletion"}, 400

        user = User.get_by_id(user_id)
        if not user:
            return {"error": "User not found"}, 404

        # Verify password
        if not check_password(password, user.password):
            return {"error": "Incorrect password"}, 403

        try:
            # Delete in FK-safe order within a single transaction
            # 1. SessionWordAttempts (FK → SessionWord)
            session_ids = [s.id for s in UserSession.query.filter_by(user_id=user_id).all()]
            if session_ids:
                SessionWordAttempt.query.filter(
                    SessionWordAttempt.session_id.in_(session_ids)
                ).delete(synchronize_session=False)

                # 2. SessionWords (FK → UserSession)
                SessionWord.query.filter(
                    SessionWord.session_id.in_(session_ids)
                ).delete(synchronize_session=False)

            # 3. UserSessions
            UserSession.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # 4. Words (FK → User, Deck)
            Word.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # 5. Decks
            Deck.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # 6. PasswordResetTokens
            PasswordResetToken.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # 7. UserProfile
            UserProfile.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # 8. User
            User.query.filter_by(id=user_id).delete(synchronize_session=False)

            db.session.commit()
            logger.info(f"Account deleted for user {user_id}")
            return {"message": "Account deleted successfully"}, 200

        except Exception:
            db.session.rollback()
            logger.exception(f"Failed to delete account for user {user_id}")
            return {"error": "Failed to delete account. Please try again."}, 500
