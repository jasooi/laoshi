# Milestone 3: AI Practice Sessions -- Design Document

## Design Overview

This document describes HOW the M3 practice session system will be implemented. The work spans the full stack: database model changes, AI agent rework, a new practice runner module, 4 new API endpoints, and frontend integration.

**What changes from the current codebase:**
- `UserSession` and `SessionWord` gain new columns; a new `SessionWordAttempt` table is added.
- The skeleton `ai_layer/` code (placeholder prompts, hardcoded dotenv paths, wrong persona, no handoff wiring) is replaced with production-ready agents.
- A new `practice_runner.py` becomes the central app-code layer between the API endpoints and the agents.
- `Practice.tsx` drops all mock data and wires to real APIs.
- Two new frontend components (`FeedbackCard`, `SessionSummary`) are created.

The guiding principles are:
1. **Agents never touch the DB or mem0 directly.** All reads/writes happen in app code. Agents receive a read-only context and return structured output.
2. **Defensive extraction.** Scores are parsed from the feedback agent's raw tool output, not from the orchestrator's conversational text.
3. **Per-turn Runner.run().** App code calls `Runner.run()` once per user message. No continuous agent loop.
4. **Single source of truth.** No JSON columns duplicating relational data. Word status is derived from `SessionWord` fields at runtime.

---

## Architecture & Approach

### End-to-End Data Flow

```
User clicks "Start Practice"
  |
  v
Frontend: practiceApi.startSession(wordsCount?)
  |
  | POST /api/practice/sessions
  v
Backend: PracticeSessionResource.post()
  |
  | 1. Query words where confidence_score < 0.9, random sample N
  | 2. Create UserSession + N SessionWord rows (word_order 0..N-1)
  | 3. Fetch mem0 preferences
  | 4. Hydrate UserSessionContext
  | 5. Runner.run(orchestrator) -> greeting message
  v
Response: { session, current_word, greeting_message, words_completed, words_total }
  |
  v
Frontend: display greeting + first word card
```

```
User submits a sentence
  |
  v
Frontend: practiceApi.sendMessage(sessionId, message)
  |
  | POST /api/practice/sessions/<id>/messages
  v
Backend: PracticeMessageResource.post()
  |
  | 1. Hydrate UserSessionContext (derive word status from SessionWord)
  | 2. Runner.run(orchestrator, input=message, session=redis_session)
  | 3. Orchestrator classifies intent:
  |    - Sentence attempt -> calls feedback_agent via evaluate_sentence tool
  |    - Chat/question -> responds conversationally
  | 4. Defensive extraction: parse scores from result.raw_responses tool outputs
  | 5. If feedback found: create SessionWordAttempt row (do NOT touch SessionWord)
  v
Response: { laoshi_response, feedback?, current_word, words_completed, words_total }
  |
  v
Frontend: display laoshi bubble + FeedbackCard (if feedback exists)
```

```
User clicks "Next Word"
  |
  v
Frontend: practiceApi.nextWord(sessionId)
  |
  | POST /api/practice/sessions/<id>/next-word
  v
Backend: PracticeNextWordResource.post()
  |
  | 1. Determine current word (first SessionWord where status == 0)
  | 2. Query SessionWordAttempt rows for this word+session
  | 3a. If attempts exist:
  |     - Average all attempt scores
  |     - Write averages to SessionWord
  |     - Compute is_correct from averages
  |     - Update Word.confidence_score via formula
  | 3b. If no attempts:
  |     - Set SessionWord.is_skipped = True
  | 4. Advance to next word by word_order
  | 5. Check if all words done -> session_complete
  | 6. If complete: trigger complete_session (summary agent handoff)
  | 7. If not: Runner.run() to introduce next word
  v
Response: { laoshi_response, current_word?, words_completed, words_total, session_complete, summary? }
```

### Agent Architecture

```
                    ┌──────────────────┐
                    │   App Code       │
                    │ (practice_runner) │
                    └────────┬─────────┘
                             │ Runner.run(orchestrator, input, context, session)
                             v
                    ┌──────────────────┐
                    │   Orchestrator   │  Gemini Flash
                    │  (laoshi-agent)  │  Sassy teacher persona
                    │                  │  Intent classification
                    └──┬──────────┬────┘
                       │          │
            tool call  │          │ handoff (session_complete=True)
                       v          v
              ┌─────────────┐  ┌────────────────┐
              │  Feedback    │  │  Summary       │
              │  Agent       │  │  Agent         │
              │  (DeepSeek)  │  │  (Gemini Flash)│
              │  Stateless   │  │  Returns JSON  │
              └─────────────┘  └────────────────┘
```

