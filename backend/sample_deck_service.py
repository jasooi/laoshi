import csv
import os
import logging

from models import Deck, Word
from extensions import db

logger = logging.getLogger(__name__)

SAMPLE_DECK_CONFIG = {
    'ZH': {
        'env_var': 'ZH_SAMPLE_DECK_FILE',
        'default_file': 'swe_vocab_list.csv',
        'name': 'Software Engineering Vocabulary',
        'description': 'Common Mandarin vocabulary used in software engineering contexts.',
        'laoshi_message': 'This is a sample deck to help you get started with Laoshi! You can delete or modify this deck as you please.',
    },
    'JP': {
        'env_var': 'JP_SAMPLE_DECK_FILE',
        'default_file': 'jp_sample_vocab_list.csv',
        'name': 'Japanese Starter Vocabulary',
        'description': 'Common Japanese vocabulary to get you started with Laoshi.',
        'laoshi_message': 'This is a sample Japanese deck. Practice forming sentences!',
    },
}


def get_sample_csv_path(language='ZH'):
    """Return absolute path to the sample CSV file for the given language."""
    config = SAMPLE_DECK_CONFIG[language]
    csv_filename = os.getenv(config['env_var'], config['default_file'])
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(backend_dir, 'sample_decks', csv_filename)
    normalized_path = os.path.normpath(csv_path)
    logger.info(f"Sample CSV path for {language}: {normalized_path}")
    return normalized_path


def load_sample_words_from_csv(language='ZH'):
    """Parse the sample CSV and return list of {word, reading, meaning} dicts."""
    csv_path = get_sample_csv_path(language)
    if not os.path.exists(csv_path):
        logger.info(f"Sample CSV for {language} not found at {csv_path} - skipping.")
        return []

    words = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_text = row.get('Word', '').strip()
            reading = (row.get('Reading', '') or row.get('Pinyin', '')).strip()
            meaning = row.get('Meaning', '').strip()
            if word_text and reading and meaning:
                words.append({'word': word_text, 'reading': reading, 'meaning': meaning})
    return words


def user_has_sample_deck(user_id, language='ZH'):
    """Check if user already has the sample deck for the given language."""
    config = SAMPLE_DECK_CONFIG[language]
    return Deck.query.filter_by(user_id=user_id, name=config['name']).first() is not None


def seed_sample_deck_for_user(user_id, language='ZH'):
    """
    Create the sample deck with all words for the given user and language.
    Returns the created Deck, or None if seeding was skipped/failed.
    """
    config = SAMPLE_DECK_CONFIG[language]

    if user_has_sample_deck(user_id, language):
        logger.info(f"User {user_id} already has {language} sample deck, skipping.")
        return None

    try:
        words_data = load_sample_words_from_csv(language)
        if not words_data:
            logger.info(f"No words loaded from {language} sample CSV for user {user_id}, skipping seed.")
            return None

        deck = Deck(
            name=config['name'],
            description=config['description'],
            laoshi_message=config['laoshi_message'],
            user_id=user_id,
            language=language,
        )
        db.session.add(deck)
        db.session.flush()  # Get deck.id before inserting words

        word_objects = [
            Word(
                word=wd['word'],
                reading=wd['reading'],
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
        logger.info(f"Seeded {language} sample deck (id={deck.id}) with {len(word_objects)} words for user {user_id}.")
        return deck
    except Exception:
        db.session.rollback()
        logger.exception(f"Failed to seed {language} sample deck for user {user_id}.")
        return None
