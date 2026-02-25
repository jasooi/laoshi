# Milestone 3: AI Practice Sessions -- Task Breakdown

## Task Overview

**Total tasks**: 27 tasks (3.1–3.27) across 5 phases
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be parallelised where noted.

---

## Prerequisites

Before starting any tasks:

1. Ensure the backend virtual environment is active and `backend/requirements.txt` dependencies are installed (includes `openai-agents`, `mem0ai`, `redis`, `litellm`, `asyncio`).
2. Ensure `npm install` has been run in `frontend/`.
3. Ensure PostgreSQL is running and the `DATABASE_URI` in `.env` is valid.
4. Ensure Redis is running and `REDIS_URI` is set in `.env`.
5. Ensure all AI API keys are set in `.env`: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL_NAME`, `MEM0_API_KEY`.
6. Ensure both servers start: `python backend/app.py` (Flask on port 5000), `npm run dev` (Vite on port 5173).
7. Ensure existing tests pass: `cd backend && python -m pytest tests/ -v` and `cd frontend && npm test -- --run`.
8. Do NOT use or modify `ai_layer/function_tools.py` or `ai_layer/learning_file.py` — these are archived.

---

## Phase 1: Database & Configuration

These tasks modify models, run migrations, and add configuration. No AI or frontend changes.

---

### T-3.1: Add columns to UserSession

**Description**: Add `summary_text` and `words_per_session` columns to the `UserSession` model. Update `format_data()` to include them.

**Files affected**:
- `backend/models.py` — modify `UserSession` class

**Changes**:

Add two columns after the existing `user_id` column:

```python
class UserSession(db.Model):
    # ... existing columns ...
    summary_text = db.Column(db.Text, nullable=True)
    words_per_session = db.Column(db.Integer, nullable=False, default=10)
```

Update `format_data()`:
```python
def format_data(self, viewer=None):
    if viewer is None:
        return None
    if viewer.id != self.user_id and not viewer.is_admin:
        return None
    return {
        'id': self.id,
        'session_start_ds': self.session_start_ds,
        'session_end_ds': self.session_end_ds,
        'user_id': self.user_id,
        'summary_text': self.summary_text,
        'words_per_session': self.words_per_session,
    }
```

**Acceptance criteria**:
- `UserSession` has `summary_text` and `words_per_session` columns.
- `format_data()` includes both new fields.
- `words_per_session` defaults to 10.
- Existing tests pass.

**Dependencies**: None.

---

### T-3.2: Add columns to SessionWord

**Description**: Add `word_order`, `grammar_score`, `usage_score`, `naturalness_score`, and `is_correct` columns to the `SessionWord` model. Update `format_data()`.

**Files affected**:
- `backend/models.py` — modify `SessionWord` class

**Changes**:

Add six columns:
```python
class SessionWord(db.Model):
    # ... existing columns (word_id, session_id, session_word_load_ds, is_skipped, session_notes) ...
    word_order = db.Column(db.Integer, nullable=False, default=0)
    grammar_score = db.Column(db.Float, nullable=True)
    usage_score = db.Column(db.Float, nullable=True)
    naturalness_score = db.Column(db.Float, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)  # 0=pending, 1=completed, -1=skipped
```

Update `format_data()` to include all new fields:
```python
def format_data(self, viewer=None):
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
    }
```

**Acceptance criteria**:
- `SessionWord` has all 6 new columns.
- `word_order` and `status` are non-nullable (default 0 for backward compat with existing rows).
- Score columns are nullable (null = not yet evaluated).
- `format_data()` includes all new fields.
- Existing tests pass.

**Dependencies**: None (can be done in parallel with T-3.1).

---

### T-3.2b: Create SessionWordAttempt model

**Description**: Create the `SessionWordAttempt` model for storing individual sentence attempts per word per session. Link it to `SessionWord` via composite FK.

**Files affected**:
- `backend/models.py` — add new `SessionWordAttempt` class, add `attempts` relationship to `SessionWord`

**Changes**:

Add after the `SessionWord` class:
```python
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
    created_ds = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['word_id', 'session_id'],
            ['session_word.word_id', 'session_word.session_id']
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
```

Add relationship to `SessionWord`:
```python
class SessionWord(db.Model):
    # ... existing code ...
    attempts = db.relationship('SessionWordAttempt', back_populates='session_word',
                               order_by='SessionWordAttempt.attempt_number')
```

**Acceptance criteria**:
- `SessionWordAttempt` model exists with `attempt_id` as PK (auto-increment).
- Composite FK to `session_word(word_id, session_id)` works correctly.
- `SessionWord.attempts` relationship returns ordered attempts.
- `get_by_word_session()` and `count_by_word_session()` classmethods work.
- `format_data()` returns all fields.

**Dependencies**: T-3.2 (SessionWord must have composite PK, which already exists).

---

### T-3.3: Run Alembic migration

**Description**: Generate and run an Alembic migration for the new columns and table.

**Files affected**:
- `backend/migrations/versions/` — new migration file (auto-generated)

**Commands**:
```bash
cd backend
flask db migrate -m "add_ai_practice_fields_and_session_word_attempt"
flask db upgrade
```

**Acceptance criteria**:
- Migration runs without errors.
- Database schema matches the model definitions.
- Existing data is preserved (new columns are nullable or have defaults).

**Dependencies**: T-3.1, T-3.2, T-3.2b.

---

### T-3.4: Add DEFAULT_WORDS_PER_SESSION to config

**Description**: Add the configurable default for words per session. REDIS_URI stays in `.env` only.

**Files affected**:
- `backend/config.py` — add constant to `Config` class

**Changes**:

```python
class Config():
    # ... existing ...
    DEFAULT_WORDS_PER_SESSION = 10
