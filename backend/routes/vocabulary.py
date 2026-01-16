"""
Vocabulary Routes

Handles vocabulary CRUD operations and CSV import functionality.
"""

import csv
import io
from flask import Blueprint, request, jsonify
from ..mock_db import get_vocabulary_collection, get_sources_collection

vocabulary_bp = Blueprint('vocabulary', __name__)

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@vocabulary_bp.route('/vocabulary', methods=['GET'])
def get_all_vocabulary():
    """Get all vocabulary words."""
    vocab_collection = get_vocabulary_collection()
    words = vocab_collection.find()
    return jsonify(words), 200


@vocabulary_bp.route('/vocabulary/<word_id>', methods=['GET'])
def get_vocabulary_word(word_id: str):
    """Get a single vocabulary word by ID."""
    vocab_collection = get_vocabulary_collection()
    word = vocab_collection.find_one({'_id': word_id})

    if not word:
        return jsonify({'error': 'Word not found'}), 404

    return jsonify(word), 200


@vocabulary_bp.route('/vocabulary', methods=['POST'])
def add_vocabulary_word():
    """Add a single vocabulary word manually."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['word', 'pinyin', 'definition']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    vocab_collection = get_vocabulary_collection()

    # Check for duplicates
    existing = vocab_collection.find_one({'word': data['word']})
    if existing:
        return jsonify({'error': 'Word already exists', 'existing': existing}), 409

    new_word = {
        'word': data['word'].strip(),
        'pinyin': data['pinyin'].strip(),
        'definition': data['definition'].strip(),
        'partOfSpeech': data.get('partOfSpeech', '').strip(),
        'sourceName': data.get('sourceName', 'Manual Entry'),
        'sourceId': data.get('sourceId', None),
        'confidenceScore': 0,
        'practiceCount': 0,
        'lastPracticed': None
    }

    result = vocab_collection.insert_one(new_word)
    new_word['_id'] = result['inserted_id']

    return jsonify(new_word), 201


@vocabulary_bp.route('/vocabulary/<word_id>', methods=['PUT'])
def update_vocabulary_word(word_id: str):
    """Update a vocabulary word."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    vocab_collection = get_vocabulary_collection()

    # Check if word exists
    existing = vocab_collection.find_one({'_id': word_id})
    if not existing:
        return jsonify({'error': 'Word not found'}), 404

    # Build update object
    update_fields = {}
    allowed_fields = ['word', 'pinyin', 'definition', 'partOfSpeech', 'sourceName']

    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field].strip() if isinstance(data[field], str) else data[field]

    if not update_fields:
        return jsonify({'error': 'No valid fields to update'}), 400

    result = vocab_collection.update_one({'_id': word_id}, {'$set': update_fields})

    if result['modified_count'] > 0:
        updated_word = vocab_collection.find_one({'_id': word_id})
        return jsonify(updated_word), 200

    return jsonify({'error': 'Update failed'}), 500


@vocabulary_bp.route('/vocabulary/<word_id>', methods=['DELETE'])
def delete_vocabulary_word(word_id: str):
    """Delete a vocabulary word."""
    vocab_collection = get_vocabulary_collection()

    result = vocab_collection.delete_one({'_id': word_id})

    if result['deleted_count'] > 0:
        return jsonify({'message': 'Word deleted successfully'}), 200

    return jsonify({'error': 'Word not found'}), 404


