"""Practice session runner - core app code for AI-coached practice sessions."""
import asyncio
import json
import os
from datetime import datetime
from statistics import mean

from agents import Runner
from agents.extensions.memory import RedisSession

from models import Word, User, UserSession, SessionWord, SessionWordAttempt
from ai_layer.context import UserSessionContext, WordContext
from ai_layer.chat_agents import laoshi_agent
from ai_layer.mem0_setup import mem0_client
from config import Config


def run_async(coro):
    """Wraps async Runner.run() for synchronous Flask using asyncio.run()."""
    return asyncio.run(coro)


def validate_feedback(data: dict) -> dict | None:
    """Validate feedback JSON from agent. Returns cleaned data or None if invalid."""
    required_keys = ['grammarScore', 'usageScore', 'naturalnessScore', 'isCorrect']
    if not all(k in data for k in required_keys):
        return None
    for key in ['grammarScore', 'usageScore', 'naturalnessScore']:
        score = data.get(key)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            return None
    return data


def validate_summary(data: dict) -> dict | None:
    """Validate summary JSON from agent. Returns cleaned data or None if invalid."""
    if 'summary_text' not in data or not isinstance(data['summary_text'], str):
        return None
    if 'mem0_updates' not in data:
        data['mem0_updates'] = []
    return data


async def run_with_retry(agent, input, context, session=None, max_attempts=3):
    """Run agent with exponential backoff retry."""
    for attempt in range(max_attempts):
        try:
            result = await Runner.run(agent, input=input, context=context, session=session)
            return result
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)  # Use asyncio.sleep, not time.sleep


def get_session(session_id: int):
    """Create a RedisSession for the given practice session.
    
    Uses Redis-backed session storage for persistence across requests.
    Falls back to in-memory if Redis URI is not configured.
    """
    redis_url = os.getenv("REDIS_URI")
    if redis_url:
        return RedisSession.from_url(
            session_id=f"session:{session_id}",
            url=redis_url
        )
    # Fallback: return None to use default session behavior
    return None


def hydrate_context(user, session, session_words, mem0_prefs=None):
    """Build UserSessionContext from DB objects."""
    session_words_sorted = sorted(session_words, key=lambda sw: sw.word_order)

    # Build word roster
    word_roster = []
    for sw in session_words_sorted:
        w = sw.word
        word_roster.append(WordContext(
            word_id=w.id, word=w.word, pinyin=w.pinyin, meaning=w.meaning
        ))

    # Derive session_word_dict, current_word, and counts
    session_word_dict = {}
    current_word = None
    words_practiced = 0
    words_skipped = 0
    for sw in session_words_sorted:
        session_word_dict[sw.word_id] = sw.status
        if sw.status == 1:  # completed
            words_practiced += 1
        elif sw.status == -1:  # skipped
            words_skipped += 1
        elif sw.status == 0 and current_word is None:  # pending and first one
            w = sw.word
            current_word = WordContext(
                word_id=w.id, word=w.word, pinyin=w.pinyin, meaning=w.meaning
            )

    session_complete = all(v != 0 for v in session_word_dict.values())

    return UserSessionContext(
        user_id=user.id,
        session_id=session.id,
        preferred_name=user.preferred_name or user.username,
        current_word=current_word,
        session_word_dict=session_word_dict,
        words_practiced=words_practiced,
        words_skipped=words_skipped,
        words_total=session.words_per_session,
        session_complete=session_complete,
        mem0_preferences=mem0_prefs,
        word_roster=word_roster,
    )


def extract_feedback_from_result(result):
    """
    Parse feedback JSON from result.new_items tool call outputs.
    Defensive extraction: NOT from orchestrator text.
    Returns validated dict or None.
    """
    from agents.items import ToolCallOutputItem
    
    for item in result.new_items:
        if isinstance(item, ToolCallOutputItem):
            # Check if this is from the evaluate_sentence tool
            # The output contains the agent's response (feedback_agent's output)
            try:
                output = item.output
                if isinstance(output, dict):
                    return validate_feedback(output)
                elif isinstance(output, str):
                    data = json.loads(output)
                    return validate_feedback(data)
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
    return None


def update_confidence(word, avg_grammar, avg_usage, avg_naturalness, is_correct):
    """Apply confidence formula from user_evaluation.md."""
    correctness_factor = 1.0 if is_correct else -0.5
    quality_multiplier = (0.4 * avg_grammar + 0.4 * avg_usage + 0.2 * avg_naturalness) / 10.0
    learning_rate = 0.1
    new_score = word.confidence_score + correctness_factor * quality_multiplier * learning_rate
    new_score = max(0.0, min(1.0, new_score))  # clamp
    word.update_confidence_score(new_score)


