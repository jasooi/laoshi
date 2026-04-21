"""Password reset API endpoints."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask import request
from flask_restful import Resource

from extensions import db, limiter
from models import User, PasswordResetToken
from utils import hash_password
from resources import validate_password
from email_service import send_password_reset_email

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_HOURS = 1


def _hash_token(token: str) -> str:
    """Hash a reset token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class PasswordResetRequestResource(Resource):
    """POST /api/password-reset/request — Request a password reset email."""

    @limiter.limit("3 per minute")
    def post(self):
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()

        if not email:
            return {"error": "Email is required"}, 400

        user = User.query.filter(
            db.func.lower(User.email) == email
        ).first()

        if not user:
            return {"registered": False}, 200

        # Generate secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)

        # Invalidate any existing unused tokens for this user
        PasswordResetToken.query.filter_by(
            user_id=user.id, used=False
        ).update({"used": True})
        db.session.commit()

        # Create new token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_ds=datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
        )
        reset_token.add()

        # Send reset email (non-blocking)
        try:
            first_name = (user.profile.preferred_name if user.profile else None) or user.username
            send_password_reset_email(user.email, first_name, raw_token)
        except Exception:
            logger.exception("Failed to send password reset email")

        return {"registered": True}, 200


class PasswordResetResource(Resource):
    """POST /api/password-reset/reset — Reset password using token."""

    @limiter.limit("5 per minute")
    def post(self):
        data = request.get_json(silent=True) or {}
        raw_token = data.get('token', '').strip()
        new_password = data.get('new_password', '')

        if not raw_token:
            return {"error": "Reset token is required"}, 400
        if not new_password:
            return {"error": "New password is required"}, 400

        # Validate password complexity
        is_valid, password_error = validate_password(new_password)
        if not is_valid:
            return {"error": password_error}, 400

        # Look up token
        token_hash = _hash_token(raw_token)
        reset_token = PasswordResetToken.query.filter_by(
            token_hash=token_hash
        ).first()

        if not reset_token:
            return {"error": "Invalid or expired reset link"}, 400

        if not reset_token.is_valid():
            return {"error": "This reset link has expired or already been used"}, 400

        # Update password
        user = User.get_by_id(reset_token.user_id)
        if not user:
            return {"error": "User not found"}, 400

        user.password = hash_password(new_password)
        user.update()

        # Mark token as used
        reset_token.used = True
        db.session.commit()

        logger.info(f"Password reset successful for user {user.id}")
        return {"message": "Password has been reset successfully"}, 200