```

Also add to `TestConfig`:
```python
class TestConfig(Config):
    # ... existing ...
    DEFAULT_WORDS_PER_SESSION = 5  # smaller for faster tests
```

**Acceptance criteria**:
- `Config.DEFAULT_WORDS_PER_SESSION` is 10.
- `TestConfig.DEFAULT_WORDS_PER_SESSION` is 5.
- `REDIS_URI` is NOT in config.py (read via `os.getenv("REDIS_URI")` in ai_layer code).

**Dependencies**: None (can be done in parallel with T-3.1–T-3.3).

---

## Phase 2: AI Layer

These tasks rework the agent definitions, build the context dataclass, and create the practice runner. Must be done after Phase 1 (needs the models).

---

### T-3.5: Expand UserSessionContext

**Description**: Rewrite `ai_layer/context.py` with the full `UserSessionContext` and `WordContext` dataclasses.

**Files affected**:
- `backend/ai_layer/context.py` — full rewrite

**Changes**:

```python
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
```

**Acceptance criteria**:
- Both dataclasses importable from `context.py`.
- `UserSessionContext` has all fields from the design doc.
- `WordContext` has word_id, word, pinyin, meaning.

**Dependencies**: None (dataclasses have no DB dependency).

---

### T-3.6: Rework Feedback Agent

**Description**: Replace the static prompt on the feedback agent with a dynamic `build_feedback_prompt()` function that injects the current word from context. Update the isCorrect threshold.

**Files affected**:
- `backend/ai_layer/chat_agents.py` — modify `feedback_agent`

**Changes**:

Add a prompt builder:
```python
def build_feedback_prompt(ctx: UserSessionContext) -> str:
    word = ctx.current_word
    return f"""You are a Mandarin Chinese language teacher evaluating a student's sentence.

Target vocabulary word: {word.word} ({word.pinyin}) - {word.meaning}

Evaluate the sentence on:
1. Grammar correctness (1-10): word order, particles, verb aspect, measure words
2. Word usage accuracy (1-10): correct meaning/context, appropriate collocations
3. Naturalness (1-10): native-like expression, idiomatic usage
4. Overall correctness: true ONLY if grammarScore == 10 AND usageScore >= 8

Provide:
- Detailed feedback in English
- Specific corrections if needed, in English
- Explanation of mistakes if needed, in English
- 2-3 example Mandarin sentences using the word correctly

Return response in JSON format:
{{
  "grammarScore": number,
  "usageScore": number,
  "naturalnessScore": number,
  "isCorrect": boolean,
  "feedback": string,
  "corrections": string[],
  "explanations": string[],
  "exampleSentences": string[]
}}"""
```

Update agent definition:
```python
feedback_agent = Agent[UserSessionContext](
    name="feedback-agent",
    instructions=build_feedback_prompt,  # callable, not string
    model=deepseek_model
)
```

**Acceptance criteria**:
- `build_feedback_prompt` injects `ctx.current_word` details.
- `isCorrect` threshold is `grammarScore == 10 AND usageScore >= 8` in the prompt.
- Agent uses `instructions=build_feedback_prompt` (callable).
- JSON output schema matches existing format.

**Dependencies**: T-3.5 (UserSessionContext).

---

### T-3.7: Rework Orchestrator Agent

**Description**: Replace the wrong "English teacher" prompt with a dynamic sassy Mandarin teacher prompt. Wire feedback agent as tool and summary agent as handoff.

**Files affected**:
- `backend/ai_layer/chat_agents.py` — modify `laoshi_agent`

**Changes**:

Add prompt builder:
```python
def build_orchestrator_prompt(ctx: UserSessionContext) -> str:
    word_info = ""
    if ctx.current_word:
        word_info = f"\nCurrent word: {ctx.current_word.word} ({ctx.current_word.pinyin}) - {ctx.current_word.meaning}"

    progress = f"{ctx.words_completed}/{ctx.words_total} words completed"

    mem0_section = ""
    if ctx.mem0_preferences:
        mem0_section = f"\n\nWhat you remember about this student:\n{ctx.mem0_preferences}"

    handoff_instruction = ""
    if ctx.session_complete:
        handoff_instruction = """
CRITICAL: The session is complete. You MUST hand off to the summary agent immediately.
Do not respond to the student directly. Use the handoff to transfer control."""

    return f"""You are Laoshi, a sassy-but-encouraging Mandarin Chinese teacher coaching your student {ctx.preferred_name}.

Your personality: witty, direct, supportive but doesn't sugarcoat. You use light humour and gentle teasing to motivate.

Session progress: {progress}{word_info}{mem0_section}

Your responsibilities:
1. INTENT CLASSIFICATION: Determine if the student's message is:
   a) A sentence attempt using the current vocabulary word -> call the evaluate_sentence tool with the student's sentence as input
   b) A chat message or question -> respond conversationally in your persona

2. When the evaluate_sentence tool returns results, relay the feedback to the student in your own words with your personality. Do NOT repeat the raw JSON. Summarise the key points naturally.

3. After relaying feedback, encourage the student to try again or move on.

4. If the student asks about a word, grammar point, or Chinese language concept, answer helpfully.

{handoff_instruction}

Rules:
- Respond in English (you may include Chinese examples).
- Keep responses concise (2-4 sentences for feedback relay, 1-2 for chat).
- Never fabricate scores or evaluation data. Only relay what the evaluate_sentence tool returns.
- Never tell the student the exact numeric scores. Describe performance qualitatively."""
```

Update agent definition:
```python
from agents import handoff

