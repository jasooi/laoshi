# Milestone 3: AI Practice Sessions -- Requirements Document

## Feature Overview

Milestone 3 delivers the core learning experience: AI-coached practice sessions where users form Mandarin sentences with vocabulary words and receive real-time evaluation from a multi-agent AI system. This is the centrepiece of Laoshi.

**What already exists:**
- Frontend `Practice.tsx` with UI shell: word card (toggle pinyin/definition), chat interface, "Next Word" button, progress bar, practiced/skipped word trays. All currently wired to mock data.
- Backend `ai_layer/` with skeleton files: `chat_agents.py` (3 agent definitions with placeholder prompts), `context.py` (minimal 2-field dataclass), `chat_service.py` (Redis stub), `mem0_setup.py` (working mem0 client with custom categories).
- Database models: `UserSession` (id, start/end timestamps, user_id), `SessionWord` (composite PK word_id+session_id, is_skipped, session_notes).

**What this milestone delivers:**
1. **Database model changes**: New columns on `UserSession` and `SessionWord`, new `SessionWordAttempt` table, Alembic migration.
2. **AI agent rework**: Dynamic prompts for all 3 agents (orchestrator, feedback, summary), proper tool/handoff wiring via OpenAI Agents SDK.
3. **Practice runner**: Core app code that initialises sessions, handles messages, manages per-attempt scoring, advances words, computes averaged scores, updates confidence, and triggers session completion.
4. **Practice API endpoints**: 4 new Flask-RESTful resources for the full session flow.
5. **Frontend integration**: Remove all mock data, wire Practice.tsx to real APIs, add FeedbackCard and SessionSummary components.

This milestone maps to **PRD User Stories**: #8 (start practice session), #9 (AI flashcard + sentence prompt), #10 (AI evaluates naturalness), #11 (detailed feedback), #12 (skip/next word), #13 (toggle pinyin/definition), #17 (confidence scores per word).

---

## User Stories

### US-01: Start a practice session
**As a** learner with vocabulary loaded, **I want** to start a practice session **so that** I can practice forming sentences with my words.

**Acceptance Criteria:**
- Clicking "Start Practice" on the Home page navigates to the Practice page and starts a session automatically.
- The backend selects up to `words_per_session` words randomly from my vocabulary where `confidence_score < 0.9` (excluding mastered words).
- If I have no eligible words (all mastered or none imported), I see an error message instead of a blank session.
- The AI coach (Laoshi) sends an initial greeting message.
- The first vocabulary word appears on the flashcard.
- The progress bar shows "1 / N words".

### US-02: Submit a sentence for evaluation
**As a** learner viewing a word on the flashcard, **I want** to type a Mandarin sentence using that word and receive AI feedback **so that** I learn whether my sentence is natural and correct.

**Acceptance Criteria:**
- I type a sentence in the text input and press Enter or click Submit.
- A typing indicator (animated dots) appears while the AI processes my sentence.
- The Submit button is disabled during processing.
- The AI coach responds with feedback including:
  - Grammar score (1-10)
  - Usage score (1-10)
  - Naturalness score (1-10)
  - Whether the sentence is correct (`grammarScore == 10 AND usageScore >= 8`)
  - Specific corrections if needed
  - Explanations of mistakes
  - 2-3 example sentences using the word correctly
- Feedback is displayed in a structured FeedbackCard within the chat.
- My attempt is recorded in the database (`SessionWordAttempt` table).
- I can submit multiple sentences for the same word (multi-attempt).

### US-03: Chat with Laoshi
**As a** learner, **I want** to ask Laoshi questions or chat freely during a practice session **so that** I can get help understanding a word or ask for clarification.

**Acceptance Criteria:**
- If I type a question or general message (not a sentence attempt), Laoshi responds conversationally without triggering the evaluation flow.
- The orchestrator agent classifies my intent and responds appropriately.
- Chat messages do not create `SessionWordAttempt` records.

### US-04: Advance to the next word
**As a** learner, **I want** to click "Next Word" to move to the next vocabulary word **so that** I can progress through the session.

**Acceptance Criteria:**
- Clicking "Next Word" after submitting one or more sentences:
  - Averages all attempt scores for that word (grammar, usage, naturalness).
  - Determines `is_correct` from averaged scores: `avgGrammarScore == 10 AND avgUsageScore >= 8`.
  - Writes averaged scores to the `SessionWord` record.
  - Updates the word's `confidence_score` using the confidence formula.
  - Marks the word as completed (`status=1`, `is_correct` set based on scores).
  - Increments `words_practiced` count.
  - Advances the flashcard to the next word.