@vocabulary_bp.route('/vocabulary/import', methods=['POST'])
def import_vocabulary():
    """
    Import vocabulary from a CSV file.

    Expected form data:
    - file: CSV file (max 10MB)
    - sourceName: Name for this vocabulary source

    Expected CSV columns:
    - Word (or word): Chinese word (required)
    - Pinyin (or pinyin): Pinyin pronunciation (required)
    - Meaning (or definition): English meaning (required)
    - partOfSpeech: Part of speech (optional)
    """
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file extension
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files are accepted'}), 400

    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Seek back to start

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': f'File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024*1024)}MB)'}), 400

    # Get source name
    source_name = request.form.get('sourceName', 'Imported Vocabulary')
    if not source_name.strip():
        source_name = 'Imported Vocabulary'

    # Create vocabulary source entry
    sources_collection = get_sources_collection()
    source_doc = {
        'name': source_name.strip(),
        'filename': file.filename,
        'wordCount': 0
    }
    source_result = sources_collection.insert_one(source_doc)
    source_id = source_result['inserted_id']

    # Parse CSV
    try:
        # Read file content and decode
        content = file.read()

        # Try UTF-8 first, fallback to latin-1
        try:
            text_content = content.decode('utf-8-sig')  # utf-8-sig handles BOM
        except UnicodeDecodeError:
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = content.decode('latin-1')

        # Parse CSV
        reader = csv.DictReader(io.StringIO(text_content))

        # Normalize column names (case-insensitive)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return jsonify({'error': 'CSV file is empty or has no headers'}), 400

        # Create column mapping (lowercase -> actual)
        column_map = {name.lower().strip(): name for name in fieldnames}

        # Check for required columns
        word_col = column_map.get('word')
        pinyin_col = column_map.get('pinyin')
        meaning_col = column_map.get('meaning') or column_map.get('definition')
        pos_col = column_map.get('partofspeech') or column_map.get('part_of_speech')

        if not word_col:
            return jsonify({'error': 'Missing required column: Word'}), 400
        if not pinyin_col:
            return jsonify({'error': 'Missing required column: Pinyin'}), 400
        if not meaning_col:
            return jsonify({'error': 'Missing required column: Meaning or Definition'}), 400

        # Process rows
        vocab_collection = get_vocabulary_collection()

        successful = 0
        duplicates = 0
        failed = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                word = row.get(word_col, '').strip()
                pinyin = row.get(pinyin_col, '').strip()
                meaning = row.get(meaning_col, '').strip()
                part_of_speech = row.get(pos_col, '').strip() if pos_col else ''

                # Validate required fields
                if not word:
                    errors.append(f'Row {row_num}: Missing word')
                    failed += 1
                    continue
                if not pinyin:
                    errors.append(f'Row {row_num}: Missing pinyin for "{word}"')
                    failed += 1
                    continue
                if not meaning:
                    errors.append(f'Row {row_num}: Missing meaning for "{word}"')
                    failed += 1
                    continue

                # Check for duplicates
                existing = vocab_collection.find_one({'word': word})
                if existing:
                    duplicates += 1
                    continue

                # Insert word
                new_word = {
                    'word': word,
                    'pinyin': pinyin,
                    'definition': meaning,
                    'partOfSpeech': part_of_speech,
                    'sourceName': source_name.strip(),
                    'sourceId': source_id,
                    'confidenceScore': 0,
                    'practiceCount': 0,
                    'lastPracticed': None
                }

                vocab_collection.insert_one(new_word)
                successful += 1

            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
                failed += 1

        # Update source word count
        sources_collection.update_one(
            {'_id': source_id},
            {'$set': {'wordCount': successful}}
        )

        return jsonify({
            'message': 'Import completed',
            'sourceId': source_id,
            'sourceName': source_name.strip(),
            'successful': successful,
            'duplicates': duplicates,
            'failed': failed,
            'errors': errors[:10] if errors else []  # Return first 10 errors
        }), 200

    except csv.Error as e:
        return jsonify({'error': f'CSV parsing error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


@vocabulary_bp.route('/vocabulary/sources', methods=['GET'])
def get_vocabulary_sources():
    """Get all vocabulary sources."""
    sources_collection = get_sources_collection()
    sources = sources_collection.find()
    return jsonify(sources), 200


@vocabulary_bp.route('/vocabulary/sources/<source_id>', methods=['DELETE'])
def delete_vocabulary_source(source_id: str):
    """Delete a vocabulary source and all its words."""
    sources_collection = get_sources_collection()
    vocab_collection = get_vocabulary_collection()

    # Check if source exists
    source = sources_collection.find_one({'_id': source_id})
    if not source:
        return jsonify({'error': 'Source not found'}), 404

    # Delete all words from this source
    vocab_result = vocab_collection.delete_many({'sourceId': source_id})

    # Delete the source
    sources_collection.delete_one({'_id': source_id})

    return jsonify({
        'message': 'Source deleted successfully',
        'wordsDeleted': vocab_result['deleted_count']
    }), 200