def initialize_session(user_id: int, words_count: int | None = None):
    """Start a new practice session."""
    import random

    user = User.get_by_id(user_id)
    if not user:
        return None, "User not found"

    # Resolve word count
    if words_count is None:
        words_count = Config.DEFAULT_WORDS_PER_SESSION

    # Select eligible words (confidence < 0.9)
    eligible_words = Word.query.filter_by(user_id=user_id).filter(
        Word.confidence_score < 0.9
    ).all()

    if not eligible_words:
        return None, "No eligible words for practice. All your words are mastered or you have no vocabulary imported."

    # Random sample
    actual_count = min(words_count, len(eligible_words))
    selected_words = random.sample(eligible_words, actual_count)

    # Create session
    session = UserSession(
        session_start_ds=datetime.utcnow(),
        user_id=user_id,
        words_per_session=actual_count,
    )
    session.add()

    # Create SessionWord rows
    for i, word in enumerate(selected_words):
        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            session_word_load_ds=datetime.utcnow(),
            word_order=i,
        )
        sw.add()

    # Fetch mem0 preferences
    mem0_prefs = None
    try:
        memories = mem0_client.search(
            query="language learning preferences and patterns",
            user_id=str(user_id)
        )
        if memories:
            mem0_prefs = str(memories)
    except Exception:
        pass  # mem0 failure should not block session start

    # Hydrate context
    session_words = SessionWord.get_list_by_session_id(session.id)
    ctx = hydrate_context(user, session, session_words, mem0_prefs)

    # Generate greeting
    session_obj = get_session(session.id)
    result = run_async(run_with_retry(
        laoshi_agent, 
        input="Start the session. Greet the student and introduce the first word.", 
        context=ctx, 
        session=session_obj
    ))

    greeting = result.final_output if hasattr(result, 'final_output') else str(result)

    return {
        'session': session.format_data(user),
        'current_word': {
            'word_id': ctx.current_word.word_id,
            'word': ctx.current_word.word,
            'pinyin': ctx.current_word.pinyin,
            'meaning': ctx.current_word.meaning,
        } if ctx.current_word else None,
        'greeting_message': greeting,
        'words_practiced': ctx.words_practiced,
        'words_skipped': ctx.words_skipped,
        'words_total': ctx.words_total,
        'session_complete': False,
    }, None


def handle_message(session_id: int, user_id: int, message: str):
    """Process a user message during practice."""
    user = User.get_by_id(user_id)
    session = UserSession.get_by_id(session_id)

    if not session or session.user_id != user_id:
        return None, "Session not found"

    if session.session_end_ds is not None:
        return None, "Session is already complete"

    # Hydrate context
    session_words = SessionWord.get_list_by_session_id(session_id)
    ctx = hydrate_context(user, session, session_words)

    if ctx.current_word is None:
        return None, "No active word in session"

    # Run orchestrator
    session_obj = get_session(session_id)
    result = run_async(run_with_retry(
        laoshi_agent, input=message, context=ctx, session=session_obj
    ))

    laoshi_response = result.final_output if hasattr(result, 'final_output') else str(result)

    # Defensive score extraction
    feedback = extract_feedback_from_result(result)
    feedback_response = None

    if feedback:
        # Create SessionWordAttempt
        attempt_count = SessionWordAttempt.count_by_word_session(
            ctx.current_word.word_id, session_id
        )
        attempt = SessionWordAttempt(
            word_id=ctx.current_word.word_id,
            session_id=session_id,
            attempt_number=attempt_count + 1,
            sentence=message,
            grammar_score=feedback['grammarScore'],
            usage_score=feedback['usageScore'],
            naturalness_score=feedback['naturalnessScore'],
            is_correct=feedback.get('isCorrect', False),
            feedback_text=feedback.get('feedback', ''),
        )
        attempt.add()

        feedback_response = feedback

    return {
        'laoshi_response': laoshi_response,
        'feedback': feedback_response,
        'current_word': {
            'word_id': ctx.current_word.word_id,
            'word': ctx.current_word.word,
            'pinyin': ctx.current_word.pinyin,
            'meaning': ctx.current_word.meaning,
        },
        'words_practiced': ctx.words_practiced,
        'words_skipped': ctx.words_skipped,
        'words_total': ctx.words_total,
        'session_complete': ctx.session_complete,
    }, None