laoshi_agent = Agent[UserSessionContext](
    name="laoshi-orchestrator",
    instructions=build_orchestrator_prompt,
    model=gemini_model,
    tools=[
        feedback_agent.as_tool(
            tool_name="evaluate_sentence",
            tool_description="Evaluate student's Mandarin sentence and give feedback and score in structured output. Pass the student's sentence as input."
        )
    ],
    handoffs=[handoff(summary_agent)]
)
```

**Acceptance criteria**:
- Prompt says "Mandarin Chinese teacher" (not "English teacher").
- Dynamic prompt injects student name, current word, progress, mem0 preferences.
- When `ctx.session_complete=True`, prompt includes explicit handoff instruction.
- Intent classification instructions are clear.
- `feedback_agent` wired as tool via `as_tool()`.
- `summary_agent` wired as handoff via `handoff()`.
- Commented-out memory tools removed.

**Dependencies**: T-3.5, T-3.6, T-3.8 (summary agent must exist for handoff).

---

### T-3.8: Rework Summary Agent

**Description**: Replace the static prompt with a dynamic one. Return `{summary_text, mem0_updates}` JSON.

**Files affected**:
- `backend/ai_layer/chat_agents.py` — modify `summary_agent`

**Changes**:

Add prompt builder:
```python
def build_summary_prompt(ctx: UserSessionContext) -> str:
    word_results = []
    for wc in ctx.word_roster:
        status = ctx.session_word_dict.get(wc.word_id, 0)
        status_label = "completed" if status == 1 else ("skipped" if status == -1 else "active")
        word_results.append(f"- {wc.word} ({wc.pinyin}): {status_label}")

    word_list = "\n".join(word_results)

    return f"""You are wrapping up a Mandarin practice session with {ctx.preferred_name}.

Words in this session:
{word_list}

Read the conversation history and produce a summary.

Your summary MUST include:
1. Two specific things the student did well -- reference actual words, phrases, or grammar patterns from their sentences.
2. One specific area for improvement -- reference an actual recurring mistake or weakness.

Rules:
- Be specific: cite Chinese words or phrases the student used. Do not speak in generalities.
- Be encouraging but honest.
- Do not repeat evaluation data verbatim; synthesise into natural teacher feedback.
- Write in plain prose (no bullet points or headings), as if speaking directly to the student.
- Keep it concise: 3-5 sentences maximum.

Also recommend any updates to long-term memory about this student's learning patterns.

Return response in JSON format:
{{
  "summary_text": string,
  "mem0_updates": string[]
}}"""
```

Update agent definition:
```python
summary_agent = Agent[UserSessionContext](
    name="summary-agent",
    instructions=build_summary_prompt,
    model=gemini_model
)
```

**Acceptance criteria**:
- Dynamic prompt injects student name and word roster with statuses.
- Output schema is `{summary_text, mem0_updates}`.
- Agent uses `instructions=build_summary_prompt` (callable).

**Dependencies**: T-3.5 (UserSessionContext).

---

### T-3.9: Clean up chat_agents.py module-level code

**Description**: Remove hardcoded dotenv path, clean up imports, remove commented-out code.

**Files affected**:
- `backend/ai_layer/chat_agents.py` — module-level code

**Changes**:

1. Replace hardcoded dotenv path:
   ```python
   # Before:
   load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')
   # After:
   load_dotenv()  # Let dotenv find .env automatically from CWD
   ```
   Note: The backend is always run from the project root, so `load_dotenv()` will find `.env` there. If this doesn't work reliably, use a path relative to the file:
   ```python
   from pathlib import Path
   load_dotenv(Path(__file__).resolve().parents[2] / '.env')
   ```

2. Remove duplicate import `from agents import Agent` (appears twice, lines 1 and 9).

3. Remove all commented-out memory tool code (lines 117–130).

4. Ensure agent definitions are in correct dependency order: `feedback_agent` first, then `summary_agent`, then `laoshi_agent` (which references both).

**Acceptance criteria**:
- No hardcoded absolute paths in the file.
- No duplicate imports.
- No commented-out code blocks.
- All agents still instantiate correctly.

**Dependencies**: T-3.6, T-3.7, T-3.8 (all agent rework must be done first).

---

### T-3.10: Create practice_runner.py scaffolding

**Description**: Create the `practice_runner.py` module with the `run_async()` wrapper, validation helpers, and retry logic. This is the scaffolding — the main functions (T-3.11–T-3.14) are added in subsequent tasks.

**Files affected**:
- `backend/ai_layer/practice_runner.py` (new file)

**Changes**:

```python
import asyncio
import json
import os
import time
from statistics import mean

