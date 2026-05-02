# File containing all models for Flask SQLAlchemy
# 4 models to be defined: Word, Word_session, Session, User

from extensions import db
from datetime import datetime, date, timedelta, timezone
from utils import construct_date_range_filter
import math


# Define models
class Deck(db.Model):
    __tablename__ = 'deck'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    laoshi_message = db.Column(db.String(500), nullable=True)
    created_ds = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_ds = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', back_populates='decks')
    words = db.relationship('Word', back_populates='deck', cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', back_populates='deck')

    def format_data(self, viewer=None):
        if viewer is None or viewer.id != self.user_id:
            return None
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'laoshi_message': self.laoshi_message,
            'created_ds': self.created_ds.isoformat() if self.created_ds else None,
            'updated_ds': self.updated_ds.isoformat() if self.updated_ds else None,
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
            self.updated_ds = datetime.now(timezone.utc)
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

    @classmethod
    def get_by_id(cls, id: int):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def get_by_user_id(cls, user_id: int):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def exists(cls, id: int) -> bool:
        return cls.query.filter_by(id=id).first() is not None


class Word(db.Model):
    __tablename__ = 'word'

    # There is no __init__ for SQLAlchemy model classes! SQLAlchemy takes care of it
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(150), nullable=False)
    pinyin = db.Column(db.String(150), nullable=False)
    meaning = db.Column(db.String(300), nullable=False)
    notes = db.Column(db.String(200), nullable=True, default=None)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))

    # Deck relationship
    deck_id = db.Column(db.Integer, db.ForeignKey("deck.id", ondelete="CASCADE"), nullable=True)
    deck = db.relationship('Deck', back_populates='words')

    # SRS (Spaced Repetition System) fields
    repetitions = db.Column(db.Integer, default=0)
    interval_days = db.Column(db.Integer, default=1)
    ease_factor = db.Column(db.Float, default=2.5)
    next_review_date = db.Column(db.Date, nullable=True)

    # Mastery tracking
    last_quality = db.Column(db.Integer, nullable=True)
    marked_as_known = db.Column(db.Boolean, default=False)
    is_mastered = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='words')
    sessions = db.relationship('SessionWord', back_populates='word', cascade='all, delete')

    @property
    def srs_status(self):
        """Return SRS-based status for UI display."""
        if self.is_mastered:
            return "Mastered"
        elif self.next_review_date is None:
            return "New"
        else:
            return "In Review"
    
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
            'notes': self.notes,
            'deck_id': self.deck_id,
            # SRS fields
            'repetitions': self.repetitions,
            'interval_days': self.interval_days,
            'ease_factor': self.ease_factor,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            # Mastery fields
            'last_quality': self.last_quality,
            'marked_as_known': self.marked_as_known,
            'is_mastered': self.is_mastered,
            'srs_status': self.srs_status,
        }

    def update_mastery_status(self):
        """
        Update is_mastered based on last_quality and marked_as_known (Option B - Lenient).

        Logic:
        - Quality 5: Always mark as mastered
        - Quality 4: Preserve existing is_mastered state (don't demote easily)
        - Quality <= 3: Remove mastered status
        - marked_as_known: Always mark as mastered (user override)
        """
        if self.marked_as_known or self.last_quality == 5:
            self.is_mastered = True
        elif self.last_quality is not None and self.last_quality <= 3:
            self.is_mastered = False
        # Quality 4: preserve existing is_mastered state (no change)

    def is_owner(self, viewer) -> bool:
        """Check if viewer is the owner of this word"""
        if viewer is None:
            return False
        return viewer.id == self.user_id
    

    def update_srs(self, quality: int):
        """
        Update word SRS state using modified SM-2 algorithm.

        Args:
            quality: 0-5 rating from user self-assessment
        """
        # Fast-track perfect first attempts
        if self.repetitions == 0 and quality == 5:
            self.interval_days = 14
            self.repetitions = 2
            self.ease_factor = 2.5
        elif quality < 3:
            # Harsh reset on failure (fair since user controls quality)
            self.repetitions = 0
            self.interval_days = 1
        else:
            # Standard SM-2 progression with gentler early intervals
            if self.repetitions == 0:
                self.interval_days = 1
            elif self.repetitions == 1:
                self.interval_days = 3
            elif self.repetitions == 2:
                self.interval_days = 7
            else:
                new_interval = self.interval_days * self.ease_factor
                # Use ceil for intervals < 7 to prevent stuck at 1 day
                if new_interval < 7:
                    self.interval_days = math.ceil(new_interval)
                else:
                    self.interval_days = round(new_interval)

            self.repetitions += 1

        # Update ease factor (SM-2 formula)
        self.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        self.ease_factor = max(1.3, self.ease_factor)

        # Set next review date
        self.next_review_date = date.today() + timedelta(days=self.interval_days)

    def mark_as_mastered(self):
        """Fast-track word to mastered state with long interval."""
        self.marked_as_known = True
        self.last_quality = 5
        self.is_mastered = True

        # SRS fast-track
        self.repetitions = 5
        self.interval_days = 90
        self.ease_factor = 2.5
        self.next_review_date = date.today() + timedelta(days=90)

    def unmark_as_mastered(self):
        """Remove mastered status and recalculate based on last quality rating."""
        self.marked_as_known = False
        # Recalculate is_mastered based on last_quality
        self.update_mastery_status()
        
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
    def get_query_for_user(cls, viewer):
        """Returns a base query for a user's words (not yet executed)."""
        return cls.query.filter_by(user_id=viewer.id)

    @classmethod
    def get_by_id(cls, id: int):
        # Returns a Word object
        return cls.query.filter_by(id = id).first()

    @classmethod
    def exists(cls, id: int) -> bool:
        return cls.query.filter_by(id=id).first() is not None

    @classmethod
    def get_new_words(cls, deck_id: int, user_id: int, limit: int = None):
        """Get words that have never been reviewed (next_review_date IS NULL)."""
        query = cls.query.filter_by(
            deck_id=deck_id,
            user_id=user_id,
            next_review_date=None
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_due_words(cls, deck_id: int, user_id: int, limit: int = None):
        """Get words that are due for review (next_review_date <= today)."""
        today = date.today()
        query = cls.query.filter(
            cls.deck_id == deck_id,
            cls.user_id == user_id,
            cls.next_review_date <= today
        ).order_by(cls.next_review_date.asc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_future_words(cls, deck_id: int, user_id: int, limit: int = None):
        """Get words with future review dates, sorted by nearest date."""
        today = date.today()
        query = cls.query.filter(
            cls.deck_id == deck_id,
            cls.user_id == user_id,
            cls.next_review_date > today
        ).order_by(cls.next_review_date.asc())
        if limit:
            query = query.limit(limit)
        return query.all()
    


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200))
    created_ds = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)

    words = db.relationship('Word', back_populates='user', cascade='all, delete-orphan')
    decks = db.relationship('Deck', back_populates='user', cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    profile = db.relationship('UserProfile', uselist=False, back_populates='user', cascade='all, delete-orphan', lazy='joined')
    reset_tokens = db.relationship('PasswordResetToken', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        name = (self.profile.preferred_name if self.profile else None) or self.username
        return f"{self.id} - {name}"

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
                    'preferred_name': (self.profile.preferred_name if self.profile else None),
                    'onboarding_complete': (self.profile.onboarding_complete if self.profile else False),
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


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_name = db.Column(db.String(80), nullable=True)
    words_per_session = db.Column(db.Integer, nullable=True)
    encrypted_deepseek_api_key = db.Column(db.Text, nullable=True)
    encrypted_gemini_api_key = db.Column(db.Text, nullable=True)
    deepseek_key_version = db.Column(db.Integer, default=1)
    gemini_key_version = db.Column(db.Integer, default=1)
    report_card_feedback = db.Column(db.Text, nullable=True)
    current_streak = db.Column(db.Integer, default=0)
    last_practice_date = db.Column(db.Date, nullable=True)
    onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)
    created_ds = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_ds = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='profile')

    def format_settings(self):
        return {
            'preferred_name': self.preferred_name,
            'words_per_session': self.words_per_session,
            'has_deepseek_key': self.encrypted_deepseek_api_key is not None,
            'has_gemini_key': self.encrypted_gemini_api_key is not None,
            'onboarding_complete': self.onboarding_complete,
        }

    def increment_key_version(self, provider: str):
        """Increment the key version for the specified provider."""
        if provider == 'deepseek':
            self.deepseek_key_version += 1
        elif provider == 'gemini':
            self.gemini_key_version += 1
        else:
            raise ValueError(f"Invalid provider: {provider}")

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def update(self):
        try:
            self.updated_ds = datetime.now(timezone.utc)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).first()