**Orchestrator** receives `UserSessionContext` and conversation history (via Redis). It decides whether the user input is a sentence attempt or a question. For sentences, it calls `evaluate_sentence` (feedback agent as tool). For questions, it answers directly. When `session_complete=True` in context, the prompt instructs the agent to hand off to the summary agent, which passes conversation history to the summary agent.

**Feedback Agent** is stateless. It receives the sentence + word details via the tool call input and its dynamic prompt. Returns structured JSON with scores, feedback, corrections, explanations, example sentences. The isCorrect threshold is `grammarScore == 10 AND usageScore >= 8`.

**Summary Agent** receives conversation history and word results via handoff. Returns JSON with `summary_text` and `mem0_updates`.

### Redis Session Management

```python
from agents import RedisSession

# Create session scoped to practice session ID
redis_session = RedisSession.from_url(
    session_id=f"session:{session.id}",
    url=os.getenv("REDIS_URI")
)

# Passed to Runner.run() on every turn
result = await Runner.run(
    orchestrator,
    input=message,
    context=ctx,
    session=redis_session
)
```

The SDK handles conversation history persistence. The Redis key is scoped per practice session. No manual cleanup needed -- Redis TTL or explicit deletion at session end.

### mem0 Integration

```
Session Start:
  mem0_client.search(query="language learning preferences", user_id=str(user_id))
  -> Inject stringified results into UserSessionContext.mem0_preferences
  -> Orchestrator's dynamic prompt references these preferences

Session End (via Summary Agent output):
  For each mem0_update in summary_agent_output.mem0_updates:
    mem0_client.add(mem0_update, user_id=str(user_id))
```

No per-turn mem0 operations. This prevents noisy low-signal entries.

---

## Backend Design

### 1. Database Model Changes (`backend/models.py`)

**UserSession -- add 2 columns:**
```python
class UserSession(db.Model):
    # ... existing columns ...
    summary_text = db.Column(db.Text, nullable=True)
    words_per_session = db.Column(db.Integer, nullable=False, default=10)
```

**SessionWord -- add 6 columns:**
```python
class SessionWord(db.Model):
    # ... existing columns (word_id, session_id, session_word_load_ds, is_skipped, session_notes) ...
    word_order = db.Column(db.Integer, nullable=False, default=0)
    grammar_score = db.Column(db.Float, nullable=True)      # averaged from attempts
    usage_score = db.Column(db.Float, nullable=True)         # averaged from attempts
    naturalness_score = db.Column(db.Float, nullable=True)   # averaged from attempts
    is_correct = db.Column(db.Boolean, nullable=True)        # from averaged scores
    status = db.Column(db.Integer, nullable=False, default=0)  # 0=pending, 1=completed, -1=skipped
```

**SessionWordAttempt -- new model:**
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
```

Add `attempts` relationship to SessionWord:
```python
class SessionWord(db.Model):
    # ...
    attempts = db.relationship('SessionWordAttempt', back_populates='session_word')
```

**Deriving session_word_dict** (uses explicit status column):
```python
def derive_session_word_dict(session_words):
    """Build {word_id: status} from SessionWord list. 1=completed, -1=skipped, 0=active."""
    result = {}
    for sw in sorted(session_words, key=lambda s: s.word_order):
        result[sw.word_id] = sw.status  # 0=pending, 1=completed, -1=skipped
    return result
```

### 2. UserSessionContext Expansion (`backend/ai_layer/context.py`)

```python
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

This dataclass is read-only. It is hydrated by app code before each `Runner.run()` call. Agents reference it for dynamic prompt generation.

### 3. Agent Rework (`backend/ai_layer/chat_agents.py`)

**3A. Dynamic prompt builders:**

Each agent gets a `build_*_prompt(ctx: UserSessionContext)` function that injects session data into the system prompt at runtime.

```python
def build_orchestrator_prompt(ctx: UserSessionContext) -> str:
    # Injects: student name, current word, progress, mem0 preferences
    # Persona: sassy-but-encouraging Mandarin teacher
    # Intent classification instructions
    # Handoff trigger: when session_complete=True
    ...

def build_feedback_prompt(ctx: UserSessionContext) -> str:
    # Injects: current word details (word, pinyin, meaning)
    # Scoring criteria and JSON output schema
    # isCorrect threshold: grammarScore == 10 AND usageScore >= 8
    ...

def build_summary_prompt(ctx: UserSessionContext) -> str:
    # Injects: student name, word roster with scores
    # Summary format: 2 positives, 1 improvement area
    # JSON output schema: {summary_text, mem0_updates}
    ...
```

**3B. Agent wiring:**

