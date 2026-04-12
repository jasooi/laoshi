"""
Deck API Resources
Handles deck management, word operations within decks, and deck combining.
"""

from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, select
from datetime import date

from extensions import db
from models import Deck, Word, User
from utils import paginate_query

deck_bp = Blueprint('deck_bp', __name__)


def get_current_user():
    """Get the current authenticated user."""
    user_id = get_jwt_identity()
    return User.get_by_id(user_id)


def compute_deck_stats(deck_id):
    """
    Compute deck statistics using SQLAlchemy subqueries to avoid N+1.
    Returns dict with word_count, mastered_count, mastery_percentage, last_practiced_at.
    """
    # Word count subquery
    word_count_sq = (
        select(func.count(Word.id))
        .where(Word.deck_id == deck_id)
        .scalar_subquery()
    )

    # Mastered count subquery
    mastered_count_sq = (
        select(func.count(Word.id))
        .where(Word.deck_id == deck_id, Word.is_mastered == True)
        .scalar_subquery()
    )

    # Practiced count subquery (words that have been reviewed at least once)
    practiced_count_sq = (
        select(func.count(Word.id))
        .where(Word.deck_id == deck_id, Word.last_quality.isnot(None))
        .scalar_subquery()
    )

    # Last practiced at subquery (from UserSession)
    from models import UserSession
    last_practiced_sq = (
        select(func.max(UserSession.session_end_ds))
        .where(UserSession.deck_id == deck_id)
        .scalar_subquery()
    )

    # Execute all stats in a single query
    result = db.session.execute(
        select(
            word_count_sq.label('word_count'),
            mastered_count_sq.label('mastered_count'),
            practiced_count_sq.label('practiced_count'),
            last_practiced_sq.label('last_practiced_at')
        )
    ).first()

    word_count = result.word_count or 0
    mastered_count = result.mastered_count or 0
    practiced_count = result.practiced_count or 0
    mastery_percentage = round((mastered_count / word_count) * 100) if word_count > 0 else 0

    return {
        'word_count': word_count,
        'mastered_count': mastered_count,
        'practiced_count': practiced_count,
        'mastery_percentage': mastery_percentage,
        'last_practiced_at': result.last_practiced_at.isoformat() if result.last_practiced_at else None,
    }


@deck_bp.route('/decks', methods=['GET'])
@jwt_required()
def get_decks():
    """Get all decks for the current user with computed stats."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Get all decks for user
    decks = Deck.get_by_user_id(user.id)

    # Build response with stats for each deck
    decks_data = []
    for deck in decks:
        deck_data = deck.format_data(viewer=user)
        if deck_data:
            stats = compute_deck_stats(deck.id)
            deck_data.update(stats)
            decks_data.append(deck_data)

    # Sort by reverse recency (least recently practiced first, nulls first)
    decks_data.sort(key=lambda d: (d['last_practiced_at'] is not None, d['last_practiced_at'] or ''))

    return jsonify({'decks': decks_data}), 200


@deck_bp.route('/decks', methods=['POST'])
@jwt_required()
def create_deck():
    """Create a new empty deck."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Deck name is required'}), 400

    if len(name) > 200:
        return jsonify({'error': 'Deck name must be 200 characters or less'}), 400

    description = data.get('description', '').strip()
    if description and len(description) > 500:
        return jsonify({'error': 'Description must be 500 characters or less'}), 400

    deck = Deck(
        name=name,
        description=description if description else None,
        user_id=user.id
    )
    deck.add()

    deck_data = deck.format_data(viewer=user)
    stats = compute_deck_stats(deck.id)
    deck_data.update(stats)

    return jsonify(deck_data), 201


@deck_bp.route('/decks/<int:deck_id>', methods=['GET'])
@jwt_required()
def get_deck(deck_id):
    """Get a specific deck with stats."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user.id:
        return jsonify({'error': 'Deck not found'}), 404

    deck_data = deck.format_data(viewer=user)
    stats = compute_deck_stats(deck.id)
    deck_data.update(stats)

    return jsonify(deck_data), 200


@deck_bp.route('/decks/<int:deck_id>', methods=['PUT'])
@jwt_required()
def update_deck(deck_id):
    """Update deck name and/or description."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user.id:
        return jsonify({'error': 'Deck not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name')
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({'error': 'Deck name cannot be empty'}), 400
        if len(name) > 200:
            return jsonify({'error': 'Deck name must be 200 characters or less'}), 400
        deck.name = name

    description = data.get('description')
    if description is not None:
        description = description.strip()
        if description and len(description) > 500:
            return jsonify({'error': 'Description must be 500 characters or less'}), 400
        deck.description = description if description else None

    deck.update()

    deck_data = deck.format_data(viewer=user)
    stats = compute_deck_stats(deck.id)
    deck_data.update(stats)

    return jsonify(deck_data), 200


@deck_bp.route('/decks/<int:deck_id>', methods=['DELETE'])
@jwt_required()
def delete_deck(deck_id):
    """Delete a deck and all its words (cascade delete)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user.id:
        return jsonify({'error': 'Deck not found'}), 404

    deck.delete()

    return jsonify({}), 200


@deck_bp.route('/decks/<int:deck_id>/words', methods=['GET'])
@jwt_required()
def get_deck_words(deck_id):
    """Get paginated words for a specific deck."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user.id:
        return jsonify({'error': 'Deck not found'}), 404

    # Get query parameters for pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'word')
    sort_order = request.args.get('sort_order', 'asc')

    # Base query for words in this deck
    query = Word.query.filter_by(deck_id=deck_id, user_id=user.id)

    # Apply search filter
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Word.word.ilike(search_pattern),
                Word.pinyin.ilike(search_pattern),
                Word.meaning.ilike(search_pattern)
            )
        )

    # Apply sorting
    valid_sort_columns = ['word', 'pinyin', 'meaning', 'next_review_date', 'is_mastered']
    if sort_by not in valid_sort_columns:
        sort_by = 'word'

    sort_column = getattr(Word, sort_by)
    if sort_order == 'desc':
        sort_column = sort_column.desc()

    query = query.order_by(sort_column)

    # Paginate
    items, pagination = paginate_query(query, page, per_page)

    result = {
        'data': [word.format_data(viewer=user) for word in items],
        'pagination': pagination,
    }

    return jsonify(result), 200


