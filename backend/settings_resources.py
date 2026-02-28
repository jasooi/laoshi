"""Settings API endpoints for user preferences and BYOK API keys."""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import UserProfile
from crypto_utils import encrypt_api_key
from ai_layer.key_validator import validate_deepseek_key, validate_gemini_key


class UserSettingsResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        profile = UserProfile.get_by_user_id(user_id)

        if not profile:
            return {
                'preferred_name': None,
                'words_per_session': None,
                'has_deepseek_key': False,
                'has_gemini_key': False,
            }, 200

        return profile.format_settings(), 200

    @jwt_required()
    def put(self):
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        # Validate inputs
        if 'preferred_name' in data and data['preferred_name'] is not None:
            if len(str(data['preferred_name'])) > 80:
                return {"error": "preferred_name must be at most 80 characters"}, 400

        if 'words_per_session' in data and data['words_per_session'] is not None:
            wps = data['words_per_session']
            if not isinstance(wps, int) or wps < 1 or wps > 50:
                return {"error": "words_per_session must be between 1 and 50"}, 400

        # Lazy-create profile
        profile = UserProfile.get_by_user_id(user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            profile.add()

        # Update fields
        if 'preferred_name' in data:
            profile.preferred_name = data['preferred_name']  # None clears it

        if 'words_per_session' in data:
            profile.words_per_session = data['words_per_session']  # None resets to default

        profile.update()
        return profile.format_settings(), 200


class UserSettingsKeyResource(Resource):
    @jwt_required()
    def delete(self, provider):
        if provider not in ('deepseek', 'gemini'):
            return {"error": "Invalid provider. Must be 'deepseek' or 'gemini'."}, 400

        user_id = int(get_jwt_identity())
        profile = UserProfile.get_by_user_id(user_id)

        if not profile:
            return {
                "message": f"{provider.title()} API key cleared",
                f"has_{provider}_key": False,
                f"{provider}_key_version": 1
            }, 200

        if provider == 'deepseek':
            profile.encrypted_deepseek_api_key = None
        else:
            profile.encrypted_gemini_api_key = None

        profile.increment_key_version(provider)
        profile.update()
        return {
            "message": f"{provider.title()} API key cleared",
            f"has_{provider}_key": False,
            f"{provider}_key_version": getattr(profile, f"{provider}_key_version")
        }, 200


class UserSettingsKeyValidateResource(Resource):
    @jwt_required()
    async def post(self, provider):
        if provider not in ('deepseek', 'gemini'):
            return {"error": "Invalid provider. Must be 'deepseek' or 'gemini'."}, 400

        data = request.get_json()
        if not data or 'api_key' not in data:
            return {"error": "api_key is required"}, 400

        api_key = data['api_key']
        if len(api_key) > 500:
            return {"error": "api_key must be at most 500 characters"}, 400

        # Validate the key with real API call
        if provider == 'deepseek':
            is_valid, error = await validate_deepseek_key(api_key)
        else:
            is_valid, error = await validate_gemini_key(api_key)

        if not is_valid:
            return {"error": error}, 400

        # Key is valid - save it
        user_id = int(get_jwt_identity())
        profile = UserProfile.get_by_user_id(user_id)

        if not profile:
            profile = UserProfile(user_id=user_id)
            profile.add()

        # Encrypt and store
        encrypted = encrypt_api_key(api_key)
        if provider == 'deepseek':
            profile.encrypted_deepseek_api_key = encrypted
        else:
            profile.encrypted_gemini_api_key = encrypted

        profile.increment_key_version(provider)
        profile.update()

        return {
            "message": f"{provider.title()} API key saved",
            f"has_{provider}_key": True
        }, 200