```python
# Feedback agent as tool on orchestrator
feedback_agent = Agent[UserSessionContext](
    name="feedback-agent",
    instructions=build_feedback_prompt,  # dynamic
    model=deepseek_model
)

# Summary agent as handoff target
summary_agent = Agent[UserSessionContext](
    name="summary-agent",
    instructions=build_summary_prompt,  # dynamic
    model=gemini_model
)

# Orchestrator with tool + handoff
laoshi_agent = Agent[UserSessionContext](
    name="laoshi-orchestrator",
    instructions=build_orchestrator_prompt,  # dynamic
    model=gemini_model,
    tools=[
        feedback_agent.as_tool(
            tool_name="evaluate_sentence",
            tool_description="Evaluate student's Mandarin sentence. Pass the sentence as input."
        )
    ],
    handoffs=[handoff(summary_agent)]
)
```

**3C. Cleanup:**
- Remove hardcoded dotenv path (`'C:/Users/Jasmine/...'`) -- use relative path or let the app-level dotenv handle it.
- Fix orchestrator prompt (currently says "English teacher" -- change to Mandarin teacher).

### 4. Practice Runner (`backend/ai_layer/practice_runner.py`)

This is the core app code. It manages session state, hydrates context, calls agents, and processes outputs. All DB writes and mem0 calls happen here -- never inside agents.

**Key functions:**

```python
async def _run_agent(agent, input, context, session):
    """Wrapper around Runner.run() with retry logic."""

def run_async(coro):
    """Wraps async Runner.run() for sync Flask using asyncio.run()."""

def initialize_session(user_id, words_count=None):
    """
    1. Resolve words_count (param or DEFAULT_WORDS_PER_SESSION)
    2. Query words where confidence_score < 0.9, random sample
    3. Create UserSession + SessionWord rows
    4. Fetch mem0 preferences
    5. Hydrate UserSessionContext
    6. Runner.run(orchestrator) for greeting
    7. Return session data + first word + greeting
    """

def handle_message(session_id, user_id, message):
    """
    1. Load session, verify ownership
    2. Derive word status from SessionWord, hydrate context
    3. Runner.run(orchestrator, input=message, session=redis_session)
    4. Defensive score extraction from result.raw_responses
    5. If feedback: create SessionWordAttempt (NOT SessionWord)
    6. Return response + feedback + progress
    """

def advance_word(session_id, user_id):
    """
    1. Determine current word (first by word_order where status == 0)
    2. Query SessionWordAttempt for this word
    3. If attempts: average scores, write to SessionWord, update confidence
    4. If no attempts: set is_skipped=True
    5. Advance to next word, check completion
    6. If complete: trigger complete_session
    7. If not: Runner.run() to introduce next word
    """

def complete_session(session_id, user_id):
    """
    1. Hydrate context with session_complete=True
    2. Runner.run() -> orchestrator hands off to summary agent
    3. Parse summary JSON
    4. Write summary_text to UserSession
    5. Write mem0 updates
    6. Set session_end_ds
    """
```

**Defensive score extraction:**

```python
def extract_feedback_from_result(result):
    """
    Parse feedback JSON from result.raw_responses tool call outputs.
    NOT from orchestrator text (prevents hallucinated scores).

    Returns parsed dict or None if no feedback tool call found.
    """
    for response in result.raw_responses:
        for choice in response.choices:
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    if tc.function.name == "evaluate_sentence":
                        return validate_feedback(json.loads(tc.function.arguments))
    return None
```

**Confidence score update:**

```python
def update_confidence(word, avg_grammar, avg_usage, avg_naturalness, is_correct):
    """Apply confidence formula from user_evaluation.md."""
    correctness_factor = 1.0 if is_correct else -0.5
    quality_multiplier = (0.4 * avg_grammar + 0.4 * avg_usage + 0.2 * avg_naturalness) / 10.0
    learning_rate = 0.1
    new_score = word.confidence_score + correctness_factor * quality_multiplier * learning_rate
    new_score = max(0.0, min(1.0, new_score))  # clamp
    word.update_confidence_score(new_score)
```

### 5. API Endpoints (`backend/practice_resources.py`)

All endpoints are JWT-protected via `@jwt_required()`.

| Resource | Endpoint | Method | Runner function |
|----------|----------|--------|-----------------|
| `PracticeSessionResource` | `/api/practice/sessions` | POST | `initialize_session()` |
| `PracticeMessageResource` | `/api/practice/sessions/<int:id>/messages` | POST | `handle_message()` |
| `PracticeNextWordResource` | `/api/practice/sessions/<int:id>/next-word` | POST | `advance_word()` |
| `PracticeSummaryResource` | `/api/practice/sessions/<int:id>/summary` | GET | DB query |

