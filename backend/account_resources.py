"""Account management API endpoints."""

import logging

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import User
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
            # ORM cascade handles all child records automatically
            db.session.delete(user)
            db.session.commit()
            logger.info(f"Account deleted for user {user_id}")
            return {"message": "Account deleted successfully"}, 200

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Failed to delete account for user {user_id}")
            logger.error(f"Delete account error details: {type(e).__name__}: {str(e)}")
            return {"error": "Failed to delete account. Please try again."}, 500