def advance_word(session_id: int, user_id: int):
    """Advance to the next word. Averages attempt scores or marks as skipped."""
    user = User.get_by_id(user_id)
    session = UserSession.get_by_id(session_id)

    if not session or session.user_id != user_id:
        return None, "Session not found"

    if session.session_end_ds is not None:
        return None, "Session is already complete"

    # Find current word (first by word_order where status == 0/pending)
    session_words = SessionWord.get_list_by_session_id(session_id)
    session_words_sorted = sorted(session_words, key=lambda sw: sw.word_order)

    current_sw = None
    for sw in session_words_sorted:
        if sw.status == 0:  # pending
            current_sw = sw
            break

    if current_sw is None:
        return None, "No active word to advance"

    # Check attempts
    attempts = SessionWordAttempt.get_by_word_session(current_sw.word_id, session_id)

    if attempts:
        # Average scores across all attempts
        avg_grammar = mean([a.grammar_score for a in attempts if a.grammar_score is not None])
        avg_usage = mean([a.usage_score for a in attempts if a.usage_score is not None])
        avg_naturalness = mean([a.naturalness_score for a in attempts if a.naturalness_score is not None])

        # Write averages to SessionWord
        current_sw.grammar_score = avg_grammar
        current_sw.usage_score = avg_usage
        current_sw.naturalness_score = avg_naturalness
        current_sw.is_correct = (avg_grammar == 10 and avg_usage >= 8)
        current_sw.status = 1  # completed
        current_sw.update()

        # Update Word confidence score
        word = Word.get_by_id(current_sw.word_id)
        update_confidence(word, avg_grammar, avg_usage, avg_naturalness, current_sw.is_correct)
        word.update()  # Persist the confidence score change
    else:
        # No attempts = skip
        current_sw.is_skipped = True
        current_sw.status = -1  # skipped
        current_sw.update()

    # Re-hydrate context to check completion and find next word
    session_words = SessionWord.get_list_by_session_id(session_id)
    ctx = hydrate_context(user, session, session_words)

    # Check completion
    if ctx.session_complete:
        result, err = complete_session(session_id, user_id)
        if err:
            return None, err
        return result, None

    # Introduce next word
    session_obj = get_session(session_id)
    next_word_msg = f"The student has moved to the next word. Introduce it: {ctx.current_word.word} ({ctx.current_word.pinyin}) - {ctx.current_word.meaning}"
    result = run_async(run_with_retry(
        laoshi_agent, input=next_word_msg, context=ctx, session=session_obj
    ))

    laoshi_response = result.final_output if hasattr(result, 'final_output') else str(result)

    return {
        'laoshi_response': laoshi_response,
        'feedback': None,
        'current_word': {
            'word_id': ctx.current_word.word_id,
            'word': ctx.current_word.word,
            'pinyin': ctx.current_word.pinyin,
            'meaning': ctx.current_word.meaning,
        } if ctx.current_word else None,
        'words_practiced': ctx.words_practiced,
        'words_skipped': ctx.words_skipped,
        'words_total': ctx.words_total,
        'session_complete': ctx.session_complete,
    }, None


def complete_session(session_id: int, user_id: int):
    """Complete a practice session: generate summary via handoff, write mem0, close session."""
    user = User.get_by_id(user_id)
    session = UserSession.get_by_id(session_id)

    if not session or session.user_id != user_id:
        return None, "Session not found"

    session_words = SessionWord.get_list_by_session_id(session_id)
    ctx = hydrate_context(user, session, session_words)
    ctx.session_complete = True  # This triggers handoff instruction in prompt

    # Trigger summary via orchestrator -> summary agent handoff
    # The orchestrator sees session_complete=True and hands off automatically
    session_obj = get_session(session_id)
    try:
        result = run_async(run_with_retry(
            laoshi_agent,
            input="Session complete. Generate summary.",  # Minimal input, agent uses context
            context=ctx,
            session=session_obj
        ))

        # When handoff occurs, result comes from summary agent
        summary_text = result.final_output if hasattr(result, 'final_output') else str(result)

        # Try to parse as JSON for structured summary
        try:
            summary_data = json.loads(summary_text)
            validated = validate_summary(summary_data)
            if validated:
                summary_text = validated['summary_text']
                # Write mem0 updates
                for update in validated.get('mem0_updates', []):
                    try:
                        mem0_client.add(update, user_id=str(user_id))
                    except Exception:
                        pass  # mem0 write failure shouldn't block session close
        except (json.JSONDecodeError, TypeError):
            pass  # Use raw text as summary

    except Exception:
        summary_text = "Session completed. Keep practicing!"

    # Close session
    session.summary_text = summary_text
    session.session_end_ds = datetime.utcnow()
    session.update()

    # Build word results
    word_results = []
    words_practiced_count = 0
    words_skipped_count = 0
    for sw in sorted(session_words, key=lambda s: s.word_order):
        w = sw.word
        if sw.status == -1:  # skipped
            words_skipped_count += 1
        elif sw.status == 1:  # completed
            words_practiced_count += 1
        word_results.append({
            'word': w.word,
            'grammar_score': sw.grammar_score,
            'usage_score': sw.usage_score,
            'naturalness_score': sw.naturalness_score,
            'is_correct': sw.is_correct,
            'is_skipped': sw.is_skipped,
        })

    return {
        'laoshi_response': summary_text,
        'feedback': None,
        'current_word': None,
        'words_practiced': words_practiced_count,
        'words_skipped': words_skipped_count,
        'words_total': ctx.words_total,
        'session_complete': True,
        'summary': {
            'session_id': session_id,
            'summary_text': summary_text,
            'words_practiced': words_practiced_count,
            'words_skipped': words_skipped_count,
            'word_results': word_results,
        }
    }, None
