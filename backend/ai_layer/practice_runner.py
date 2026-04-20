"""Practice session runner - core app code for AI-coached practice sessions."""
import asyncio
import json
import logging
import os
import random
import math
from datetime import datetime, date, timedelta
from statistics import mean

from agents import Runner
from agents.extensions.memory import RedisSession

from models import Word, User, UserSession, SessionWord, SessionWordAttempt, UserProfile, Deck
from ai_layer.context import UserSessionContext, WordContext
from ai_layer.chat_agents import laoshi_agent, summary_agent, build_agents
from ai_layer.mem0_setup import mem0_client
from crypto_utils import decrypt_api_key
from config import Config
from extensions import db

logger = logging.getLogger(__name__)


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
    Falls back to in-memory if Redis URI is not configured or connection fails.
    """
    redis_url = os.getenv("REDIS_URI")
    if redis_url:
        redis_kwargs = {
            "socket_connect_timeout": 10,
            "socket_keepalive": True,
        }

        try:
            # Eagerly test Redis connectivity with a synchronous ping.
            # RedisSession.from_url is lazy and won't fail until async usage,
            # which bypasses this try/except block.
            import redis as sync_redis
            test_client = sync_redis.from_url(
                redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            test_client.ping()
            test_client.close()

            return RedisSession.from_url(
                session_id=f"session:{session_id}",
                url=redis_url,
                redis_kwargs=redis_kwargs
            )
        except Exception as e:
            logger.warning(
                f"Redis connection failed (session_id={session_id}). "
                f"Using in-memory session. Error: {type(e).__name__}: {e}"
            )
            return None
    # Fallback: return None to use default in-memory session behavior
    return None


def get_user_agent(user, session_ds_version=None, session_gemini_version=None):
    """Get the appropriate agents for the user (custom BYOK keys or default).

    Checks key versions to detect mid-session key changes.
    Returns (orchestrator_agent, summary_agent, current_ds_version, current_gemini_version).
    """
    if not user.profile:
        return laoshi_agent, summary_agent, 1, 1

    ds_key = None
    gemini_key = None

    if user.profile.encrypted_deepseek_api_key:
        ds_key = decrypt_api_key(user.profile.encrypted_deepseek_api_key)
    if user.profile.encrypted_gemini_api_key:
        gemini_key = decrypt_api_key(user.profile.encrypted_gemini_api_key)

    current_ds_version = user.profile.deepseek_key_version
    current_gemini_version = user.profile.gemini_key_version

    # Check if keys changed mid-session
    ds_changed = (session_ds_version is not None and
                  session_ds_version != current_ds_version)
    gemini_changed = (session_gemini_version is not None and
                      session_gemini_version != current_gemini_version)

    if ds_changed or gemini_changed:
        logger.info(f"Key version change detected: ds={ds_changed}, gemini={gemini_changed}")

    if not ds_key and not gemini_key:
        return laoshi_agent, summary_agent, current_ds_version, current_gemini_version

    orch, summ = build_agents(deepseek_api_key=ds_key, gemini_api_key=gemini_key)
    return orch, summ, current_ds_version, current_gemini_version


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

    # Get preferred_name from UserProfile if available, fallback to username
    preferred_name = user.username
    if user.profile and user.profile.preferred_name:
        preferred_name = user.profile.preferred_name

    return UserSessionContext(
        user_id=user.id,
        session_id=session.id,
        preferred_name=preferred_name,
        current_word=current_word,
        session_word_dict=session_word_dict,
        words_practiced=words_practiced,
        words_skipped=words_skipped,
        words_total=session.words_per_session,
        session_complete=session_complete,
        mem0_preferences=mem0_prefs,
        word_roster=word_roster,
    )


def _parse_json_from_string(text: str) -> dict | None:
    """Extract JSON object from a string that may contain markdown fences or surrounding text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    import re
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: find first { ... } block
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def extract_feedback_from_result(result):
    """
    Parse feedback JSON from result.new_items tool call outputs.
    Defensive extraction: NOT from orchestrator text.
    Returns validated dict or None.
    """
    from agents.items import ToolCallOutputItem

    for item in result.new_items:
        if isinstance(item, ToolCallOutputItem):
            try:
                output = item.output
                if isinstance(output, dict):
                    return validate_feedback(output)
                elif isinstance(output, str):
                    data = _parse_json_from_string(output)
                    if data:
                        return validate_feedback(data)
            except (TypeError, AttributeError):
                continue
    return None


def update_streak(user_id: int):
    """
    Update user's practice streak with database-level locking to prevent race conditions.
    Uses SELECT FOR UPDATE to ensure atomic streak updates.
    """
    # Use transaction with row-level locking
    with db.session.begin():
        # Lock the user_profile row for this user
        profile = db.session.query(UserProfile).filter_by(
            user_id=user_id
        ).with_for_update().first()

        if not profile:
            return

        today = date.today()

        if profile.last_practice_date == today:
            return  # Already practiced today
        elif profile.last_practice_date == today - timedelta(days=1):
            profile.current_streak += 1
        else:
            profile.current_streak = 1

        profile.last_practice_date = today
        # No explicit commit needed - db.session.begin() context manager handles it


