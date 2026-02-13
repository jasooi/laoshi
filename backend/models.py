# File containing all models for Flask SQLAlchemy
# 4 models to be defined: Word, Word_session, Session, User

from extensions import db
from datetime import datetime
from utils import construct_date_range_filter


# Define models
class Word(db.Model):
    __tablename__ = 'word'

    # There is no __init__ for SQLAlchemy model classes! SQLAlchemy takes care of it
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(150), nullable=False)
    pinyin = db.Column(db.String(150), nullable=False)
    meaning = db.Column(db.String(300), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False, default=0.5)
    source_name = db.Column(db.String(200), nullable=True, default=None)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship('User', back_populates='words')
    sessions = db.relationship('SessionWord', back_populates='word')

    #TODO: extract this out to a function or config or something. feels like a smell
    @property
    def status(self):
        score = self.confidence_score if self.confidence_score is not None else 0.5
        if score > 0.9:
            return "Mastered"
        elif score > 0.7:
            return "Reviewing"
        elif score > 0.3:
            return "Learning"
        elif score >= 0:
            return "Needs Revision"
        else:
            return "Unknown"
    
    def __repr__(self):
        return f"{self.id} - {self.word} - {self.pinyin} - {self.meaning}"

    def format_data(self, viewer=None):
        # If no viewer or viewer is not the owner, return None (access denied at model level)
        if viewer is None or viewer.id != self.user_id:
            return None
        return {
            'id': self.id,
            'word': self.word,
            'pinyin': self.pinyin,
            'meaning': self.meaning,
            'confidence_score': self.confidence_score,
            'status': self.status,
            'source_name': self.source_name,
        }

    def is_owner(self, viewer) -> bool:
        """Check if viewer is the owner of this word"""
        if viewer is None:
            return False
        return viewer.id == self.user_id
    

    def update_confidence_score(self, new_value: float):
        if Word.is_valid_confidence_score(new_value):
            self.confidence_score = new_value
            return self
        else:
            raise ValueError("Confidence score invalid!")
        
    # Model owns all database update logic, not resource
    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def update(self):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def add_list(cls, list_of_instances):
        # if you want to add multiple instances at once, use class method for semantic sense
        try:
            db.session.add_all(list_of_instances)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def delete_all(cls, viewer):
        # delete all words for the logged in user
        try:
            db.session.query(Word).filter_by(user_id=viewer.id).delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    

    @classmethod
    def get_full_list(cls, viewer):
        # Returns a list of Word objects for a user
        return cls.query.filter_by(user_id=viewer.id).all()

    
    @classmethod
    def get_by_id(cls, id: int):
        # Returns a Word object
        return cls.query.filter_by(id = id).first()

    @classmethod
    def exists(cls, id: int) -> bool:
        return cls.query.filter_by(id=id).first() is not None

    @classmethod
    def is_valid_confidence_score(cls, confidence_score: float) -> bool:
        return 0 <= confidence_score <= 1
    


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200))
    preferred_name = db.Column(db.String(80))
    created_ds = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)

    words = db.relationship('Word', back_populates='user')
    sessions = db.relationship('UserSession', back_populates='user')

    def __repr__(self):
        return f"{self.id} - {self.preferred_name}"
    
    def format_data(self, viewer=None):
        # viewer should be the User object of the logged in user
        if viewer is None:
            return {
                'id': self.id
            } 

        if viewer.id == self.id or viewer.is_admin == True:
                return {
                    'id': self.id,
                    'username': self.username,
                    'preferred_name': self.preferred_name
                }
        else:
            return {
                'id': self.id
            } 

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def update(self):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def get_full_list(cls):
        # Returns a list of User objects
        return cls.query.all()
    
    @classmethod
    def get_by_id(cls, id: int):
        # Returns a User object
        return cls.query.filter_by(id = id).first()
    
    @classmethod
    def get_by_username(cls, username: str):
        # Returns a User object
        return cls.query.filter_by(username = username).first()

    @classmethod
    def exists(cls, id: int) -> bool:
        return cls.query.filter_by(id=id).first() is not None

    @classmethod
    def is_username_valid(cls, username: str) -> bool:
        if username is None:
            return False
        # Check if username already exists in database
        # use ilike for case INSENSITIVE match, also supports SQL % wildcard. filter_by is case sensitive
        existing_username = cls.query.filter(cls.username.ilike(username)).first()
        return existing_username is None
    
    @classmethod
    def is_email_valid(cls, email: str) -> bool:
        # Simplistic pattern matching to catch ill-formatted emails
        if type(email) != str:
            return False
        if email.count('@') != 1:
            return False
        
        local, domain = email.split("@")
        if not local or not domain:
            return False
        if "." not in domain:
            return False
        if domain.startswith(".") or domain.endswith("."):
            return False
        
        # Check if email already exists in database
        email_query = email.lower()
        existing_user = cls.query.filter(cls.email.ilike(email_query)).first()
        return existing_user is None
    

