# This file contains the resources for the Flask-Restful app
# 8 Resources to be defined: word, wordslist, user, userslist, session, sessionslist, word_session, word_sessionslist

from flask import request, make_response
from flask_restful import Resource
from http import HTTPStatus
from models import Word, User, SessionWord, UserSession, TokenBlocklist
from datetime import datetime
from utils import hash_password, check_password, paginate_query
from extensions import db
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_refresh_cookies, unset_refresh_cookies
)
from sqlalchemy.exc import IntegrityError
import re


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.
    Returns (is_valid, error_message).
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Only alphanumeric characters (letters and numbers)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.match(r'^[a-zA-Z0-9]+$', password):
        return False, "Password must contain only letters and numbers"
    
    return True, ""

class WordListResource(Resource):

    @jwt_required()
    def get(self):
        vc_user = User.get_by_id(int(get_jwt_identity()))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str).strip()
        sort_by = request.args.get('sort_by', 'pinyin', type=str)

        base_query = Word.get_query_for_user(vc_user)

        if search:
            pattern = f"%{search}%"
            base_query = base_query.filter(
                db.or_(
                    Word.word.ilike(pattern),
                    Word.pinyin.ilike(pattern),
                    Word.meaning.ilike(pattern),
                )
            )

        if sort_by == 'word':
            base_query = base_query.order_by(Word.word)
        else:
            base_query = base_query.order_by(Word.pinyin)

        items, pagination = paginate_query(base_query, page=page, per_page=per_page)
        data = [w.format_data(vc_user) for w in items]

        return {"data": data, "pagination": pagination}, 200

    @jwt_required()
    def post(self):
        # Words are created in bulk by default
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        if not isinstance(data, list):
            return {"error": "Expected a JSON array of words"}, 400

        for i, item in enumerate(data):
            for key in ("word", "pinyin", "meaning"):
                if key not in item or not item[key]:
                    return {"error": f"Row {i+1} is missing required field: {key}"}, 400

        vc_user = User.get_by_id(int(get_jwt_identity()))

        words_list = []
        for item in data:
            word_to_add = Word(word=item["word"], pinyin=item["pinyin"], meaning=item["meaning"], source_name=item.get("source_name"), user_id=vc_user.id)
            words_list.append(word_to_add)

        try:
            Word.add_list(words_list)
        except IntegrityError:
            return {"error": "Invalid user_id - user does not exist"}, 400
        except Exception as e:
            return {"error": str(e)}, 500
        
        # Format data after commit so ids are populated
        added_words_list_json = [word.format_data(vc_user) for word in words_list]
        return {"created_data": added_words_list_json}, HTTPStatus.CREATED


    @jwt_required()
    def delete(self):
        # this deletes all words for the logged in user
        vc_user = User.get_by_id(int(get_jwt_identity()))
        try:
            Word.delete_all(vc_user)
        except Exception as e:
            return {"error": str(e)}, 500

        success_message = "All your words successfully deleted"
        return {'message': success_message}, HTTPStatus.OK
        


