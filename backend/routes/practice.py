"""
Practice Routes

Handles practice session management and word selection.
"""

import random
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..mock_db import get_vocabulary_collection, get_progress_collection, get_settings_collection

practice_bp = Blueprint('practice', __name__)

# Default settings
DEFAULT_WORDS_TO_PRACTICE = 10


@practice_bp.route('/practice/next-word', methods=['GET'])
def get_next_word():
    """
    Get the next word to practice based on the confidence algorithm.

    The algorithm prioritizes:
    1. Words with lower confidence scores
    2. Words that haven't been practiced recently
    3. Words that haven't been practiced at all

    Query params:
    - exclude: Comma-separated list of word IDs to exclude (already practiced this session)
    """
    vocab_collection = get_vocabulary_collection()

    # Get words to exclude
    exclude_str = request.args.get('exclude', '')
    exclude_ids = [id.strip() for id in exclude_str.split(',') if id.strip()]

    # Get all words
    all_words = vocab_collection.find()

    if not all_words:
        return jsonify({'error': 'No vocabulary words available'}), 404

    # Filter out excluded words
    available_words = [w for w in all_words if w['_id'] not in exclude_ids]

    if not available_words:
        return jsonify({'error': 'No more words available for practice'}), 404

    # Select word based on weighted algorithm
    selected_word = select_word_by_confidence(available_words)

    return jsonify(selected_word), 200


@practice_bp.route('/practice/evaluate', methods=['POST'])
def evaluate_sentence():
    """
    Evaluate a sentence for a given word.

    Expected JSON:
    - wordId: ID of the word being practiced
    - sentence: The sentence the user wrote

    Returns:
    - score: Evaluation score (0-100)
    - feedback: Feedback message
    - corrections: List of corrections (if any)
    - exampleSentences: Example sentences using the word

    Note: In Phase 1, this is a simplified evaluation.
    In production, this would call the Gemini Flash API.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    word_id = data.get('wordId')
    sentence = data.get('sentence', '').strip()

    if not word_id:
        return jsonify({'error': 'wordId is required'}), 400

    if not sentence:
        return jsonify({'error': 'sentence is required'}), 400

    vocab_collection = get_vocabulary_collection()

    # Get the word
    word = vocab_collection.find_one({'_id': word_id})
    if not word:
        return jsonify({'error': 'Word not found'}), 404

    target_word = word.get('word', '')

    # Simplified evaluation (mock)
    # In production, this would call Gemini Flash API
    evaluation = mock_evaluate_sentence(sentence, target_word, word)

    # Record the practice
    from .progress import record_practice_internal
    record_practice_internal(
        word_id=word_id,
        word=word,
        score=evaluation['score'],
        sentence=sentence,
        feedback=evaluation['feedback']
    )

    return jsonify(evaluation), 200


@practice_bp.route('/practice/skip', methods=['POST'])
def skip_word():
    """
    Skip a word during practice session.

    Expected JSON:
    - wordId: ID of the word to skip
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    word_id = data.get('wordId')

    if not word_id:
        return jsonify({'error': 'wordId is required'}), 400

    vocab_collection = get_vocabulary_collection()

    # Check if word exists
    word = vocab_collection.find_one({'_id': word_id})
    if not word:
        return jsonify({'error': 'Word not found'}), 404

    # For now, just return success
    # In the future, we might track skipped words separately

    return jsonify({
        'message': 'Word skipped',
        'wordId': word_id
    }), 200


@practice_bp.route('/practice/session-summary', methods=['POST'])
def get_session_summary():
    """
    Generate a summary for the practice session.

    Expected JSON:
    - practicedWordIds: List of word IDs practiced in this session
    - scores: List of scores for each word

    Returns:
    - summary: Teacher-style summary
    - strengths: 2 strengths identified
    - improvements: 1 area for improvement

    Note: In production, this would call Gemini Flash API.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    practiced_ids = data.get('practicedWordIds', [])
    scores = data.get('scores', [])

    if not practiced_ids:
        return jsonify({'error': 'No practiced words provided'}), 400

    # Calculate statistics
    avg_score = sum(scores) / len(scores) if scores else 0
    total_words = len(practiced_ids)

    # Generate mock summary (in production, call Gemini Flash)
    summary = generate_mock_summary(avg_score, total_words)

    return jsonify(summary), 200


@practice_bp.route('/practice/settings', methods=['GET'])
def get_practice_settings():
    """Get practice session settings."""
    settings_collection = get_settings_collection()

    settings = settings_collection.find_one({'type': 'practice'})

    if not settings:
        # Return defaults
        return jsonify({
            'wordsToPractice': DEFAULT_WORDS_TO_PRACTICE
        }), 200

    return jsonify({
        'wordsToPractice': settings.get('wordsToPractice', DEFAULT_WORDS_TO_PRACTICE)
    }), 200


@practice_bp.route('/practice/settings', methods=['PUT'])
def update_practice_settings():
    """Update practice session settings."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    settings_collection = get_settings_collection()

    words_to_practice = data.get('wordsToPractice', DEFAULT_WORDS_TO_PRACTICE)

    # Validate
    if not isinstance(words_to_practice, int) or words_to_practice < 1:
        return jsonify({'error': 'wordsToPractice must be a positive integer'}), 400

    if words_to_practice > 100:
        return jsonify({'error': 'wordsToPractice cannot exceed 100'}), 400

    # Update or create settings
    existing = settings_collection.find_one({'type': 'practice'})

    if existing:
        settings_collection.update_one(
            {'type': 'practice'},
            {'$set': {'wordsToPractice': words_to_practice}}
        )
    else:
        settings_collection.insert_one({
            'type': 'practice',
            'wordsToPractice': words_to_practice
        })

    return jsonify({
        'message': 'Settings updated',
        'wordsToPractice': words_to_practice
    }), 200