- Clicking "Next Word" without having submitted any sentences:
  - Marks the word as skipped (`status=-1`, `is_skipped=True`).
  - Does NOT update confidence score.
  - Increments `words_skipped` count.
  - Advances to the next word.
- The progress bar updates to reflect the new position.
- The practiced/skipped words trays in the sidebar update accordingly.
- The AI coach introduces the next word.

### US-05: Complete a practice session
**As a** learner, **I want** the session to end when all words have been practiced or skipped **so that** I get a summary of my performance.

**Acceptance Criteria:**
- The session completes when every word has status != 0 (all completed or skipped).
- At session end, the Summary Agent generates a summary with:
  - 2 specific positives referencing actual words/phrases from the session.
  - 1 specific area for improvement referencing actual mistakes.
- The summary is displayed in a SessionSummary component.
- The summary shows a word results table (word, scores, correct/skipped).
- "Start New Session" and "Back to Home" buttons are available.
- The session's `session_end_ds` is set and `summary_text` is saved.
- mem0 persistent memory is updated with learning patterns from the session.

### US-06: Toggle pinyin and translation on the flashcard
**As a** learner, **I want** to show or hide pinyin and English translation on the word flashcard **so that** I can challenge myself at different difficulty levels.

**Acceptance Criteria:**
- Toggle buttons for pinyin and translation exist on the flashcard (already implemented).
- Toggling does not affect the session state or API calls.

### US-07: View word confidence after practice
**As a** learner, **I want** my word confidence scores to update based on my practice performance **so that** I can track my progress.

**Acceptance Criteria:**
- After clicking "Next Word" for a practiced word, the word's `confidence_score` in the database is updated using the formula:
  ```
  correctnessFactor = 1.0 if isCorrect else -0.5
  qualityMultiplier = (0.4 * avgGrammar + 0.4 * avgUsage + 0.2 * avgNaturalness) / 10.0
  learningRate = 0.1
  newScore = clamp(currentScore + correctnessFactor * qualityMultiplier * learningRate, 0.0, 1.0)
  ```
- Skipped words have no confidence change.
- The status label (Learning, Reviewing, Mastered, Needs Revision) updates based on the new score.

---

## Functional Requirements

### Session Lifecycle -- Backend

**FR-001**: `POST /api/practice/sessions` MUST create a new `UserSession` with `session_start_ds=now`, `words_per_session=N`, and N `SessionWord` rows with `word_order=0..N-1`.

**FR-002**: Word selection MUST randomly sample from the user's words where `confidence_score < 0.9`. If no eligible words exist, return 400 with an error message.

**FR-003**: The `words_count` parameter in `POST /api/practice/sessions` body is optional. If omitted, fall back to `DEFAULT_WORDS_PER_SESSION` (10) from config.

**FR-004**: `POST /api/practice/sessions` MUST fetch mem0 preferences for the user and inject them into the agent context for the initial greeting.

**FR-005**: `POST /api/practice/sessions` MUST return `{session, current_word, greeting_message, words_practiced, words_skipped, words_total, session_complete}`.

### Message Handling -- Backend

**FR-006**: `POST /api/practice/sessions/<id>/messages` MUST accept `{message: string}` and route through the orchestrator agent via `Runner.run()`.

**FR-007**: Defensive score extraction: feedback scores MUST be extracted from the feedback agent's raw tool output in `result.raw_responses`, NOT from the orchestrator's text response.

**FR-008**: When feedback is extracted, a `SessionWordAttempt` row MUST be created with: the sentence, per-attempt scores (grammar, usage, naturalness), per-attempt `is_correct`, feedback text, and incrementing `attempt_number`.

**FR-009**: `handle_message` MUST NOT write scores to `SessionWord` or update `Word.confidence_score`. These are deferred to `advance_word`.

**FR-010**: `POST /api/practice/sessions/<id>/messages` MUST return `{laoshi_response, feedback (nullable), current_word, words_practiced, words_skipped, words_total, session_complete}`.

### Next Word / Advance -- Backend

**FR-011**: `POST /api/practice/sessions/<id>/next-word` MUST determine the current word (first `SessionWord` by `word_order` where status == 0).

