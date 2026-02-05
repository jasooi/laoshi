# This file contains the resources for the Flask-Restful app
# 8 Resources to be defined: word, wordslist, user, userslist, session, sessionslist, word_session, word_sessionslist

from flask import request
from flask_restful import Resource
from http import HTTPStatus
from models import Word, User, SessionWord, UserSession
from datetime import datetime
from utils import hash_password, check_password
from sqlalchemy.exc import IntegrityError

class WordListResource(Resource):
    def get(self):
        user_filter = request.args.get("user_id", type=int)
        try:
            words_list = Word.get_full_list(user_filter)
        except Exception as e:
            return {"error": str(e)}, 500
        
        if not words_list:
            return {'error': 'no words found'}, HTTPStatus.NOT_FOUND

        words_list_json = [w.format_data() for w in words_list]
        return words_list_json, 200
        

    def post(self):
        # Words are created in bulk by default
        # TODO: add validation for individual word json data
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400
        
        try:
            user_id = data["user_id"]
            word_data = data["data"]
        except KeyError:
            return {"error": "Invalid format or missing data"}, 400
        
        

        word_to_add = None
        words_list = []
        for item in word_data:
            word_to_add = Word(word=item["word"], pinyin=item["pinyin"], meaning=item["meaning"], user_id=user_id)
            words_list.append(word_to_add)

        try:
            Word.add_list(words_list)
        except IntegrityError:
            return {"error": "Invalid user_id - user does not exist"}, 400
        except Exception as e:
            return {"error": str(e)}, 500
        
        # Format data after commit so ids are populated
        added_words_list_json = [word.format_data() for word in words_list]
        return {"created_data": added_words_list_json}, HTTPStatus.CREATED


    def delete(self):
        # this deletes all words
        try:
            Word.delete_all()
        except Exception as e:
            return {"error": str(e)}, 500
        
        success_message = "All words successfully deleted"
        return {'message': success_message}, HTTPStatus.OK
        


class WordResource(Resource):
    def get(self, id:int):
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500
        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND
        return found_word.format_data(), 200


    def put(self, id:int):
        data = request.get_json()

        if not data:
            return {"error": "No data provided"}, 400

        allowable_fields = ["word", "pinyin", "meaning", "confidence_score"]
        fields_to_update = [k for k in data.keys() if k in allowable_fields]

        if len(fields_to_update) == 0:
            return {"error": "Invalid update parameters"}, 400
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND

        for field in fields_to_update:
            if field == "confidence_score":
                found_word.update_confidence_score(new_value= data[field])
                continue
            setattr(found_word, field, data[field])

        try:
            found_word.update()
        except Exception as e:
            return {"error": str(e)}, 500
        
        return found_word.format_data(), HTTPStatus.OK
        
        
    def delete(self, id:int):
        try:
            found_word = Word.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500
        
        if not found_word:
            return {'error': 'word not found'}, HTTPStatus.NOT_FOUND
        
        try:
            found_word.delete()
        except Exception as e:
            return {"error": str(e)}, 500
        
        success_message = f"word {found_word.word} successfully deleted"
        return {'message': success_message}, HTTPStatus.OK
        
        

class UserListResource(Resource):
    def get(self):
        try:
            users_list = User.get_full_list()
        except Exception as e:
            return {"error": str(e)}, 500
        
        if not users_list:
            return {'error': 'no users found'}, HTTPStatus.NOT_FOUND
        users_list_json = [u.format_data() for u in users_list]
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
    def get(self, id: int):
        try:
            found_user = User.get_by_id(id)
            if not found_user:
                return {'error': 'user not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {"error": str(e)}, 500
        return found_user.format_data(), 200

    def put(self, id: int):
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

        return {"updated_data": found_user.format_data()}, HTTPStatus.OK
            
                

class SessionListResource(Resource):
    # TODO: add get by date range parameters

    def get(self):
        try:
            session_list = UserSession.get_full_list()
        except Exception as e:
            return {"error": str(e)}, 500

        if not session_list:
            return {'error': 'no sessions found'}, HTTPStatus.NOT_FOUND
        
        session_list_json = [s.format_data() for s in session_list]
        return session_list_json, 200
    
    def post(self):
        data = request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return {"error": "user_id missing. user_id must be provided"}, 400  

        # Only session start timestamp is filled - end ds is filled via put when session is ended
        session_start_ds = datetime.now()
        new_session = UserSession(session_start_ds=session_start_ds, user_id=user_id)

        try:
            new_session.add()
        except IntegrityError:
            return {"error": "Invalid user_id - user does not exist"}, 400
        except Exception as e:
            return {"error": str(e)}, 500

        return {"created_data": new_session.format_data()}, HTTPStatus.CREATED


class SessionResource(Resource):
    def get(self, id: int):
        try:
            found_session = UserSession.get_by_id(id)
        except Exception as e:
            return {"error": str(e)}, 500
        if not found_session:
            return {'error': 'session not found'}, HTTPStatus.NOT_FOUND

        session_data = found_session.format_data()
        if session_data["session_end_ds"]:
            duration = session_data["session_end_ds"] - session_data["session_start_ds"]
            session_data["duration_seconds"] = duration.total_seconds()
        else:
            session_data["duration_seconds"] = None

        return session_data, 200
    
    def put(self, id: int):
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

        return {"updated_data": found_session.format_data()}, HTTPStatus.OK


class SessionWordListResource(Resource):
    def get(self, session_id: int):
        try:
            session_word_list = SessionWord.get_list_by_session_id(session_id=session_id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not session_word_list:
            return {'error': 'no words found in session. Session may not exist.'}, HTTPStatus.NOT_FOUND
        
        session_word_list_json = [s.format_data() for s in session_word_list]
        return session_word_list_json, 200
    

    def post(self, session_id: int):
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

        return {"created_data": new_session_word.format_data()}, HTTPStatus.CREATED


class SessionWordResource(Resource):
    def get(self, session_id: int, word_id: int):
        try:
            found_session_word = SessionWord.get_by_session_word_id(word_id=word_id, session_id=session_id)
        except Exception as e:
            return {"error": str(e)}, 500

        if not found_session_word:
            return {'error': 'Session word not found. Session may not exist.'}, HTTPStatus.NOT_FOUND
        
        return found_session_word.format_data(), 200
    
    def put(self, session_id: int, word_id: int):
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

        for field in fields_to_update:
            setattr(found_session_word, field, data[field])

        try:
            found_session_word.update()
        except Exception as e:
            return {"error": str(e)}, 500

        return {"updated_data": found_session_word.format_data()}, HTTPStatus.OK


class HomeResource(Resource):
    def get(self):
        return "You have successfully called this API. Congrats!"
    
    def delete(self):
        return "This is a meaningless action, but have fun anyways."
        