Each resource:
1. Extracts JWT identity via `get_jwt_identity()`
2. Validates ownership
3. Delegates to the appropriate practice_runner function
4. Returns JSON response

**Registration in `app.py`:**
```python
from practice_resources import (
    PracticeSessionResource,
    PracticeMessageResource,
    PracticeNextWordResource,
    PracticeSummaryResource
)

# Inside register_resources():
api.add_resource(PracticeSessionResource, '/practice/sessions')
api.add_resource(PracticeMessageResource, '/practice/sessions/<int:id>/messages')
api.add_resource(PracticeNextWordResource, '/practice/sessions/<int:id>/next-word')
api.add_resource(PracticeSummaryResource, '/practice/sessions/<int:id>/summary')
```

**Config addition (`backend/config.py`):**
```python
class Config():
    # ... existing ...
    DEFAULT_WORDS_PER_SESSION = 10
```

### 6. Async Bridge

Flask is synchronous. The OpenAI Agents SDK's `Runner.run()` is async. Bridge via:

```python
import asyncio

def run_async(coro):
    """Run an async coroutine from synchronous Flask code."""
    return asyncio.run(coro)
```

Each HTTP request gets its own event loop. This is safe for Flask's request-per-thread model.

---

## Frontend Design

### 1. TypeScript Types (`frontend/src/types/api.ts`)

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
  words_completed: number
  words_total: number
  session_complete: boolean
}

export interface PracticeMessageResponse {
  laoshi_response: string
  feedback: FeedbackData | null
  current_word: WordContext | null
  words_completed: number
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

### 2. API Helpers (`frontend/src/lib/api.ts`)

```typescript
export const practiceApi = {
  startSession: (wordsCount?: number) =>
    api.post<PracticeSessionResponse>('/api/practice/sessions',
      wordsCount ? { words_count: wordsCount } : {}),

  sendMessage: (sessionId: number, message: string) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/messages`, { message }),

  nextWord: (sessionId: number) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/next-word`),

  getSummary: (sessionId: number) =>
    api.get<PracticeSummaryResponse>(
      `/api/practice/sessions/${sessionId}/summary`),
}
```

### 3. Practice.tsx Rewrite

**State structure:**
```typescript
const [sessionId, setSessionId] = useState<number | null>(null)
const [sessionPhase, setSessionPhase] = useState<'initializing' | 'practicing' | 'completed'>('initializing')
const [currentWord, setCurrentWord] = useState<WordContext | null>(null)
const [messages, setMessages] = useState<Message[]>([])
const [wordsPracticed, setWordsPracticed] = useState(0)
const [wordsSkipped, setWordsSkipped] = useState(0)
const [wordsTotal, setWordsTotal] = useState(0)
const [practicedWords, setPracticedWords] = useState<WordContext[]>([])
const [skippedWords, setSkippedWords] = useState<WordContext[]>([])
const [isWaiting, setIsWaiting] = useState(false)  // typing indicator
const [summary, setSummary] = useState<PracticeSummaryResponse | null>(null)
```

**Key changes from current implementation:**
- Remove `getMockWord()`, `WORDS_TO_PRACTICE`, all fallback catch blocks.
- On mount: call `practiceApi.startSession()`, store `sessionId` and `wordsTotal`.
- `handleSubmit`: call `practiceApi.sendMessage()`, show typing indicator, display response. If `feedback` is non-null, render `FeedbackCard` in the chat. Do NOT advance word.
- `handleNextWord` (renamed from `handleSkip`): call `practiceApi.nextWord()`. Update sidebar trays based on whether the word had attempts (completed) or not (skipped). If `session_complete=true`, transition to summary view.
- Submit button disabled when `isWaiting=true`.
- Typing indicator (3 animated dots in a laoshi bubble) when `isWaiting=true`.

**Session lifecycle:**
```
initializing -> practiceApi.startSession() -> practicing -> all words done -> completed
```

**"Next Word" button label:** Replaces "Skip this word" text. The button always says "Next Word". The backend determines whether the word was practiced or skipped based on `SessionWordAttempt` existence.

### 4. FeedbackCard Component (`frontend/src/components/FeedbackCard.tsx`)

Renders inside a laoshi chat bubble when `message.feedback` exists.