def update_srs(word, quality: int):
    """
    Update word SRS state using modified SM-2 algorithm.

    Args:
        quality: 0-5 rating from user self-assessment
    """
    # Fast-track perfect first attempts
    if word.repetitions == 0 and quality == 5:
        word.interval_days = 14
        word.repetitions = 2
        word.ease_factor = 2.5
    elif quality < 3:
        # Harsh reset on failure (fair since user controls quality)
        word.repetitions = 0
        word.interval_days = 1
    else:
        # Standard SM-2 progression with gentler early intervals
        if word.repetitions == 0:
            word.interval_days = 1
        elif word.repetitions == 1:
            word.interval_days = 3
        elif word.repetitions == 2:
            word.interval_days = 7
        else:
            new_interval = word.interval_days * word.ease_factor
            # Use ceil for intervals < 7 to prevent stuck at 1 day
            if new_interval < 7:
                word.interval_days = math.ceil(new_interval)
            else:
                word.interval_days = round(new_interval)

        word.repetitions += 1

    # Update ease factor (SM-2 formula)
    word.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    word.ease_factor = max(1.3, word.ease_factor)

    # Set next review date
    word.next_review_date = date.today() + timedelta(days=word.interval_days)


def select_srs_words(deck_id: int, user_id: int, words_count: int):
    """
    Select words using SRS algorithm:
    - 40% new words (never reviewed)
    - 60% due/overdue review words
    - Buffer pools if either is insufficient
    - Fallback to future words if both insufficient
    """
    today = date.today()

    # Calculate target counts
    target_new = round(words_count * 0.4)
    target_review = words_count - target_new

    # Pool 1: New words (never reviewed)
    new_words = Word.query.filter_by(
        deck_id=deck_id,
        user_id=user_id,
        next_review_date=None
    ).all()

    # Pool 2: Due/overdue review words
    review_words = Word.query.filter(
        Word.deck_id == deck_id,
        Word.user_id == user_id,
        Word.next_review_date <= today
    ).order_by(Word.next_review_date.asc()).all()

    # Take what's available
    actual_new = min(target_new, len(new_words))
    actual_review = min(target_review, len(review_words))

    # Use buffer pools
    new_shortfall = target_new - actual_new
    review_shortfall = target_review - actual_review

    if new_shortfall > 0:
        actual_review = min(target_review + new_shortfall, len(review_words))
    elif review_shortfall > 0:
        actual_new = min(target_new + review_shortfall, len(new_words))

    # Select words
    selected_new = random.sample(new_words, actual_new) if actual_new > 0 else []
    selected_review = review_words[:actual_review]
    selected_words = selected_new + selected_review

    # Fallback: if both pools insufficient, use future words
    if len(selected_words) < words_count:
        selected_ids = {w.id for w in selected_words}
        future_words = Word.query.filter(
            Word.deck_id == deck_id,
            Word.user_id == user_id,
            Word.next_review_date > today
        ).order_by(Word.next_review_date.asc()).all()

        remaining = [w for w in future_words if w.id not in selected_ids]
        needed = words_count - len(selected_words)
        selected_words.extend(remaining[:needed])

    return selected_words


