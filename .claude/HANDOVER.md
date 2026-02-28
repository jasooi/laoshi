# Handover Document: Milestone 3 Documentation Updates

## What Was Completed

### 1. PRD.md - DONE
- Section 4.1 (AI-Coached Practice Sessions) rewritten to describe multi-agent architecture, multi-attempt scoring, "Next Word" progression, persistent memory, session summaries
- Section 6 (AI Strategy) fully rewritten with subsections: 6.1 Multi-Agent Architecture, 6.2 Design Principles, 6.3 Persistent Memory (mem0), 6.4 Model Selection

### 2. architecture.md - DONE
- Added AI Layer Stack section (OpenAI Agents SDK, DeepSeek, Gemini Flash, mem0, Redis)
- Updated Repository Structure with ai_layer/ folder, practice_resources.py, new components
- Updated Environment Variables with all new env vars (DEEPSEEK_BASE_URL, GEMINI_BASE_URL, etc.)
- Updated Database Models with new tables (SessionWordAttempt) and new fields
- Added AI Agent Architecture section with agent table and data flow description
- Added Practice API endpoints section (POST sessions, POST messages, POST next-word, GET summary)
- Added Confidence Score Formula section

### 3. PROJECT_PLAN.md - PARTIALLY DONE
- Tech Stack table updated (AI Layer, Memory rows added)
- Milestone 3 section fully rewritten with new architecture description, design principles, and 27 detailed tasks
- Task 3.2b added for SessionWordAttempt model

## What Still Needs To Be Done

### A. PROJECT_PLAN.md - 3 remaining edits

**Edit 1:** Update tasks 3.12-3.14 to reflect the "Next Word" flow instead of "skip" flow. Replace the current content:
```
| 3.12 | Backend: Implement `handle_message(session_id, user_id, message)` -- hydrate context from SessionWord, call Runner.run(), defensive score extraction from tool output, write scores to SessionWord, update Word.confidence_score, check session completion | [ ] |
| 3.13 | Backend: Implement `complete_session(session_id, user_id)` -- trigger orchestrator->summary handoff, extract summary JSON, write summary_text to UserSession, write mem0 updates, set session_end_ds | [ ] |
| 3.14 | Backend: Implement `skip_word(session_id, user_id)` -- mark SessionWord.is_skipped, advance to next word, check completion | [ ] |
```
With:
```
| 3.12 | Backend: Implement `handle_message(session_id, user_id, message)` -- hydrate context from SessionWord, call Runner.run(), defensive score extraction from tool output, write per-attempt scores to `SessionWordAttempt` | [ ] |
| 3.13 | Backend: Implement `advance_word(session_id, user_id)` ("Next Word" action) -- if attempts exist: average all attempt scores, write averages to SessionWord, set is_correct, update Word.confidence_score, set status=1. If no attempts: set is_skipped=True, status=-1. Advance to next word. Check session completion. | [ ] |
| 3.14 | Backend: Implement `complete_session(session_id, user_id)` -- trigger orchestrator->summary handoff, extract summary JSON, write summary_text to UserSession, write mem0 updates, set session_end_ds | [ ] |
```

**Edit 2:** Update task 3.15 API endpoints - rename `/skip` to `/next-word`:
Replace: `PracticeSkipResource` (POST `/practice/sessions/<id>/skip`)
With: `PracticeNextWordResource` (POST `/practice/sessions/<id>/next-word`)

**Edit 3:** Update task 3.20 frontend - change "skip" references to "Next Word":
Replace: `handleSkip`: call `practiceApi.skipWord()`
With: `handleNextWord`: call `practiceApi.nextWord()` -- if word was attempted, status=1; if not attempted, status=-1 (skip)

Also update the pre-existing frontend work note at the bottom:
- Change "Practice page skip button UI [x]" to "Practice page 'Next Word' button UI [x]"

### B. Implementation Plan File - Needs Updates

File: `C:\Users\Jasmine\.claude\plans\indexed-imagining-adleman.md`