```
┌─────────────────────────────────────────┐
│  ┌──────┐ ┌──────┐ ┌──────────────┐    │
│  │ 9/10 │ │ 8/10 │ │ 7/10         │    │  Score badges
│  │Grammar│ │Usage │ │Naturalness   │    │
│  └──────┘ └──────┘ └──────────────┘    │
│                                         │
│  ✓ Correct  /  ✗ Needs improvement     │  isCorrect indicator
│                                         │
│  Feedback text...                       │
│                                         │
│  Corrections:                           │
│  • "Consider using 每天都..."           │
│                                         │
│  Example sentences:                     │
│  • 我每天都学习中文。                    │
│  • 她每天学习两个小时。                  │
└─────────────────────────────────────────┘
```

Props: `{ feedback: FeedbackData }`

### 5. SessionSummary Component (`frontend/src/components/SessionSummary.tsx`)

Replaces the chat view when `sessionPhase === 'completed'`.

```
┌───────────────────────────────────────┐
│         Session Complete!             │
│                                       │
│  Summary prose from AI...             │
│                                       │
│  ┌───────────────────────────────┐    │
│  │ Word   │ Grammar │ Usage │ ✓ │    │
│  │ 学习   │  9.5    │  8.0  │ ✗ │    │
│  │ 开心   │  10     │  9.0  │ ✓ │    │
│  │ 再见   │  --     │  --   │ ⏭ │    │  (skipped)
│  └───────────────────────────────┘    │
│                                       │
│  8 practiced, 2 skipped               │
│                                       │
│  [Start New Session]  [Back to Home]  │
└───────────────────────────────────────┘
```

Props: `{ summary: PracticeSummaryResponse, onNewSession: () => void }`

---

## Error Handling

### Backend

| Scenario | Handling |
|----------|----------|
| Feedback agent returns malformed JSON | Return "I had trouble evaluating that, try again". Do NOT write to DB. |
| Summary agent fails | Write generic summary ("Session completed. Keep practicing!"). Still close session. |
| Runner.run() network error | Retry with exponential backoff (3 attempts). If all fail, return 500 with user-friendly error. |
| No eligible words for practice | Return 400 with descriptive error message. |
| Session not found or not owned | Return 404. |
| Message sent to completed session | Return 400 "Session is already complete". |

### Frontend

| Scenario | Handling |
|----------|----------|
| API call in progress | Typing indicator + disabled Submit button. |
| Network/500 error | Error toast. User can retry by resubmitting. |
| Timeout (30s) | Cancel request, show error toast. |
| No words available | Display error message with link to vocabulary import. |

---

## File Changes Summary

| File | Type | Description |
|------|------|-------------|
| `backend/models.py` | Modify | Add columns to UserSession, SessionWord; add SessionWordAttempt model |
| `backend/config.py` | Modify | Add `DEFAULT_WORDS_PER_SESSION = 10` |
| `backend/ai_layer/context.py` | Modify | Expand UserSessionContext, add WordContext |
| `backend/ai_layer/chat_agents.py` | Modify | Dynamic prompts, handoff wiring, fix persona, clean dotenv |
| `backend/ai_layer/practice_runner.py` | New | Session init, message handling, advance_word, complete_session |
| `backend/practice_resources.py` | New | 4 Flask-RESTful resources |
| `backend/app.py` | Modify | Register 4 new resources |
| `frontend/src/types/api.ts` | Modify | Add practice-related interfaces |
| `frontend/src/lib/api.ts` | Modify | Add `practiceApi` object |
| `frontend/src/pages/Practice.tsx` | Modify | Remove mocks, wire to real APIs, session lifecycle |
| `frontend/src/components/FeedbackCard.tsx` | New | Score badges + feedback display |
| `frontend/src/components/SessionSummary.tsx` | New | End-of-session summary view |

---

## Testing Strategy

### Backend

| Test file | Scope | Key test cases |
|-----------|-------|----------------|
| `test_practice_models.py` | Unit: new models | SessionWordAttempt creation, composite FK, format_data on updated models |
| `test_practice_runner.py` | Unit: practice_runner | Session init (word selection, edge cases), handle_message (with/without feedback), advance_word (with attempts / no attempts / averaging), complete_session, confidence formula, defensive extraction |
| `test_practice_resources.py` | Integration: API endpoints | All 4 endpoints, JWT auth, ownership checks, error responses |

Agent calls are mocked in unit tests using `unittest.mock.patch` on `Runner.run()`. The mock returns pre-built result objects with known scores.

### Frontend

| Test file | Scope | Key test cases |
|-----------|-------|----------------|
| `FeedbackCard.test.tsx` | Component | Renders scores, corrections, examples; handles missing optional fields |
| `SessionSummary.test.tsx` | Component | Renders summary text, word results table, buttons |
| `Practice.test.tsx` | Integration | Session lifecycle, message sending, next word flow, summary transition |

API calls mocked via `vi.mock('../lib/api')` or MSW.
