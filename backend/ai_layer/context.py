# Define the context object for the agents & helper functions
from dataclasses import dataclass


@dataclass
class WordContext:
    word_id: int
    word: str
    pinyin: str
    meaning: str


@dataclass
class UserSessionContext:
    user_id: int
    session_id: int
    preferred_name: str
    current_word: WordContext | None
    session_word_dict: dict           # {word_id: status} -- 1=completed, -1=skipped, 0=active
    words_practiced: int              # words with >=1 attempt (completed)
    words_skipped: int                # words with 0 attempts (skipped)
    words_total: int
    session_complete: bool
    mem0_preferences: str | None      # stringified mem0 search results
    word_roster: list[WordContext]     # all session words in word_order