from agents import Runner
from agents.sessions import RedisSession

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


def get_redis_session(session_id: int):
    """Create a RedisSession for the given practice session."""
    return RedisSession.from_url(
        session_id=f"session:{session_id}",
        url=os.getenv("REDIS_URI")
    )


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

    # Derive session_word_dict and current_word
    session_word_dict = {}
    current_word = None
    words_completed = 0
    for sw in session_words_sorted:
        if sw.grammar_score is not None and sw.is_correct is not None:
            session_word_dict[sw.word_id] = 1
            words_completed += 1
        elif sw.is_skipped:
            session_word_dict[sw.word_id] = -1
            words_completed += 1
        else:
            session_word_dict[sw.word_id] = 0
            if current_word is None:
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
        words_completed=words_completed,
        words_total=session.words_per_session,
        session_complete=session_complete,
        mem0_preferences=mem0_prefs,
        word_roster=word_roster,
    )


def extract_feedback_from_result(result):
    """
    Parse feedback JSON from result.raw_responses tool call outputs.
    Defensive extraction: NOT from orchestrator text.
    Returns validated dict or None.
    """
    for response in result.raw_responses:
        for choice in response.choices:
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    if tc.function.name == "evaluate_sentence":
                        try:
                            data = json.loads(tc.function.arguments)
                            return validate_feedback(data)
                        except (json.JSONDecodeError, TypeError):
                            return None
    return None


def update_confidence(word, avg_grammar, avg_usage, avg_naturalness, is_correct):
    """Apply confidence formula from user_evaluation.md."""
    correctness_factor = 1.0 if is_correct else -0.5
    quality_multiplier = (0.4 * avg_grammar + 0.4 * avg_usage + 0.2 * avg_naturalness) / 10.0
    learning_rate = 0.1
    new_score = word.confidence_score + correctness_factor * quality_multiplier * learning_rate
    new_score = max(0.0, min(1.0, new_score))
    word.update_confidence_score(new_score)