def select_word_by_confidence(words: list) -> dict:
    """
    Select a word based on confidence-weighted algorithm.

    Words with lower confidence scores have higher probability of being selected.
    """
    if not words:
        return None

    # Calculate weights (inverse of confidence)
    # Words with 0 confidence get highest weight
    weights = []
    for word in words:
        confidence = word.get('confidenceScore', 0)
        # Weight formula: lower confidence = higher weight
        # Add bonus for unpracticed words
        practice_count = word.get('practiceCount', 0)

        if practice_count == 0:
            weight = 100  # Highest priority for new words
        else:
            weight = max(1, 100 - confidence)

        weights.append(weight)

    # Weighted random selection
    total_weight = sum(weights)
    if total_weight == 0:
        return random.choice(words)

    r = random.uniform(0, total_weight)
    cumulative = 0

    for word, weight in zip(words, weights):
        cumulative += weight
        if r <= cumulative:
            return word

    return words[-1]  # Fallback


def mock_evaluate_sentence(sentence: str, target_word: str, word_data: dict) -> dict:
    """
    Mock sentence evaluation.

    In production, this would call the Gemini Flash API.
    """
    # Check if the target word is in the sentence
    word_used = target_word in sentence

    # Basic scoring
    if not word_used:
        score = 30
        feedback = f"请在句子中使用'{target_word}'这个词。Try using '{target_word}' in your sentence."
    elif len(sentence) < 5:
        score = 50
        feedback = "句子有点短。Try making a longer, more complete sentence."
    elif len(sentence) < 10:
        score = 70
        feedback = f"不错！Good job using '{target_word}'! Try adding more context next time."
    else:
        score = 85
        feedback = f"很好！Great sentence using '{target_word}'! Keep up the good work!"

    # Generate example sentences (mock)
    pinyin = word_data.get('pinyin', '')
    definition = word_data.get('definition', '')

    example_sentences = [
        f"Example: 我今天学了'{target_word}'这个词。",
        f"Example: '{target_word}'的意思是'{definition}'。"
    ]

    return {
        'score': score,
        'feedback': feedback,
        'wordUsed': word_used,
        'corrections': [],
        'exampleSentences': example_sentences,
        'grammarNotes': []
    }


def generate_mock_summary(avg_score: float, total_words: int) -> dict:
    """
    Generate a mock practice session summary.

    In production, this would call the Gemini Flash API.
    """
    # Determine performance level
    if avg_score >= 80:
        performance = 'excellent'
        encouragement = "Outstanding work today! 太棒了！"
        strengths = [
            "Excellent vocabulary usage in context",
            "Good sentence structure and complexity"
        ]
        improvement = "Try incorporating more advanced grammar patterns"
    elif avg_score >= 60:
        performance = 'good'
        encouragement = "Good progress today! 加油！"
        strengths = [
            "Consistent practice effort",
            "Improving word recognition"
        ]
        improvement = "Focus on using words in more varied contexts"
    else:
        performance = 'developing'
        encouragement = "Keep practicing! 继续努力！"
        strengths = [
            "Taking time to learn new words",
            "Engaging with the practice material"
        ]
        improvement = "Review the words with lower scores before next session"

    return {
        'performance': performance,
        'averageScore': round(avg_score, 1),
        'totalWordsPracticed': total_words,
        'encouragement': encouragement,
        'strengths': strengths,
        'improvement': improvement,
        'nextSteps': f"You practiced {total_words} words. Great job maintaining your study habit!"
    }


def record_practice_internal(word_id: str, word: dict, score: int, sentence: str, feedback: str):
    """Internal function to record practice (called from evaluate_sentence)."""
    from ..mock_db import get_progress_collection, get_vocabulary_collection

    progress_collection = get_progress_collection()
    vocab_collection = get_vocabulary_collection()

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

    # Calculate new confidence score
    weight_new = 0.4
    weight_old = 0.6
    new_confidence = int(current_confidence * weight_old + score * weight_new)
    new_confidence = max(0, min(100, new_confidence))

    vocab_collection.update_one(
        {'_id': word_id},
        {'$set': {
            'confidenceScore': new_confidence,
            'practiceCount': practice_count,
            'lastPracticed': datetime.utcnow().isoformat()
        }}
    )