This is the approved implementation plan that guides coding. It needs these updates:

1. **Phase 1 (DB Models):** Add `SessionWordAttempt` model description:
   - PK: `attempt_id` (Integer, auto-increment)
   - FKs: `word_id` + `session_id` (referencing SessionWord composite key)
   - Columns: `attempt_number` (Integer), `sentence` (Text), `grammar_score` (Float), `usage_score` (Float), `naturalness_score` (Float), `is_correct` (Boolean), `feedback_text` (Text), `created_ds` (DateTime)

2. **Phase 4 (Practice Runner):** Major rework:
   - `handle_message()` no longer writes to SessionWord or updates confidence. It writes to `SessionWordAttempt` only.
   - New function `advance_word()` replaces `skip_word()`:
     - If attempts exist for current word: compute average scores across all SessionWordAttempt rows, write averages to SessionWord, compute isCorrect from averages (avgGrammar==10 AND avgUsage>=8), update Word.confidence_score
     - If no attempts: set SessionWord.is_skipped=True
     - Advance to next word (next by word_order with status 0)
     - Check completion: session complete when all words have status != 0
   - `complete_session()` stays the same

3. **Phase 5 (API Endpoints):** Rename `/skip` to `/next-word`, rename `PracticeSkipResource` to `PracticeNextWordResource`

4. **Phase 6 (Frontend):** Rename skip button to "Next Word", update `handleSkip` to `handleNextWord`, update `practiceApi.skipWord()` to `practiceApi.nextWord()`

### C. Key Design Decisions (Context for the Next Agent)

These decisions were made during planning and should NOT be changed:

1. **No `word_dict` JSON column on UserSession.** Word ordering uses `SessionWord.word_order` (Integer). Status is derived from `is_correct`/`is_skipped` fields. Single source of truth.

2. **REDIS_URI stays in `.env` only** - contains credentials. Not added to config.py. Read via `os.getenv("REDIS_URI")` in ai_layer code.

3. **`isCorrect` threshold:** `avgGrammarScore == 10 AND avgUsageScore >= 8` (grammar must be perfect, usage allows minor imperfections)

4. **Word selection:** Random from words with `confidence_score < 0.9` (excludes mastered)

5. **Words per session:** Configurable via `DEFAULT_WORDS_PER_SESSION` in config.py (default 10). Stored per-session on `UserSession.words_per_session`. Accepted as optional param in POST `/practice/sessions`.

6. **Per-turn Runner.run() calls** -- app code manages the loop, not a continuous agent loop.

7. **Defensive score extraction** -- scores taken from feedback agent's raw tool output in `result.raw_responses`, not from orchestrator's text.

8. **Session completion** -- all words attempted (status 1) or skipped (status -1). Not gated by `isCorrect`.

9. **Multi-attempt per word** -- user can submit multiple sentences per word. Latest scores don't overwrite; instead, all attempts are stored in `SessionWordAttempt` and averaged when "Next Word" is clicked.

10. **`function_tools.py` and `learning_file.py`** in ai_layer are ARCHIVED. Do not use or modify.

### D. Reference Files

| File | Role |
|---|---|
| `.claude/plans/indexed-imagining-adleman.md` | Approved implementation plan (needs updates per section B above) |
| `.claude/PROJECT_PLAN.md` | Project roadmap with M3 task checklist (needs edits per section A above) |
| `.claude/PRD.md` | Product requirements (updated, done) |
| `.claude/architecture.md` | Technical architecture (updated, done) |
| `.claudedocs/user_evaluation.md` | Confidence score formula and evaluation criteria |
| `practice_session_agent_brief.pdf` | Engineering brief for the multi-agent architecture (attached to original conversation) |
| `backend/ai_layer/` | Existing skeleton code for agents, mem0, Redis |
| `backend/models.py` | Current DB models (need new columns + new table) |
| `backend/app.py` | Flask app factory (needs new resource registration) |
| `frontend/src/pages/Practice.tsx` | Existing practice UI (needs data flow rewrite) |
