"""
Progress Routes

Handles user progress tracking and statistics.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from ..mock_db import get_progress_collection, get_vocabulary_collection

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/progress/stats', methods=['GET'])
def get_progress_stats():
    """
    Get overall progress statistics.

    Returns:
    - wordsToday: Number of unique words practiced today
    - masteryProgress: Overall mastery percentage (0-100)
    - totalPracticed: Total words ever practiced
    - currentStreak: Current practice streak in days
    """
    vocab_collection = get_vocabulary_collection()
    progress_collection = get_progress_collection()

    # Get all vocabulary words
    all_words = vocab_collection.find()
    total_words = len(all_words)

    if total_words == 0:
        return jsonify({
            'wordsToday': 0,
            'masteryProgress': 0,
            'totalPracticed': 0,
            'currentStreak': 0,
            'totalWords': 0
        }), 200

    # Calculate words practiced today
    today = datetime.utcnow().date().isoformat()
    today_progress = progress_collection.find({'date': today})
    words_today = len(set(p.get('wordId') for p in today_progress))

    # Calculate mastery progress (average confidence score)
    total_confidence = sum(w.get('confidenceScore', 0) for w in all_words)
    mastery_progress = int((total_confidence / (total_words * 100)) * 100) if total_words > 0 else 0

    # Count words that have been practiced at least once
    practiced_words = [w for w in all_words if w.get('practiceCount', 0) > 0]
    total_practiced = len(practiced_words)

    # Calculate streak (simplified - just check consecutive days)
    streak = calculate_streak(progress_collection)

    return jsonify({
        'wordsToday': words_today,
        'masteryProgress': mastery_progress,
        'totalPracticed': total_practiced,
        'currentStreak': streak,
        'totalWords': total_words
    }), 200


@progress_bp.route('/progress/record', methods=['POST'])
def record_practice():
    """
    Record a practice session for a word.

    Expected JSON:
    - wordId: ID of the word practiced
    - score: Score from evaluation (0-100)
    - sentence: The sentence the user wrote
    - feedback: Feedback from the evaluator
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    word_id = data.get('wordId')
    score = data.get('score', 0)
    sentence = data.get('sentence', '')
    feedback = data.get('feedback', '')

    if not word_id:
        return jsonify({'error': 'wordId is required'}), 400

    vocab_collection = get_vocabulary_collection()
    progress_collection = get_progress_collection()

    # Check if word exists
    word = vocab_collection.find_one({'_id': word_id})
    if not word:
        return jsonify({'error': 'Word not found'}), 404

    # Record progress entry
    progress_entry = {
        'wordId': word_id,
        'word': word.get('word'),
        'date': datetime.utcnow().date().isoformat(),
        'timestamp': datetime.utcnow().isoformat(),
        'score': score,
        'sentence': sentence,
        'feedback': feedback
    }
    progress_collection.insert_one(progress_entry)

    # Update word confidence score and practice count
    current_confidence = word.get('confidenceScore', 0)
    practice_count = word.get('practiceCount', 0) + 1

    # Calculate new confidence score (weighted average)
    # More recent scores have higher weight
    weight_new = 0.4
    weight_old = 0.6
    new_confidence = int(current_confidence * weight_old + score * weight_new)
    new_confidence = max(0, min(100, new_confidence))  # Clamp to 0-100

    vocab_collection.update_one(
        {'_id': word_id},
        {'$set': {
            'confidenceScore': new_confidence,
            'practiceCount': practice_count,
            'lastPracticed': datetime.utcnow().isoformat()
        }}
    )

    return jsonify({
        'message': 'Practice recorded',
        'newConfidenceScore': new_confidence,
        'practiceCount': practice_count
    }), 200


@progress_bp.route('/progress/history', methods=['GET'])
def get_progress_history():
    """
    Get practice history.

    Query params:
    - wordId: Filter by specific word (optional)
    - days: Number of days to look back (default: 30)
    - limit: Maximum entries to return (default: 100)
    """
    progress_collection = get_progress_collection()

    word_id = request.args.get('wordId')
    days = int(request.args.get('days', 30))
    limit = int(request.args.get('limit', 100))

    # Build filter
    filter_query = {}

    if word_id:
        filter_query['wordId'] = word_id

    # Date filter
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    filter_query['date'] = {'$gte': cutoff_date}

    # Get progress entries
    entries = progress_collection.find(filter_query)

    # Sort by timestamp descending and limit
    entries = sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]

    return jsonify(entries), 200


@progress_bp.route('/progress/word/<word_id>', methods=['GET'])
def get_word_progress(word_id: str):
    """Get progress history for a specific word."""
    progress_collection = get_progress_collection()
    vocab_collection = get_vocabulary_collection()

    # Check if word exists
    word = vocab_collection.find_one({'_id': word_id})
    if not word:
        return jsonify({'error': 'Word not found'}), 404

    # Get all progress entries for this word
    entries = progress_collection.find({'wordId': word_id})
    entries = sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)

    return jsonify({
        'word': word,
        'history': entries,
        'totalPractices': len(entries)
    }), 200


def calculate_streak(progress_collection) -> int:
    """Calculate the current practice streak in days."""
    # Get all unique practice dates
    all_progress = progress_collection.find()
    dates = set(p.get('date') for p in all_progress if p.get('date'))

    if not dates:
        return 0

    # Sort dates in descending order
    sorted_dates = sorted(dates, reverse=True)

    # Check if practiced today or yesterday
    today = datetime.utcnow().date()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()

    if today_str not in dates and yesterday_str not in dates:
        return 0

    # Count consecutive days
    streak = 0
    current_date = today if today_str in dates else today - timedelta(days=1)

    while current_date.isoformat() in dates:
        streak += 1
        current_date -= timedelta(days=1)

    return streak