**FR-012**: If `SessionWordAttempt` rows exist for the current word:
- Compute `avgGrammar = mean(all grammar_scores)`, `avgUsage = mean(all usage_scores)`, `avgNaturalness = mean(all naturalness_scores)`.
- Write averages to `SessionWord.grammar_score`, `usage_score`, `naturalness_score`.
- Set `SessionWord.is_correct` based on `avgGrammar == 10 AND avgUsage >= 8`.
- Update `Word.confidence_score` using the confidence formula.

**FR-013**: If no `SessionWordAttempt` rows exist for the current word:
- Set `SessionWord.is_skipped = True`.
- Do NOT update `Word.confidence_score`.

**FR-014**: After scoring/skipping, advance to the next word by `word_order` where status == 0.

**FR-015**: Check session completion: session is complete when ALL `SessionWord` rows have status != 0 (all completed or skipped).

**FR-016**: If session is complete, trigger `complete_session` flow (Summary Agent handoff, mem0 writes, set `session_end_ds`).

### Session Summary -- Backend

**FR-017**: `complete_session` MUST trigger the orchestrator-to-summary-agent handoff via the SDK's `handoff()` function.

**FR-018**: The summary agent's output MUST be parsed for `{summary_text, mem0_updates}` JSON.

**FR-019**: `summary_text` MUST be written to `UserSession.summary_text`.

**FR-020**: `mem0_updates` MUST be written via `mem0_client.add()` for each recommended memory update.

**FR-021**: `GET /api/practice/sessions/<id>/summary` MUST return `{session_id, summary_text, words_completed, words_skipped, word_results[]}`.

### Agent Behaviour -- Backend

**FR-022**: The orchestrator agent MUST classify user input as either a sentence attempt or a chat/question.

**FR-023**: For sentence attempts, the orchestrator MUST call the feedback agent via the `evaluate_sentence` tool.

**FR-024**: For chat/questions, the orchestrator MUST respond conversationally without calling the feedback agent.

**FR-025**: The orchestrator MUST have a sassy-but-encouraging Mandarin teacher persona (NOT "English teacher").

**FR-026**: The feedback agent MUST return structured JSON: `{grammarScore, usageScore, naturalnessScore, isCorrect, feedback, corrections, explanations, exampleSentences}`.

**FR-027**: The feedback agent `isCorrect` threshold: `grammarScore == 10 AND usageScore >= 8`.

**FR-028**: The summary agent MUST produce a summary with 2 specific positives and 1 area for improvement, referencing actual session content.

**FR-029**: All agent calls MUST use retry with exponential backoff (max 3 attempts).

**FR-030**: All agent JSON outputs MUST be validated against expected schemas before DB writes. Malformed output MUST NOT be written to the database.

### Database Models -- Backend

**FR-031**: `UserSession` model MUST have new columns: `summary_text` (Text, nullable), `words_per_session` (Integer, not null, default 10).

**FR-032**: `SessionWord` model MUST have new columns: `word_order` (Integer, not null), `grammar_score` (Float, nullable), `usage_score` (Float, nullable), `naturalness_score` (Float, nullable), `is_correct` (Boolean, nullable), `status` (Integer, not null, default 0). Status values: 0=pending, 1=completed, -1=skipped.

**FR-033**: New `SessionWordAttempt` model MUST have: `attempt_id` (PK, auto-increment), `word_id` + `session_id` (composite FK to SessionWord), `attempt_number` (Integer), `sentence` (Text), `grammar_score` (Float), `usage_score` (Float), `naturalness_score` (Float), `is_correct` (Boolean), `feedback_text` (Text), `created_ds` (DateTime).

**FR-034**: `format_data()` methods on `UserSession` and `SessionWord` MUST be updated to include the new columns.

### Configuration -- Backend

**FR-035**: `config.py` MUST have `DEFAULT_WORDS_PER_SESSION = 10`.

**FR-036**: `REDIS_URI` MUST NOT be added to `config.py`. It MUST be read via `os.getenv("REDIS_URI")` in `ai_layer/` code only.

### Frontend -- Types

**FR-037**: `types/api.ts` MUST include: `WordContext`, `PracticeSessionResponse`, `FeedbackData`, `PracticeMessageResponse`, `PracticeSummaryResponse`.

### Frontend -- API Helpers

**FR-038**: `lib/api.ts` MUST export a `practiceApi` object with: `startSession(wordsCount?)`, `sendMessage(sessionId, message)`, `nextWord(sessionId)`, `getSummary(sessionId)`.

### Frontend -- Practice Page

**FR-039**: `Practice.tsx` MUST remove all mock data: `getMockWord()`, `WORDS_TO_PRACTICE` constant, fallback catch blocks.