class UserSession(db.Model):
    __tablename__ = 'user_session'

    id = db.Column(db.Integer, primary_key=True)
    session_start_ds = db.Column(db.DateTime)
    session_end_ds = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    deck_id = db.Column(db.Integer, db.ForeignKey("deck.id", ondelete="SET NULL"), nullable=True)
    summary_text = db.Column(db.Text, nullable=True)
    words_per_session = db.Column(db.Integer, nullable=False, default=10)

    user = db.relationship('User', back_populates='sessions')
    deck = db.relationship('Deck', back_populates='sessions')
    session_words = db.relationship('SessionWord', back_populates='user_session', cascade='all, delete')

    def __repr__(self):
        preferred_name = (self.user.profile.preferred_name if self.user.profile else None) or self.user.username
        return f"session {self.id} of user {preferred_name}"
    
    def format_data(self, viewer=None):
        # If no viewer, return None (access denied at model level)
        # Only owner or admin can see session data
        if viewer is None:
            return None
        if viewer.id != self.user_id and not viewer.is_admin:
            return None
        return {
            'id': self.id,
            'session_start_ds': self.session_start_ds.isoformat() if self.session_start_ds else None,
            'session_end_ds': self.session_end_ds.isoformat() if self.session_end_ds else None,
            'user_id': self.user_id,
            'deck_id': self.deck_id,
            'summary_text': self.summary_text,
            'words_per_session': self.words_per_session,
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

    word_id = db.Column(db.Integer, db.ForeignKey("word.id", ondelete="CASCADE"))
    session_id = db.Column(db.Integer, db.ForeignKey("user_session.id", ondelete="CASCADE"))
    session_word_load_ds = db.Column(db.DateTime)
    is_skipped = db.Column(db.Boolean, default=False)
    session_notes = db.Column(db.String(2000))
    word_order = db.Column(db.Integer, nullable=False, default=0)
    grammar_score = db.Column(db.Float, nullable=True)
    usage_score = db.Column(db.Float, nullable=True)
    naturalness_score = db.Column(db.Float, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)  # 0=pending, 1=completed, -1=skipped
    srs_snapshot = db.Column(db.JSON, nullable=True)  # Pre-rating SRS state for undo+redo

    __table_args__ = (
        db.PrimaryKeyConstraint('word_id', 'session_id'),
    )

    # Define relationships to access the related objects easily
    word = db.relationship('Word', back_populates='sessions')
    user_session = db.relationship('UserSession', back_populates='session_words')
    attempts = db.relationship('SessionWordAttempt', back_populates='session_word',
                               cascade='all, delete',
                               order_by='SessionWordAttempt.attempt_number')

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
            'word_id': self.word_id,
            'session_id': self.session_id,
            'word_order': self.word_order,
            'is_skipped': self.is_skipped,
            'status': self.status,
            'grammar_score': self.grammar_score,
            'usage_score': self.usage_score,
            'naturalness_score': self.naturalness_score,
            'is_correct': self.is_correct,
            'session_notes': self.session_notes,
            'srs_snapshot': self.srs_snapshot,
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


class SessionWordAttempt(db.Model):
    __tablename__ = 'session_word_attempt'

    attempt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word_id = db.Column(db.Integer, nullable=False)
    session_id = db.Column(db.Integer, nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)  # 1-indexed
    sentence = db.Column(db.Text, nullable=False)
    grammar_score = db.Column(db.Float, nullable=True)
    usage_score = db.Column(db.Float, nullable=True)
    naturalness_score = db.Column(db.Float, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    feedback_text = db.Column(db.Text, nullable=True)
    created_ds = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['word_id', 'session_id'],
            ['session_word.word_id', 'session_word.session_id'],
            ondelete="CASCADE",
        ),
    )

    session_word = db.relationship('SessionWord', back_populates='attempts')

    def __repr__(self):
        return f"attempt {self.attempt_id} for word {self.word_id} in session {self.session_id}"

    def format_data(self):
        return {
            'attempt_id': self.attempt_id,
            'word_id': self.word_id,
            'session_id': self.session_id,
            'attempt_number': self.attempt_number,
            'sentence': self.sentence,
            'grammar_score': self.grammar_score,
            'usage_score': self.usage_score,
            'naturalness_score': self.naturalness_score,
            'is_correct': self.is_correct,
            'feedback_text': self.feedback_text,
            'created_ds': self.created_ds.isoformat() if self.created_ds else None,
        }

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def get_by_word_session(cls, word_id: int, session_id: int):
        """Return all attempts for a specific word in a specific session, ordered by attempt_number."""
        return cls.query.filter_by(word_id=word_id, session_id=session_id).order_by(cls.attempt_number).all()

    @classmethod
    def count_by_word_session(cls, word_id: int, session_id: int) -> int:
        """Return the number of attempts for a specific word in a session."""
        return cls.query.filter_by(word_id=word_id, session_id=session_id).count()


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_ds = db.Column(db.DateTime, nullable=False)

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def is_blocklisted(cls, jti: str) -> bool:
        return cls.query.filter_by(jti=jti).first() is not None


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_ds = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_ds = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User')

    def is_expired(self):
        now = datetime.now(timezone.utc)
        # DB may return naive datetime — assume UTC
        expires = self.expires_ds if self.expires_ds.tzinfo else self.expires_ds.replace(tzinfo=timezone.utc)
        return now > expires

    def is_valid(self):
        return not self.used and not self.is_expired()

    def add(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