def initialize_session(user_id: int, deck_id: int, words_count: int | None = None):
    """Start a new practice session using SRS word selection."""
    user = User.get_by_id(user_id)
    if not user:
        return None, "User not found"

    # Verify deck exists and belongs to user
    deck = Deck.get_by_id(deck_id)
    if not deck or deck.user_id != user_id:
        return None, "Deck not found"

    # Resolve word count - check user profile first, then fallback to config default
    if words_count is None:
        if user.profile and user.profile.words_per_session:
            words_count = user.profile.words_per_session
        else:
            words_count = Config.DEFAULT_WORDS_PER_SESSION

    # Select words using SRS algorithm
    selected_words = select_srs_words(deck_id, user_id, words_count)

    if not selected_words:
        return None, "No words available for practice in this deck."

    actual_count = len(selected_words)

    # Create session
    session = UserSession(
        session_start_ds=datetime.utcnow(),
        user_id=user_id,
        deck_id=deck_id,
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

    # Get user-specific agent (with BYOK support) and store key versions
    agent, _, ds_ver, gemini_ver = get_user_agent(user)

    # Generate greeting
    session_obj = get_session(session.id)
    result = run_async(run_with_retry(
        agent,
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

    # Get user-specific agent (with BYOK support and version tracking)
    agent, _, ds_ver, gemini_ver = get_user_agent(user)

    # Run orchestrator
    session_obj = get_session(session_id)
    result = run_async(run_with_retry(
        agent, input=message, context=ctx, session=session_obj
    ))

    laoshi_response = result.final_output if hasattr(result, 'final_output') else str(result)

    # Debug: log all items from the agent run to diagnose tool call failures
    from agents.items import ToolCallItem, ToolCallOutputItem
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            logger.info(f"[DIAG] Tool called: {item.name} | input: {str(item.arguments)[:200]}")
        elif isinstance(item, ToolCallOutputItem):
            logger.info(f"[DIAG] Tool output: {str(item.output)[:500]}")
        else:
            logger.info(f"[DIAG] Item type: {type(item).__name__} | {str(item)[:200]}")

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


def advance_word(session_id: int, user_id: int, quality: int | None = None):
    """Advance to the next word. Averages attempt scores, updates SRS, updates mastery."""
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

        # Update Word SRS state if quality rating provided
        word = Word.get_by_id(current_sw.word_id)

        # Save SRS snapshot before rating (for undo+redo on retroactive edits)
        if quality is not None:
            current_sw.srs_snapshot = {
                'repetitions': word.repetitions,
                'interval_days': word.interval_days,
                'ease_factor': float(word.ease_factor),
                'next_review_date': str(word.next_review_date) if word.next_review_date else None,
                'is_mastered': word.is_mastered,
                'last_quality': word.last_quality,
            }
            current_sw.update()

        if quality is not None:
            word.last_quality = quality
            update_srs(word, quality)
            word.update_mastery_status()
        word.update()
    else:
        # No attempts = skip - defer by 1 day
        current_sw.is_skipped = True
        current_sw.status = -1  # skipped
        current_sw.update()

        word = Word.get_by_id(current_sw.word_id)
        if word.next_review_date:
            word.next_review_date = word.next_review_date + timedelta(days=1)
        else:
            word.next_review_date = date.today() + timedelta(days=1)
        word.update()

    # Re-hydrate context to check completion and find next word
    session_words = SessionWord.get_list_by_session_id(session_id)
    ctx = hydrate_context(user, session, session_words)

    # Check completion
    if ctx.session_complete:
        result, err = complete_session(session_id, user_id)
        if err:
            return None, err
        return result, None

    # Get user-specific agent (with BYOK support and version tracking)
    agent, _, ds_ver, gemini_ver = get_user_agent(user)

    # Introduce next word
    session_obj = get_session(session_id)
    next_word_msg = f"The student has moved to the next word. Introduce it: {ctx.current_word.word} ({ctx.current_word.pinyin}) - {ctx.current_word.meaning}"
    result = run_async(run_with_retry(
        agent, input=next_word_msg, context=ctx, session=session_obj
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
    """Complete a practice session: generate summary directly via summary agent."""
    user = User.get_by_id(user_id)
    session = UserSession.get_by_id(session_id)

    if not session or session.user_id != user_id:
        return None, "Session not found"

    session_words = SessionWord.get_list_by_session_id(session_id)
    ctx = hydrate_context(user, session, session_words)
    ctx.session_complete = True

    # Get user-specific summary agent (with BYOK support)
    _, summ_agent, ds_ver, gemini_ver = get_user_agent(user)

    # Run summary agent directly (no handoff needed)
    session_obj = get_session(session_id)
    try:
        result = run_async(run_with_retry(
            summ_agent,
            input="Generate session summary.",
            context=ctx,
            session=session_obj
        ))

        summary_text = result.final_output if hasattr(result, 'final_output') else str(result)

        # Try to parse as JSON for structured summary
        summary_data = _parse_json_from_string(summary_text)
        if summary_data:
            validated = validate_summary(summary_data)
            if validated:
                summary_text = validated['summary_text']
                # Write mem0 updates
                for update in validated.get('mem0_updates', []):
                    try:
                        mem0_client.add(update, user_id=str(user_id))
                    except Exception:
                        pass  # mem0 write failure shouldn't block session close

    except Exception:
        summary_data = None
        summary_text = "Session completed. Keep practicing!"

    # Extract deck_oneliner from the ORIGINAL parsed JSON (before summary_text was overwritten)
    if summary_data and 'deck_oneliner' in summary_data:
        deck_id = session.deck_id
        if deck_id:
            deck = Deck.get_by_id(deck_id)
            if deck:
                deck.laoshi_message = summary_data['deck_oneliner'][:500]  # Max 500 chars
                deck.update()
    else:
        # Fallback placeholder if AI doesn't generate one-liner
        deck_id = session.deck_id
        if deck_id:
            deck = Deck.get_by_id(deck_id)
            if deck and (not deck.laoshi_message or deck.laoshi_message == ""):
                deck.laoshi_message = "Laoshi is waiting for your next practice session"
                deck.update()

    # Update streak
    update_streak(user_id)

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