**FR-040**: `Practice.tsx` MUST manage session lifecycle with a `sessionPhase` state: `initializing` | `practicing` | `completed`.

**FR-041**: On mount, `Practice.tsx` MUST call `practiceApi.startSession()` and store the session ID and `words_total` from the response.

**FR-042**: `handleSubmit` MUST call `practiceApi.sendMessage()` and display the structured response (feedback card if evaluation, text if chat).

**FR-043**: `handleNextWord` MUST call `practiceApi.nextWord()` and update the UI with the next word or transition to summary.

**FR-044**: A typing indicator (animated dots) MUST appear while waiting for agent responses.

**FR-045**: The Submit button MUST be disabled during API calls.

**FR-046**: When `session_complete=true`, the UI MUST transition to the SessionSummary view.

### Frontend -- Components

**FR-047**: `FeedbackCard.tsx` MUST render inside laoshi chat bubbles when feedback data exists. It MUST show score badges (grammar, usage, naturalness), corrections, and example sentences.

**FR-048**: `SessionSummary.tsx` MUST render the end-of-session view with: summary prose, word results table, "Start New Session" and "Back to Home" buttons.

---

## Non-Functional Requirements

**NFR-001**: Agent calls (DeepSeek, Gemini Flash) may take 3-10 seconds. The frontend MUST show a typing indicator during this time.

**NFR-002**: Frontend MUST implement a 30-second timeout for API calls to practice endpoints.

**NFR-003**: Backend MUST implement retry with exponential backoff (max 3 attempts) for all `Runner.run()` calls.

**NFR-004**: If the feedback agent returns malformed JSON, the backend MUST return a user-friendly error ("I had trouble evaluating that, try again") and NOT write bad data to the database.

**NFR-005**: If the summary agent fails, the backend MUST write a generic summary and still close the session gracefully.

**NFR-006**: Conversation history MUST be stored in Redis via the SDK's `RedisSession`, keyed by session ID. MUST be cleared at session end.

**NFR-007**: mem0 reads MUST happen at session start only. mem0 writes MUST happen at session end only. No per-turn mem0 operations.

---

## API Requirements

### AR-001: Start Practice Session

**Request**: `POST /api/practice/sessions`
```json
{
  "words_count": 10  // optional, defaults to DEFAULT_WORDS_PER_SESSION
}
```

**Success response (201)**:
```json
{
  "session": {
    "id": 42,
    "session_start_ds": "2026-02-21T10:30:00Z",
    "words_per_session": 10
  },
  "current_word": {
    "word_id": 7,
    "word": "学习",
    "pinyin": "xue2 xi2",
    "meaning": "to study, to learn"
  },
  "greeting_message": "嘿！Ready to practice? Let's see what you've got today...",
  "words_practiced": 0,
  "words_skipped": 0,
  "words_total": 10,
  "session_complete": false
}
```

**Error response (400)** -- no eligible words:
```json
{
  "error": "No eligible words for practice. All your words are mastered or you have no vocabulary imported."
}
```

### AR-002: Send Message

**Request**: `POST /api/practice/sessions/<id>/messages`
```json
{
  "message": "我每天学习中文。"
}
```

**Success response (200)** -- with evaluation:
```json
{
  "laoshi_response": "Not bad! Your sentence structure is good, but let me give you some tips...",
  "feedback": {
    "grammarScore": 9,
    "usageScore": 8,
    "naturalnessScore": 7,
    "isCorrect": false,
    "feedback": "The sentence is grammatically sound but...",
    "corrections": ["Consider using 每天都 for emphasis..."],
    "explanations": ["In natural speech, 都 is often added..."],
    "exampleSentences": ["我每天都学习中文。", "她每天学习两个小时。"]
  },
  "current_word": {
    "word_id": 7,
    "word": "学习",
    "pinyin": "xue2 xi2",
    "meaning": "to study, to learn"
  },
  "words_practiced": 0,
  "words_skipped": 0,
  "words_total": 10,
  "session_complete": false
}
```

**Success response (200)** -- chat (no evaluation):
```json
{
  "laoshi_response": "Good question! 学习 is used when...",
  "feedback": null,
  "current_word": { ... },
  "words_practiced": 0,
  "words_skipped": 0,
  "words_total": 10,
  "session_complete": false
}
```

### AR-003: Next Word

**Request**: `POST /api/practice/sessions/<id>/next-word`

No request body.