```

**Acceptance criteria**:
- Module imports correctly.
- `run_async`, `validate_feedback`, `validate_summary`, `run_with_retry`, `get_redis_session`, `hydrate_context`, `extract_feedback_from_result`, `update_confidence` are all importable.
- No circular imports.

**Dependencies**: T-3.5 (context), T-3.6/7/8 (agents), T-3.1/2/2b (models).

---

### T-3.11: Implement initialize_session

**Description**: Implement the `initialize_session()` function that starts a new practice session: selects words, creates DB rows, fetches mem0, generates greeting.

**Files affected**:
- `backend/ai_layer/practice_runner.py` — add function

**Changes**:

```python
def initialize_session(user_id: int, words_count: int | None = None):
    """Start a new practice session."""
    from extensions import db
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
    redis_session = get_redis_session(session.id)
    result = run_async(run_with_retry(laoshi_agent, input="Start the session. Greet the student and introduce the first word.", context=ctx, session=redis_session))

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
```

Add `from datetime import datetime` to the imports at the top of the file if not already present.

**Acceptance criteria**:
- Words with `confidence_score >= 0.9` are excluded.
- Returns error if no eligible words.
- Creates `UserSession` and `SessionWord` rows correctly.
- `word_order` is 0-indexed and sequential.
- mem0 failure doesn't crash session start.
- Greeting is generated via `Runner.run()`.

**Dependencies**: T-3.10 (scaffolding).

---

### T-3.12: Implement handle_message

**Description**: Implement the `handle_message()` function that processes a user message through the orchestrator, extracts feedback if present, and writes to `SessionWordAttempt`.

**Files affected**:
- `backend/ai_layer/practice_runner.py` — add function

**Changes**:

```python
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
    redis_session = get_redis_session(session_id)
    result = run_async(run_with_retry(
        laoshi_agent, input=message, context=ctx, session=redis_session
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
```

**Acceptance criteria**:
- Routes message through orchestrator via `Runner.run()`.
- Extracts feedback defensively from `result.raw_responses`.
- Creates `SessionWordAttempt` row when feedback is found.
- Does NOT modify `SessionWord` scores or `Word.confidence_score`.
- Returns structured response with nullable feedback.
- Rejects messages to completed sessions.

**Dependencies**: T-3.10, T-3.11 (for session to exist).

---

### T-3.13: Implement advance_word

**Description**: Implement the `advance_word()` function ("Next Word" action) that computes averaged scores, updates confidence, and advances to the next word.

**Files affected**:
- `backend/ai_layer/practice_runner.py` — add function

**Changes**:

```python
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
    redis_session = get_redis_session(session_id)
    next_word_msg = f"The student has moved to the next word. Introduce it: {ctx.current_word.word} ({ctx.current_word.pinyin}) - {ctx.current_word.meaning}"
    result = run_async(run_with_retry(
        laoshi_agent, input=next_word_msg, context=ctx, session=redis_session
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
```

**Acceptance criteria**:
- If attempts exist: averages all attempt scores, writes to SessionWord, computes is_correct, sets status=1 (completed), updates Word.confidence_score.
- If no attempts: sets is_skipped=True, status=-1 (skipped).
- Uses explicit status column (0=pending, 1=completed, -1=skipped) to track word state.
- Advances to next word by word_order where status==0.
- Triggers complete_session when all words done.
- Generates next word introduction via Runner.run().

**Dependencies**: T-3.10, T-3.12.

---

### T-3.14: Implement complete_session

**Description**: Implement session completion: orchestrator-to-summary-agent handoff, summary writing, mem0 updates.

**Files affected**:
- `backend/ai_layer/practice_runner.py` — add function

**Changes**:

```python
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
    redis_session = get_redis_session(session_id)
    try:
        result = run_async(run_with_retry(
            laoshi_agent,
            input="Session complete. Generate summary.",  # Minimal input, agent uses context
            context=ctx,
            session=redis_session
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
```

**Acceptance criteria**:
- Triggers handoff to summary agent via Runner.run().
- Parses summary JSON if returned, falls back to raw text.
- Writes `summary_text` and `session_end_ds` to UserSession.
- Writes mem0 updates (graceful failure).
- Falls back to generic summary if agent fails entirely.
- Returns structured summary response with word results.

**Dependencies**: T-3.10, T-3.13 (complete_session is called from advance_word).

---

## Phase 3: API Endpoints

These tasks create the Flask-RESTful resources and register them. Must be done after Phase 2 (needs practice_runner).

---

### T-3.15: Create practice_resources.py

**Description**: Create the 4 Flask-RESTful resource classes for the practice session flow.

**Files affected**:
- `backend/practice_resources.py` (new file)

**Changes**:

```python
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import User, UserSession, SessionWord
from ai_layer.practice_runner import initialize_session, handle_message, advance_word


class PracticeSessionResource(Resource):
    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        words_count = data.get('words_count')

        result, error = initialize_session(user_id, words_count)
        if error:
            return {'error': error}, 400
        return result, 201


class PracticeMessageResource(Resource):
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data or not data.get('message'):
            return {'error': 'Message is required'}, 400

        result, error = handle_message(id, user_id, data['message'])
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeNextWordResource(Resource):
    @jwt_required()
    def post(self, id):
        user_id = int(get_jwt_identity())

        result, error = advance_word(id, user_id)
        if error:
            status = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status
        return result, 200


class PracticeSummaryResource(Resource):
    @jwt_required()
    def get(self, id):
        user_id = int(get_jwt_identity())
        user = User.get_by_id(user_id)
        session = UserSession.get_by_id(id)

        if not session or session.user_id != user_id:
            return {'error': 'Session not found'}, 404

        session_words = SessionWord.get_list_by_session_id(id)
        words_completed = sum(1 for sw in session_words if sw.grammar_score is not None and not sw.is_skipped)
        words_skipped = sum(1 for sw in session_words if sw.is_skipped)

        word_results = []
        for sw in sorted(session_words, key=lambda s: s.word_order):
            w = sw.word
            word_results.append({
                'word': w.word,
                'grammar_score': sw.grammar_score,
                'usage_score': sw.usage_score,
                'naturalness_score': sw.naturalness_score,
                'is_correct': sw.is_correct,
                'is_skipped': sw.is_skipped,
            })

        return {
            'session_id': id,
            'summary_text': session.summary_text,
            'words_completed': words_completed,
            'words_skipped': words_skipped,
            'word_results': word_results,
        }, 200
```

**Acceptance criteria**:
- All 4 resources exist with correct HTTP methods.
- All endpoints are JWT-protected.
- Error responses use appropriate status codes (400, 404).
- PracticeMessageResource validates that `message` field exists.

**Dependencies**: T-3.11, T-3.12, T-3.13, T-3.14 (practice_runner functions).

---

### T-3.16: Register practice resources in app.py

**Description**: Import and register the 4 new resources with the Flask API.

**Files affected**:
- `backend/app.py` — modify import and `register_resources()`

**Changes**:

Add import:
```python
from practice_resources import (
    PracticeSessionResource,
    PracticeMessageResource,
    PracticeNextWordResource,
    PracticeSummaryResource
)
```

Add routes inside `register_resources()`:
```python
api.add_resource(PracticeSessionResource, '/practice/sessions')
api.add_resource(PracticeMessageResource, '/practice/sessions/<int:id>/messages')
api.add_resource(PracticeNextWordResource, '/practice/sessions/<int:id>/next-word')
api.add_resource(PracticeSummaryResource, '/practice/sessions/<int:id>/summary')
```

**Acceptance criteria**:
- All 4 routes are registered.
- `flask routes` command shows the new endpoints.
- App starts without import errors.

**Dependencies**: T-3.15.

---

### T-3.17: Backend manual smoke test

**Description**: Manually test the full session flow using curl or Postman.

**Test sequence**:
1. `POST /api/token` — login
2. `POST /api/practice/sessions` — start session, verify response shape
3. `POST /api/practice/sessions/<id>/messages` — send a sentence, verify feedback
4. `POST /api/practice/sessions/<id>/messages` — send another sentence (multi-attempt)
5. `POST /api/practice/sessions/<id>/next-word` — advance word, verify scores averaged
6. `POST /api/practice/sessions/<id>/next-word` — skip a word (no prior messages)
7. Repeat until session complete
8. `GET /api/practice/sessions/<id>/summary` — verify summary response
9. Check database: `SessionWordAttempt` rows, `SessionWord` scores, `Word.confidence_score` updated, `UserSession.summary_text` populated

**Acceptance criteria**:
- Full session flow works end-to-end.
- Scores are correctly averaged across attempts.
- Skipped words have no scores.
- Confidence scores update in the Word table.
- Summary is generated and saved.

**Dependencies**: T-3.16.

---

## Phase 4: Frontend

These tasks update the frontend to use real APIs. Must be done after Phase 3 (needs working endpoints).

---

### T-3.18: Add practice TypeScript types

**Description**: Add TypeScript interfaces for all practice-related API responses.

**Files affected**:
- `frontend/src/types/api.ts` — add interfaces

**Changes**:

Add after existing interfaces:
```typescript
export interface WordContext {
  word_id: number
  word: string
  pinyin: string
  meaning: string
}

export interface FeedbackData {
  grammarScore: number
  usageScore: number
  naturalnessScore: number
  isCorrect: boolean
  feedback: string
  corrections: string[]
  explanations: string[]
  exampleSentences: string[]
}

export interface PracticeSessionResponse {
  session: { id: number; session_start_ds: string; words_per_session: number }
  current_word: WordContext
  greeting_message: string
  words_practiced: number
  words_skipped: number
  words_total: number
  session_complete: boolean
}

export interface PracticeMessageResponse {
  laoshi_response: string
  feedback: FeedbackData | null
  current_word: WordContext | null
  words_practiced: number
  words_skipped: number
  words_total: number
  session_complete: boolean
  summary?: PracticeSummaryResponse
}

export interface WordResult {
  word: string
  grammar_score: number | null
  usage_score: number | null
  naturalness_score: number | null
  is_correct: boolean | null
  is_skipped: boolean
}

export interface PracticeSummaryResponse {
  session_id: number
  summary_text: string
  words_practiced: number
  words_skipped: number
  word_results: WordResult[]
}
```

**Acceptance criteria**:
- All interfaces exported and compile without errors.
- Types match the API response shapes defined in requirements.md.

**Dependencies**: None (can start as soon as Phase 3 response shapes are finalised).

---

### T-3.19: Add practiceApi helpers

**Description**: Add the `practiceApi` object to `lib/api.ts` with typed API helper functions.

**Files affected**:
- `frontend/src/lib/api.ts` — add exports

**Changes**:

Add imports at the top:
```typescript
import type {
  PracticeSessionResponse,
  PracticeMessageResponse,
  PracticeSummaryResponse,
} from '../types/api'
```

Add before `export default api`:
```typescript
export const practiceApi = {
  startSession: (wordsCount?: number) =>
    api.post<PracticeSessionResponse>(
      '/api/practice/sessions',
      wordsCount ? { words_count: wordsCount } : {}
    ),

  sendMessage: (sessionId: number, message: string) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/messages`,
      { message }
    ),

  nextWord: (sessionId: number) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/next-word`
    ),

  getSummary: (sessionId: number) =>
    api.get<PracticeSummaryResponse>(
      `/api/practice/sessions/${sessionId}/summary`
    ),
}
```

**Acceptance criteria**:
- `practiceApi` object is exported.
- All 4 methods exist with correct types.
- TypeScript compiles without errors.

**Dependencies**: T-3.18 (types).

---

### T-3.20: Rewrite Practice.tsx data flow

**Description**: Remove all mock data from Practice.tsx. Wire to real APIs with session lifecycle management.

**Files affected**:
- `frontend/src/pages/Practice.tsx` — major rewrite

**Key changes**:

1. **Remove**: `getMockWord()`, `WORDS_TO_PRACTICE` constant, all `catch` blocks with mock fallbacks.

2. **Add state**:
   ```typescript
   const [sessionId, setSessionId] = useState<number | null>(null)
   const [sessionPhase, setSessionPhase] = useState<'initializing' | 'practicing' | 'completed'>('initializing')
   const [wordsTotal, setWordsTotal] = useState(0)
   const [wordsPracticed, setWordsPracticed] = useState(0)
   const [wordsSkipped, setWordsSkipped] = useState(0)
   const [summary, setSummary] = useState<PracticeSummaryResponse | null>(null)
   const [isWaiting, setIsWaiting] = useState(false)
   ```

3. **On mount**: Call `practiceApi.startSession()`, store session ID, words_total, current word, display greeting message. Set `sessionPhase='practicing'`.

4. **handleSubmit**: Call `practiceApi.sendMessage(sessionId, inputText)`. Show typing indicator. On response: add laoshi message. If `feedback` is non-null, render `FeedbackCard`. Do NOT add to `practicedWords` — that happens on Next Word.

5. **handleNextWord** (replaces `handleSkip`): Call `practiceApi.nextWord(sessionId)`. Based on whether the current word had any messages (track locally), add to `practicedWords` or `skippedWords` in the sidebar. Update `currentWord` from response. If `session_complete=true`, transition to `sessionPhase='completed'` and set summary.

6. **wordsProgress**: Use `wordsPracticed`, `wordsSkipped`, and `wordsTotal` from API responses (not computed locally). Progress bar shows `(wordsPracticed + wordsSkipped) / wordsTotal` for overall progress.

7. **Rename "Skip this word" button text to "Next Word"**.

8. **Update `currentWord` type**: Use `WordContext` instead of `Word` (different shape — no `confidence_score`, `status`, `source_name`).

**Acceptance criteria**:
- No mock data remains in the file.
- Session starts via API on mount.
- Messages route through the real API.
- "Next Word" button advances via API.
- Progress bar uses API-provided counts.
- Session transitions to summary view when complete.
- `currentWord` uses `WordContext` type.

**Dependencies**: T-3.18, T-3.19, T-3.16 (working endpoints).

---

### T-3.21: Add typing indicator and loading states

**Description**: Add a typing indicator (animated dots) when waiting for agent responses. Disable Submit button during API calls.

**Files affected**:
- `frontend/src/pages/Practice.tsx` — add indicator logic

**Changes**:

1. When `isWaiting=true`, render a laoshi chat bubble with animated dots:
   ```tsx
   {isWaiting && (
     <div className="flex justify-start">
       <img src="/laoshi-logo.png" alt="Laoshi" className="w-8 h-8 rounded-full object-cover mr-3 mt-1" />
       <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-5 py-3 shadow-sm">
         <div className="flex gap-1">
           <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
           <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
           <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
         </div>
       </div>
     </div>
   )}
   ```

2. Disable Submit button when `isWaiting=true`:
   ```tsx
   <button
     onClick={handleSubmit}
     disabled={!inputText.trim() || isWaiting}
     className="..."
   >
   ```

3. Disable "Next Word" button when `isWaiting=true`.

4. Set `isWaiting=true` before API calls, `isWaiting=false` after (in finally block).

**Acceptance criteria**:
- Typing indicator appears during API calls.
- Submit and Next Word buttons are disabled during API calls.
- Indicator disappears when response arrives.
- 30-second timeout on API calls (via Axios config or AbortController).

**Dependencies**: T-3.20 (Practice.tsx rewrite).

---

### T-3.22: Create FeedbackCard component

**Description**: Create the FeedbackCard component that renders inside laoshi chat bubbles when feedback data exists.

**Files affected**:
- `frontend/src/components/FeedbackCard.tsx` (new file)

**Props**:
```typescript
interface FeedbackCardProps {
  feedback: FeedbackData
}
```

**Layout**:
- Score badges row: Grammar (X/10), Usage (X/10), Naturalness (X/10)
- isCorrect indicator: green checkmark or red X
- Feedback text paragraph
- Corrections list (if non-empty)
- Example sentences list (if non-empty)

**Styling**: Use the existing purple/gray/white palette. Score badges use colored backgrounds (green for 8+, yellow for 5-7, red for <5).

**Acceptance criteria**:
- Renders all feedback fields.
- Handles empty `corrections` and `exampleSentences` arrays gracefully.
- Score badges are color-coded.
- Component is self-contained (no external state).

**Dependencies**: T-3.18 (FeedbackData type).

---

### T-3.23: Create SessionSummary component

**Description**: Create the SessionSummary component shown when the session is complete.

**Files affected**:
- `frontend/src/components/SessionSummary.tsx` (new file)

**Props**:
```typescript
interface SessionSummaryProps {
  summary: PracticeSummaryResponse
  onNewSession: () => void
}
```

**Layout**:
- "Session Complete!" heading
- Summary prose text
- Word results table: Word | Grammar | Usage | Naturalness | Status (correct/skipped)
- Stats: "X practiced, Y skipped"
- Buttons: "Start New Session" (calls `onNewSession`), "Back to Home" (Link to `/home`)

**Acceptance criteria**:
- Renders summary text and word results table.
- Skipped words show "--" for scores.
- "Start New Session" calls `onNewSession` prop.
- "Back to Home" navigates to /home.
- Consistent with existing purple design system.

**Dependencies**: T-3.18 (PracticeSummaryResponse type).

---

## Phase 5: Tests & Verification

These tasks write tests and verify the full flow. Must be done after Phases 1–4.

---

### T-3.24: Backend unit tests for practice_runner

**Description**: Write unit tests for `practice_runner.py` with mocked agent calls.

**Files affected**:
- `backend/tests/test_practice_runner.py` (new file)

**Test cases**:

1. **initialize_session**: Words with `confidence_score >= 0.9` excluded. Returns error if no eligible words. Creates correct number of SessionWord rows. `word_order` is sequential.
2. **handle_message**: Creates SessionWordAttempt on feedback. Does NOT modify SessionWord. Returns null feedback for chat messages.
3. **advance_word with attempts**: Averages scores correctly. Writes to SessionWord. Updates Word.confidence_score. Sets is_correct based on averages.
4. **advance_word without attempts**: Sets is_skipped=True. Does NOT update confidence.
5. **complete_session**: Writes summary_text. Sets session_end_ds. Graceful fallback on agent failure.
6. **validate_feedback**: Rejects missing keys. Rejects out-of-range scores.
7. **update_confidence**: Formula matches user_evaluation.md. Clamps to [0, 1].
8. **extract_feedback_from_result**: Returns None when no tool calls. Parses valid feedback.

**Mocking**: Use `unittest.mock.patch` on `Runner.run` and `mem0_client`. Use TestConfig with SQLite in-memory.

**Acceptance criteria**:
- All test cases pass.
- `python -m pytest tests/test_practice_runner.py -v` passes.

**Dependencies**: T-3.10–T-3.14.

---

### T-3.25: Backend integration tests for practice API endpoints

**Description**: Write integration tests for the 4 practice API endpoints.

**Files affected**:
- `backend/tests/test_practice_resources.py` (new file)

**Test cases**:

1. **POST /practice/sessions**: Returns 201 with correct response shape. Returns 400 when no eligible words. JWT required.
2. **POST /practice/sessions/:id/messages**: Returns 200 with laoshi_response. Returns 400 when message missing. Returns 404 for wrong session. JWT required.
3. **POST /practice/sessions/:id/next-word**: Returns 200 with next word. Returns session_complete=true on last word. JWT required.
4. **GET /practice/sessions/:id/summary**: Returns word results. Returns 404 for non-existent session. JWT required.
5. **Ownership**: User A cannot access User B's session.

**Mocking**: Mock `Runner.run` to return pre-built results. Use TestConfig.

**Acceptance criteria**:
- All test cases pass.
- `python -m pytest tests/test_practice_resources.py -v` passes.

**Dependencies**: T-3.15, T-3.16.

---

### T-3.26: Frontend component tests

**Description**: Write component tests for FeedbackCard and SessionSummary.

**Files affected**:
- `frontend/src/test/FeedbackCard.test.tsx` (new file)
- `frontend/src/test/SessionSummary.test.tsx` (new file)

**FeedbackCard test cases**:
1. Renders score badges with correct values.
2. Renders isCorrect indicator (checkmark for true, X for false).
3. Renders feedback text.
4. Renders corrections when non-empty.
5. Handles empty corrections/examples arrays.

**SessionSummary test cases**:
1. Renders summary text.
2. Renders word results table with scores.
3. Shows "--" for skipped words.
4. "Start New Session" button calls onNewSession.
5. "Back to Home" link exists.

**Acceptance criteria**:
- All tests pass.
- `npm test -- --run` passes with no regressions.

**Dependencies**: T-3.22, T-3.23.

---

### T-3.27: End-to-end manual test

**Description**: Full session flow test with real AI APIs (no mocks).

**Test sequence**:
1. Login, navigate to Practice page.
2. Verify session starts: greeting message, first word card.
3. Submit 2 sentences for the first word. Verify feedback cards appear with scores.
4. Click "Next Word". Verify scores are averaged (check DB).
5. Click "Next Word" without submitting (skip). Verify word marked as skipped.
6. Complete remaining words.
7. Verify session summary appears with word results table.
8. Check database: `SessionWordAttempt` rows match attempts, `SessionWord` scores are averages, `Word.confidence_score` updated, `UserSession.summary_text` populated, `session_end_ds` set.
9. Check mem0: new memories written for the user.
10. Start a new session. Verify mem0 preferences are injected (greeting references past sessions).

**Acceptance criteria**:
- Full flow works end-to-end with real AI.
- All database writes are correct.
- mem0 persistence works across sessions.
- No console errors in browser.
- No unhandled exceptions in Flask logs.

**Dependencies**: All previous tasks.

---

## Execution Order Summary

```
Phase 1 (parallel):
  T-3.1   UserSession columns
  T-3.2   SessionWord columns
  T-3.2b  SessionWordAttempt model    (depends on T-3.2)
  T-3.4   Config constant             (independent)
  T-3.3   Alembic migration           (after T-3.1, T-3.2, T-3.2b)

Phase 2 (mostly sequential):
  T-3.5   Expand UserSessionContext    (independent)
  T-3.6   Rework Feedback Agent        (depends on T-3.5)
  T-3.8   Rework Summary Agent         (depends on T-3.5, parallel with T-3.6)
  T-3.7   Rework Orchestrator Agent    (depends on T-3.6, T-3.8)
  T-3.9   Clean up chat_agents.py      (after T-3.6, T-3.7, T-3.8)
  T-3.10  Practice runner scaffolding  (depends on T-3.5, models)
  T-3.11  initialize_session           (depends on T-3.10)
  T-3.12  handle_message               (depends on T-3.10)
  T-3.13  advance_word                 (depends on T-3.10, T-3.12)
  T-3.14  complete_session             (depends on T-3.10, T-3.13)

Phase 3 (sequential):
  T-3.15  practice_resources.py        (depends on T-3.11–T-3.14)
  T-3.16  Register in app.py           (depends on T-3.15)
  T-3.17  Manual smoke test            (depends on T-3.16)

Phase 4 (mixed parallelism):
  T-3.18  TypeScript types             (independent)
  T-3.19  practiceApi helpers           (depends on T-3.18)
  T-3.22  FeedbackCard component       (depends on T-3.18, parallel with T-3.19)
  T-3.23  SessionSummary component     (depends on T-3.18, parallel with T-3.19)
  T-3.20  Practice.tsx rewrite         (depends on T-3.19, T-3.22, T-3.23)
  T-3.21  Typing indicator             (depends on T-3.20)

Phase 5 (after all above):
  T-3.24  Backend unit tests           (parallel with T-3.25)
  T-3.25  Backend integration tests    (parallel with T-3.24)
  T-3.26  Frontend component tests     (parallel with T-3.24/25)
  T-3.27  End-to-end manual test       (after T-3.24–T-3.26)
```
