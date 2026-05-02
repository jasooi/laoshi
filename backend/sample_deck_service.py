import csv
import os
import logging

from models import Deck, Word
from extensions import db

logger = logging.getLogger(__name__)

SAMPLE_DECK_NAME = "Software Engineering Vocabulary"
SAMPLE_DECK_DESCRIPTION = "Common Mandarin vocabulary used in software engineering contexts."
SAMPLE_DECK_LAOSHI_MESSAGE = "This is a sample deck to help you get started with Laoshi! You can delete or modify this deck as you please."


def get_sample_csv_path():
    """Return absolute path to the sample CSV file."""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(backend_dir, '..', 'sample_decks', 'swe_vocab_list.csv')
    normalized_path = os.path.normpath(csv_path)
    logger.info(f"Sample CSV path: backend_dir={backend_dir}, csv_path={normalized_path}")
    return normalized_path


def load_sample_words_from_csv():
    """Parse the sample CSV and return list of {word, pinyin, meaning} dicts."""
    csv_path = get_sample_csv_path()
    if not os.path.exists(csv_path):
        logger.error(f"Sample CSV not found at {csv_path} - seeding will be skipped!")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Files in parent dir: {os.listdir(os.path.dirname(csv_path)) if os.path.exists(os.path.dirname(csv_path)) else 'parent dir does not exist'}")
        return []

    words = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_text = row.get('Word', '').strip()
            pinyin = row.get('Pinyin', '').strip()
            meaning = row.get('Meaning', '').strip()
            if word_text and pinyin and meaning:
                words.append({'word': word_text, 'pinyin': pinyin, 'meaning': meaning})
    return words


def user_has_sample_deck(user_id):
    """Check if user already has the sample deck."""
    return Deck.query.filter_by(user_id=user_id, name=SAMPLE_DECK_NAME).first() is not None


def seed_sample_deck_for_user(user_id):
    """
    Create the sample deck with all words for the given user.
    Returns the created Deck, or None if seeding was skipped/failed.
    """
    if user_has_sample_deck(user_id):
        logger.info(f"User {user_id} already has sample deck, skipping.")
        return None

    try:
        words_data = load_sample_words_from_csv()
        if not words_data:
            logger.error(f"No words loaded from sample CSV for user {user_id}, skipping seed. Check if sample_decks/swe_vocab_list.csv exists in deployment.")
            return None

        deck = Deck(
            name=SAMPLE_DECK_NAME,
            description=SAMPLE_DECK_DESCRIPTION,
            laoshi_message=SAMPLE_DECK_LAOSHI_MESSAGE,
            user_id=user_id,
        )
        db.session.add(deck)
        db.session.flush()  # Get deck.id before inserting words

        word_objects = [
            Word(
                word=wd['word'],
                pinyin=wd['pinyin'],
                meaning=wd['meaning'],
                user_id=user_id,
                deck_id=deck.id,
                repetitions=0,
                interval_days=1,
                ease_factor=2.5,
            )
            for wd in words_data
        ]

        db.session.add_all(word_objects)
        db.session.commit()
        logger.info(f"Seeded sample deck (id={deck.id}) with {len(word_objects)} words for user {user_id}.")
        return deck
    except Exception:
        db.session.rollback()
        logger.exception(f"Failed to seed sample deck for user {user_id}.")
        return None