**Success response (200)** -- next word available:
```json
{
  "laoshi_response": "Alright, moving on! Let's try this one...",
  "feedback": null,
  "current_word": {
    "word_id": 15,
    "word": "开心",
    "pinyin": "kai1 xin1",
    "meaning": "happy, joyful"
  },
  "words_practiced": 1,
  "words_skipped": 0,
  "words_total": 10,
  "session_complete": false
}
```

**Success response (200)** -- session complete:
```json
{
  "laoshi_response": "Great session! Let me put together a summary for you...",
  "feedback": null,
  "current_word": null,
  "words_practiced": 8,
  "words_skipped": 2,
  "words_total": 10,
  "session_complete": true,
  "summary": {
    "summary_text": "You did really well with 学习 and 开心 today...",
    "words_practiced": 8,
    "words_skipped": 2,
    "word_results": [
      { "word": "学习", "grammar_score": 9.5, "usage_score": 8.0, "naturalness_score": 7.5, "is_correct": false, "is_skipped": false },
      { "word": "开心", "grammar_score": 10, "usage_score": 9, "naturalness_score": 8, "is_correct": true, "is_skipped": false }
    ]
  }
}
```

### AR-004: Get Summary

**Request**: `GET /api/practice/sessions/<id>/summary`

**Success response (200)**:
```json
{
  "session_id": 42,
  "summary_text": "You did really well with 学习 and 开心 today...",
  "words_completed": 8,
  "words_skipped": 2,
  "word_results": [
    { "word": "学习", "grammar_score": 9.5, "usage_score": 8.0, "naturalness_score": 7.5, "is_correct": false, "is_skipped": false },
    { "word": "开心", "grammar_score": 10, "usage_score": 9, "naturalness_score": 8, "is_correct": true, "is_skipped": false }
  ]
}
```

**Error response (404)** -- session not found or not owned:
```json
{
  "error": "Session not found"
}
```

---

## Out of Scope

The following items are explicitly NOT part of Milestone 3:

1. **Collection-based session start** (PRD story #8 full). M3 selects words from the user's entire vocabulary. Collection filtering is M5.
2. **Saved sentences** (PRD story #14). Users cannot save correct sentences to words yet. This is M6.
3. **BYOK API keys**. M3 uses the app's default free-tier API keys. BYOK is M4.
4. **Configurable words per session via Settings UI**. The backend supports a `words_count` parameter, but the Settings page is M4. M3 uses the default (10).
5. **Spaced repetition algorithm (SM-2)**. Word selection is random (excluding mastered). SM-2 is Phase 3.
6. **Main/backup LLM fallback**. DeepSeek is used for feedback, Gemini Flash for orchestrator/summary. No automatic fallback between providers.
7. **Voice input/output**. Text-only interaction for M3.
8. **Mobile-responsive practice layout**. Desktop viewport (1024px+) only.

---

## Decisions Log

**DL-001**: Multi-attempt scoring with averaging. Rather than using only the last attempt's scores, all attempts for a word are averaged when "Next Word" is clicked. This rewards consistent practice over lucky single attempts.

**DL-002**: SessionWordAttempt as a separate table (not JSON on SessionWord). This maintains relational integrity, enables per-attempt querying, and avoids JSON parsing overhead.

**DL-003**: `isCorrect` threshold: `grammarScore == 10 AND usageScore >= 8`. Grammar must be perfect (wrong grammar is never "correct"), but usage allows minor imperfections (a technically correct but slightly unnatural usage can still be acceptable).

**DL-004**: No `word_dict` JSON column on UserSession. Word ordering and status are derived from `SessionWord` rows at runtime. Single source of truth.

**DL-005**: Session completion is gated by all words having status != 0 (completed or skipped). It is NOT gated by `isCorrect` -- a word can be attempted, scored below the threshold, and still counted as completed when "Next Word" is clicked.

**DL-006**: REDIS_URI stays in `.env` only (contains credentials). Not added to `config.py`. Read via `os.getenv()` in ai_layer code.

**DL-007**: Per-turn `Runner.run()` calls. App code manages the conversation loop, calling `Runner.run()` once per user message. The agent does not run in a continuous loop.

**DL-008**: Defensive score extraction. Scores are taken from the feedback agent's raw tool output in `result.raw_responses`, not from the orchestrator's text response. This prevents score hallucination by the orchestrator.

**DL-009**: mem0 reads at session start only, writes at session end only. No per-turn memory operations to prevent noisy, low-signal entries.

**DL-010**: `function_tools.py` and `learning_file.py` in ai_layer are ARCHIVED. Do not use or modify.