class WordResource(Resource):
    @jwt_required()
    def get(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500
        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner only
        if not found_word.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        return found_word.format_data(vc_user), 200

    @jwt_required()
    def put(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        data = request.get_json()

        if not data:
            return {"error": "No data provided"}, 400

        allowable_fields = ["word", "pinyin", "meaning", "confidence_score", "source_name"]
        fields_to_update = [k for k in data.keys() if k in allowable_fields]

        if len(fields_to_update) == 0:
            return {"error": "Invalid update parameters"}, 400
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner only
        if not found_word.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        for field in fields_to_update:
            if field == "confidence_score":
                found_word.update_confidence_score(new_value=data[field])
                continue
            setattr(found_word, field, data[field])

        try:
            found_word.update()
        except Exception as e:
            return {"error": str(e)}, 500

        return found_word.format_data(vc_user), HTTPStatus.OK

    @jwt_required()
    def delete(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner only
        if not found_word.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        try:
            found_word.delete()
        except Exception as e:
            return {"error": str(e)}, 500

        success_message = f"word {found_word.word} successfully deleted"
        return {'message': success_message}, HTTPStatus.OK
        
        

class UserListResource(Resource):
    @jwt_required()
    def get(self):
        
        vc_user = User.get_by_id(int(get_jwt_identity()))

        if not vc_user.is_admin:
            return {"error": "Forbidden"}, 403

        try:
            users_list = User.get_full_list()
        except Exception as e:
            return {"error": str(e)}, 500
        
        if not users_list:
            return {'error': 'no users found'}, HTTPStatus.NOT_FOUND
        users_list_json = [u.format_data(vc_user) for u in users_list]
        return users_list_json, 200


    def post(self):
        # Users can only be created one at a time
        data = request.get_json()

        if not data:
            return {"error": "No data provided"}, 400

        # mandatory fields - use key indexing to throw error if key doesn't exist
        try:
            username = data['username']
            email = data['email']
        except KeyError:
            return {"error": "Email and Username are required"}, 400

        # optional fields - use dict.get() to default to None if not found
        preferred_name = data.get('preferred_name')
        non_hash_password = data.get('password')
        
        # Validate password
        is_password_valid, password_error = validate_password(non_hash_password)
        if not is_password_valid:
            return {"error": password_error}, 400
        
        hashed_password = hash_password(non_hash_password)

        if not User.is_email_valid(email):
            return {"error": "Email invalid or already registered"}, 400
        if not User.is_username_valid(username):
            return {"error": "Username invalid or already registered"}, 400
        
        current_ds = datetime.now()
        user_to_add = User(username=username, email=email, password=hashed_password, preferred_name=preferred_name, created_ds=current_ds)
        
        try:
            user_to_add.add()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"created_data": user_to_add.format_data()}, HTTPStatus.CREATED
    

class UserResource(Resource):
    @jwt_required(optional=True)
    def get(self, id: int):
        try:
            found_user = User.get_by_id(id)
            if not found_user:
                return {'error': 'user not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {"error": str(e)}, 500
        
        # Since we set identity=user.id when using create_access_token, user.id is returned
        identity = get_jwt_identity()
        current_user = User.get_by_id(int(identity)) if identity else None
        return found_user.format_data(current_user), 200

    @jwt_required()
    def put(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        data = request.get_json()

        if not data:
            return {"error": "No data provided"}, 400

        allowable_fields = ["username", "email", "password", "preferred_name"]
        fields_to_update = [k for k in data.keys() if k in allowable_fields]

        try:
            found_user = User.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_user:
            return {'error': 'user not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner or admin only
        if vc_user.id != found_user.id and not vc_user.is_admin:
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        for field in fields_to_update:
            if field == "username" and not User.is_username_valid(data[field]):
                return {"error": "Username invalid or already registered"}, 400
            if field == "email" and not User.is_email_valid(data[field]):
                return {"error": "Email invalid or already registered"}, 400
            setattr(found_user, field, data[field])

        try:
            found_user.update()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"updated_data": found_user.format_data(vc_user)}, HTTPStatus.OK
            
                

class SessionListResource(Resource):
    # TODO: add get by date range parameters

    @jwt_required()
    def get(self):
        vc_user = User.get_by_id(int(get_jwt_identity()))

        # Access control: admin only
        if not vc_user.is_admin:
            return {"error": "Forbidden"}, HTTPStatus.FORBIDDEN

        try:
            session_list = UserSession.get_full_list()
        except Exception as e:
            return {"error": str(e)}, 500

        if not session_list:
            return {'error': 'no sessions found'}, HTTPStatus.NOT_FOUND

        session_list_json = [s.format_data(vc_user) for s in session_list]
        return session_list_json, 200

    @jwt_required()
    def post(self):
        vc_user = User.get_by_id(int(get_jwt_identity()))

        # Auto-assign user_id from JWT - users can only create sessions for themselves
        session_start_ds = datetime.now()
        new_session = UserSession(session_start_ds=session_start_ds, user_id=vc_user.id)

        try:
            new_session.add()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"created_data": new_session.format_data(vc_user)}, HTTPStatus.CREATED


class SessionResource(Resource):
    @jwt_required()
    def get(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        try:
            found_session = UserSession.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500
        if not found_session:
            return {'error': 'session not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner or admin
        if not found_session.can_view(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        session_data = found_session.format_data(vc_user)
        if session_data["session_end_ds"]:
            duration = session_data["session_end_ds"] - session_data["session_start_ds"]
            session_data["duration_seconds"] = duration.total_seconds()
        else:
            session_data["duration_seconds"] = None

        return session_data, 200

    @jwt_required()
    def put(self, id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        # put is just to update session_end_ds
        data = request.get_json()
        session_end_ds = data.get("session_end_ds")
        if not session_end_ds:
            return {"error": "No session end ds provided"}, 400

        try:
            found_session = UserSession.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_session:
            return {'error': 'session not found'}, HTTPStatus.NOT_FOUND

        # Access control: owner only
        if not found_session.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        try:
            session_end_ds = datetime.fromisoformat(session_end_ds)
        except (ValueError, TypeError):
            return {"error": "Invalid datetime format. Use ISO format (e.g., 2024-01-15T14:30:00)"}, 400

        if not found_session.is_new_session_end_valid(new_session_end=session_end_ds):
            return {"error": "Session end timestamp invalid"}, 400

        found_session.session_end_ds = session_end_ds
        try:
            found_session.update()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"updated_data": found_session.format_data(vc_user)}, HTTPStatus.OK


class SessionWordListResource(Resource):
    @jwt_required()
    def get(self, session_id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))

        # First check if session exists and viewer has access
        found_session = UserSession.get_by_id(session_id)
        if not found_session:
            return {'error': 'session not found'}, HTTPStatus.NOT_FOUND

        # Access control: session owner or admin
        if not found_session.can_view(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        try:
            session_word_list = SessionWord.get_list_by_session_id(session_id=session_id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not session_word_list:
            return {'error': 'no words found in session'}, HTTPStatus.NOT_FOUND

        session_word_list_json = [s.format_data(vc_user) for s in session_word_list]
        return session_word_list_json, 200

    @jwt_required()
    def post(self, session_id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))

        # First check if session exists and viewer is the owner
        found_session = UserSession.get_by_id(session_id)
        if not found_session:
            return {'error': 'session not found'}, HTTPStatus.NOT_FOUND

        # Access control: session owner only
        if not found_session.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        data = request.get_json()
        word_id = data.get("word_id")

        if not word_id:
            return {"error": "word_id missing. word_id must be provided"}, 400

        load_ds = datetime.now()
        new_session_word = SessionWord(word_id=word_id, session_id=session_id, session_word_load_ds=load_ds, is_skipped=False, session_notes=None)

        try:
            new_session_word.add()
        except IntegrityError:
            return {"error": "Invalid word_id or session_id - referenced record does not exist"}, 400
        except Exception as e:
            return {"error": str(e)}, 500

        return {"created_data": new_session_word.format_data(vc_user)}, HTTPStatus.CREATED


class SessionWordResource(Resource):
    @jwt_required()
    def get(self, session_id: int, word_id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        try:
            found_session_word = SessionWord.get_by_session_word_id(word_id=word_id, session_id=session_id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_session_word:
            return {'error': 'Session word not found'}, HTTPStatus.NOT_FOUND

        # Access control: session owner or admin
        if not found_session_word.can_view(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        return found_session_word.format_data(vc_user), 200

    @jwt_required()
    def put(self, session_id: int, word_id: int):
        vc_user = User.get_by_id(int(get_jwt_identity()))
        # put is to update is_skipped and session_notes
        data = request.get_json()

        if not data:
            return {"error": "No data provided"}, 400

        allowable_fields = ["is_skipped", "session_notes"]
        fields_to_update = [k for k in data.keys() if k in allowable_fields]

        try:
            found_session_word = SessionWord.get_by_session_word_id(word_id=word_id, session_id=session_id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_session_word:
            return {'error': 'session word not found'}, HTTPStatus.NOT_FOUND

        # Access control: session owner only
        if not found_session_word.is_owner(vc_user):
            return {'error': 'Forbidden'}, HTTPStatus.FORBIDDEN

        for field in fields_to_update:
            setattr(found_session_word, field, data[field])

        try:
            found_session_word.update()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"updated_data": found_session_word.format_data(vc_user)}, HTTPStatus.OK


class HomeResource(Resource):
    def get(self):
        return "You have successfully called this API. Congrats!"
        

class TokenResource(Resource):
    # This is the login endpoint
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.get_by_username(username)

        if not user or not check_password(password, user.password):
            return {'message': 'Username or password is incorrect.'}, HTTPStatus.UNAUTHORIZED

        try:
            identity = str(user.id)
            access_token = create_access_token(identity=identity)
            refresh_token = create_refresh_token(identity=identity)
        except Exception as e:
            return {'message': 'Failure creating access token.'}, 500

        response = make_response(
            {'access_token': access_token},
            HTTPStatus.OK
        )
        set_refresh_cookies(response, refresh_token)
        return response
    

class TokenRefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Issue a new access token + rotated refresh token."""
        identity = get_jwt_identity()
        old_jti = get_jwt()['jti']

        # Blocklist the old refresh token
        now = datetime.now()
        blocklist_entry = TokenBlocklist(jti=old_jti, created_ds=now)
        blocklist_entry.add()

        # Issue new tokens
        new_access_token = create_access_token(identity=identity)
        new_refresh_token = create_refresh_token(identity=identity)

        response = make_response(
            {'access_token': new_access_token},
            HTTPStatus.OK
        )
        set_refresh_cookies(response, new_refresh_token)
        return response


class TokenRevokeResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Revoke the refresh token (logout)."""
        jti = get_jwt()['jti']
        now = datetime.now()

        blocklist_entry = TokenBlocklist(jti=jti, created_ds=now)
        blocklist_entry.add()

        response = make_response(
            {'message': 'Token revoked'},
            HTTPStatus.OK
        )
        unset_refresh_cookies(response)
        return response


class MeResource(Resource):
    # return data on self for logged in users
    @jwt_required()
    def get(self):
        try:
            found_user = User.get_by_id(int(get_jwt_identity()))
            if not found_user:
                return {'error': 'user not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {"error": str(e)}, 500

        return found_user.format_data(found_user), 200