@deck_bp.route('/decks/<int:deck_id>/words', methods=['POST'])
@jwt_required()
def add_words_to_deck(deck_id):
    """Add words to a deck (bulk create)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user.id:
        return jsonify({'error': 'Deck not found'}), 404

    data = request.get_json()
    if not data or 'words' not in data:
        return jsonify({'error': 'No words provided'}), 400

    words_data = data['words']
    if not isinstance(words_data, list) or len(words_data) == 0:
        return jsonify({'error': 'Words must be a non-empty list'}), 400

    created_words = []
    errors = []

    for idx, word_data in enumerate(words_data):
        word_text = word_data.get('word', '').strip()
        pinyin = word_data.get('pinyin', '').strip()
        meaning = word_data.get('meaning', '').strip()
        notes = word_data.get('notes', '').strip() or None

        if not word_text or not pinyin or not meaning:
            errors.append(f'Word at index {idx}: word, pinyin, and meaning are required')
            continue

        word = Word(
            word=word_text,
            pinyin=pinyin,
            meaning=meaning,
            notes=notes,
            user_id=user.id,
            deck_id=deck_id,
            # SRS fields use defaults
            repetitions=0,
            interval_days=1,
            ease_factor=2.5,
            next_review_date=None,
            last_quality=None,
            marked_as_known=False,
            is_mastered=False,
        )
        db.session.add(word)
        created_words.append(word)

    if errors:
        db.session.rollback()
        return jsonify({'error': 'Validation errors', 'details': errors}), 400

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create words', 'message': str(e)}), 500

    return jsonify({
        'created': [word.format_data(viewer=user) for word in created_words]
    }), 201


@deck_bp.route('/decks/combine', methods=['POST'])
@jwt_required()
def combine_decks():
    """Combine multiple decks into a new deck (words are copied)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Deck name is required'}), 400

    if len(name) > 200:
        return jsonify({'error': 'Deck name must be 200 characters or less'}), 400

    description = data.get('description', '').strip()
    if description and len(description) > 500:
        return jsonify({'error': 'Description must be 500 characters or less'}), 400

    source_deck_ids = data.get('source_deck_ids', [])
    if not isinstance(source_deck_ids, list) or len(source_deck_ids) == 0:
        return jsonify({'error': 'source_deck_ids must be a non-empty list'}), 400

    # Verify all source decks exist and belong to user
    source_decks = []
    for deck_id in source_deck_ids:
        deck = Deck.get_by_id(deck_id)
        if not deck or deck.user_id != user.id:
            return jsonify({'error': f'Source deck not found: {deck_id}'}), 404
        source_decks.append(deck)

    # Create new deck
    new_deck = Deck(
        name=name,
        description=description if description else None,
        user_id=user.id
    )
    db.session.add(new_deck)
    db.session.flush()  # Get the deck ID

    # Copy all words from source decks
    words_copied = 0
    for source_deck in source_decks:
        source_words = Word.query.filter_by(deck_id=source_deck.id, user_id=user.id).all()
        for source_word in source_words:
            new_word = Word(
                word=source_word.word,
                pinyin=source_word.pinyin,
                meaning=source_word.meaning,
                notes=source_word.notes,
                user_id=user.id,
                deck_id=new_deck.id,
                # Copy SRS state
                repetitions=source_word.repetitions,
                interval_days=source_word.interval_days,
                ease_factor=source_word.ease_factor,
                next_review_date=source_word.next_review_date,
                last_quality=source_word.last_quality,
                marked_as_known=source_word.marked_as_known,
                is_mastered=source_word.is_mastered,
            )
            db.session.add(new_word)
            words_copied += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to combine decks', 'message': str(e)}), 500

    deck_data = new_deck.format_data(viewer=user)
    stats = compute_deck_stats(new_deck.id)
    deck_data.update(stats)
    deck_data['words_copied'] = words_copied

    return jsonify(deck_data), 201