class UserSession(db.Model):
    __tablename__ = 'user_session'

    id = db.Column(db.Integer, primary_key=True)
    session_start_ds = db.Column(db.DateTime)
    session_end_ds = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship('User', back_populates='sessions')
    session_words = db.relationship('SessionWord', back_populates='user_session')

    def __repr__(self):
        return f"session {self.id} of user {self.user.preferred_name}"
    
    def format_data(self, viewer=None):
        # If no viewer, return None (access denied at model level)
        # Only owner or admin can see session data
        if viewer is None:
            return None
        if viewer.id != self.user_id and not viewer.is_admin:
            return None
        return {
            'id': self.id,
            'session_start_ds': self.session_start_ds,
            'session_end_ds': self.session_end_ds,
            'user_id': self.user_id
        }

    def is_owner(self, viewer) -> bool:
        """Check if viewer is the owner of this session"""
        if viewer is None:
            return False
        return viewer.id == self.user_id

    def can_view(self, viewer) -> bool:
        """Check if viewer can view this session (owner or admin)"""
        if viewer is None:
            return False
        return viewer.id == self.user_id or viewer.is_admin
    
    def is_new_session_end_valid(self, new_session_end: datetime):
        # Only allow session end ds to be updated if it is after start ds or previous end ds (in the case of reopening of session)
        if not self.session_end_ds:
            if new_session_end >= self.session_start_ds:
                return True
        else:
            if new_session_end >= self.session_end_ds:
                return True
        return False

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def update(self):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def get_full_list(cls):
        # Returns a list of User_Session objects
        return cls.query.all()
    
    @classmethod
    def get_by_id(cls, id: int):
        # Returns a User_Session object based on id search
        return cls.query.filter_by(id = id).first()

    @classmethod
    def exists(cls, id: int) -> bool:
        return cls.query.filter_by(id=id).first() is not None

    @classmethod
    def get_by_ds_range(cls, range_start=None, range_end=None):
        # Returns a User_Session object based on time range search
        return cls.query.filter(construct_date_range_filter(UserSession.session_start_ds, UserSession.session_end_ds, range_start, range_end)).all()


class SessionWord(db.Model):
    __tablename__ = 'session_word'

    word_id = db.Column(db.Integer, db.ForeignKey("word.id"))
    session_id = db.Column(db.Integer, db.ForeignKey("user_session.id"))
    session_word_load_ds = db.Column(db.DateTime)
    is_skipped = db.Column(db.Boolean, default=False)
    session_notes = db.Column(db.String(2000))

    __table_args__ = (
        db.PrimaryKeyConstraint('word_id', 'session_id'),
    )

    # Define relationships to access the related objects easily
    word = db.relationship('Word', back_populates='sessions')
    user_session = db.relationship('UserSession', back_populates='session_words')

    def __repr__(self):
        return f"word {self.word_id} in session {self.session_id}"
    
    def format_data(self, viewer=None):
        # Access control based on session ownership
        # SessionWord inherits access from its parent session
        if viewer is None:
            return None
        if not self.user_session.can_view(viewer):
            return None
        id_string = str(self.word_id) + '_' + str(self.session_id)
        return {
            'id': id_string,
            'is_skipped': self.is_skipped,
            'session_notes': self.session_notes
        }

    def is_owner(self, viewer) -> bool:
        """Check if viewer is the owner of this session word (via session ownership)"""
        if viewer is None:
            return False
        return self.user_session.is_owner(viewer)

    def can_view(self, viewer) -> bool:
        """Check if viewer can view this session word (owner or admin)"""
        if viewer is None:
            return False
        return self.user_session.can_view(viewer)

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def update(self):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def get_list_by_session_id(cls, session_id: int):
        # Returns a list of Session_Word objects
        return cls.query.filter_by(session_id=session_id).all()
    
    @classmethod
    def get_by_session_word_id(cls, word_id: int, session_id: int):
        # Returns a Session_Word object by composite key
        return cls.query.filter_by(word_id=word_id, session_id=session_id).first()

