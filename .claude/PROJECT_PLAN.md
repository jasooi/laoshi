# Laoshi -- Project Plan

> Execution roadmap for the Laoshi Mandarin learning app.
> For business requirements, see [PRD.md](PRD.md). For technical architecture, see [architecture.md](architecture.md).
> Detailed implementation specs live in `.claudedocs/<milestone-name>/` folders. 

---

## Documentation Workflow

```
PRD.md (what to build & why)
  --> PROJECT_PLAN.md (when to build it -- this file)
    --> .claudedocs/<milestone-name>/  (how to build it)
          ├── requirements.md   Acceptance criteria extracted from PRD
          ├── design.md         Technical architecture & approach (architecture.md is source of truth)
          └── tasks.md          Granular implementation subtasks
```

**How the implementing agent should use this file:**
1. Pick the next incomplete milestone in order.
2. If the `.claudedocs/<milestone-name>/` folder does not exist, create it and populate requirements.md, design.md, and tasks.md before coding.
3. Work through the task checklist below, checking off items as they are completed.
4. Update the milestone status when all its tasks are done.

**Task status legend:** `[x]` done | `[~]` partially done | `[ ]` not started

---

## Tech Stack Reference

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite, Tailwind CSS, React Router, Axios |
| Backend | Flask + Flask-RESTful, SQLAlchemy ORM, Flask-JWT-Extended |
| Database | PostgreSQL (via SQLAlchemy + Flask-Migrate/Alembic) |
| AI Layer | OpenAI Agents SDK (multi-agent orchestration), DeepSeek (feedback evaluation), Gemini Flash (orchestrator + summary) |
| Memory | mem0 (cross-session persistent user preferences), Redis (session-scoped conversation history) |
| Auth | JWT (access tokens via `/token` endpoint) |

---

## Phase Overview

| Phase | Scope | Status |
|---|---|---|
| **Phase 1 (MVP)** | Auth, vocabulary CRUD + CSV import, AI practice sessions, home stats, settings | **In Progress** |
| Phase 2 | Custom collections, pre-defined vocab sets, saved sentences, detailed progress dashboard | Not Started |
| Phase 3 | Spaced repetition (SuperMemo), community-contributed vocab sets | Not Started |
| Phase 4 | Contextual hints (images/notes on words), voice chat | Not Started |

---

## Phase 1 -- MVP

### Milestone 0: Foundation Fixes
**Status:** Done
**Spec folder:** `.claudedocs/m0-foundation-fixes/`

Resolve structural issues blocking all other milestones: API path mismatches between frontend and backend, missing auth headers on frontend requests, and absence of test infrastructure.

| # | Task | Status |
|---|---|---|
| 0.1 | Resolve API path mismatch: frontend calls `/api/vocabulary/*`, `/api/practice/*`, `/api/progress/*` but backend serves `/words/*`, `/sessions/*`, etc. Decide approach (add `/api` prefix to Flask routes, or adjust Vite proxy/frontend paths) and implement consistently. | [x] |
| 0.2 | Add JWT Authorization header to all frontend API calls (currently no auth header is sent) | [x] |
| 0.3 | Create React auth context/provider to store JWT token and user state, provide login/logout functions | [x] |
| 0.4 | Set up frontend test infrastructure (Vitest + React Testing Library) with at least one smoke test | [x] |
| 0.5 | Set up backend test infrastructure (pytest + Flask test client) with at least one smoke test | [x] |
| 0.6 | Align frontend TypeScript interfaces with backend response shapes (e.g. backend returns `meaning`, frontend expects `definition`; backend returns computed `status`, frontend expects `confidenceLevel`) | [x] |

---

### Milestone 1: Authentication & Onboarding
**Status:** Done
**Spec folder:** `.claudedocs/m1-auth-onboarding/`
**PRD stories:** #1 (Register & login), #2 (Guided onboarding)

| # | Task | Status |
|---|---|---|
| 1.1 | Backend: POST `/users` registration endpoint | [x] |
| 1.2 | Backend: POST `/token` login endpoint (returns JWT) | [x] |
| 1.3 | Backend: GET `/me` current-user endpoint | [x] |
| 1.4 | Frontend: Create Login page (`/login`) with username + password form | [x] |
| 1.5 | Frontend: Create Register page (`/register`) with username, email, password form | [x] |
| 1.6 | Frontend: Implement protected route wrapper -- redirect unauthenticated users to `/login` | [x] |
| 1.7 | Frontend: Update Welcome page to route new users through registration, then onboarding | [x] |
| 1.8 | Frontend: Onboarding flow -- after first login, guide user to import vocabulary (Welcome.tsx partially does this) | [x] |
| 1.9 | Frontend: Add logout button to Sidebar/Header, clear token on logout | [x] |

---

### Milestone 2: Vocabulary Management
**Status:** Done
**Completed:** 2026-02-15
**Spec folder:** `.claudedocs/m2-vocabulary/`
**PRD stories:** #3 (CSV import), #6 (Search/filter/sort), #7 (Edit/delete words)

| # | Task | Status |
|---|---|---|
| 2.1 | Backend: GET `/words` -- list all words for authenticated user | [x] |
| 2.2 | Backend: POST `/words` -- bulk create words (JSON array) | [x] |
| 2.3 | Backend: GET `/words/<id>` -- get single word | [x] |
| 2.4 | Backend: PUT `/words/<id>` -- update word fields | [x] |
| 2.5 | Backend: DELETE `/words/<id>` -- delete single word | [x] |
| 2.6 | Backend: DELETE `/words` -- delete all words for user | [x] |
| 2.7 | Backend: POST CSV import endpoint -- accept multipart file upload, parse CSV, create words in bulk | N/A (CSV parsing moved client-side in M0; frontend sends JSON to POST `/api/words`) |
| 2.8 | Frontend: Vocabulary table with search and sort | [x] |
| 2.9 | Frontend: CSV upload modal with client-side PapaParse parsing, sends JSON to POST `/api/words` | [x] |
| 2.10 | Frontend: Edit word modal | [x] |
| 2.11 | Frontend: Delete word via DELETE `/api/words/<id>` | [x] |
| 2.12 | Frontend: Wire vocabulary fetch to backend with correct auth headers (via centralized Axios instance from M0) | [x] |
| 2.13 | Backend: Add `paginate_query` utility to `utils.py` and `Word.get_query_for_user` classmethod to `models.py` | [x] |
| 2.14 | Backend: Add pagination, server-side search, and sort to `GET /api/words` (response changes from bare array to `{data, pagination}`) | [x] |
| 2.15 | Backend: Add input validation to `POST /api/words` (check array type, required keys) | [x] |
| 2.16 | Backend: Extract status thresholds to class constant in `models.py` | [x] |
| 2.17 | Frontend: Create reusable `Pagination` component (`components/Pagination.tsx`) | [x] |
| 2.18 | Frontend: Extract `UploadModal` and `EditWordModal` from monolithic `Vocabulary.tsx` into `pages/vocabulary/` | [x] |
| 2.19 | Frontend: Restructure Vocabulary page -- fixed layout with scrollable table body, sticky thead, server-side paginated search/sort, 10/20/50 per-page selector, debounced search | [x] |
| 2.20 | Frontend: Update `Home.tsx` to consume new paginated response format for word count | [x] |
| 2.21 | Backend tests: pagination utility unit tests (17) + `GET /api/words` integration tests (22) -- 57 total backend tests pass | [x] |
| 2.22 | Frontend tests: `Pagination` component tests (23) + all M2-related tests pass (2 pre-existing M1 Register.test.tsx failures remain) | [x] |

---

### Milestone 3: AI Practice Sessions
**Status:** In Progress (frontend UI shell exists with mock data; `ai_layer/` has skeleton agents)
**Spec folder:** `.claudedocs/m3-practice-sessions/`
**PRD stories:** #8 (Select collection & start session), #9 (AI flashcard + sentence prompt), #10 (AI evaluates naturalness), #11 (Detailed feedback), #12 (Skip words), #13 (Toggle pinyin/definition), #17 (Confidence scores per word)

**Architecture:** Multi-agent system using OpenAI Agents SDK. Three agents: Orchestrator (Gemini Flash, sassy teacher persona, intent classification), Feedback Agent (DeepSeek, sentence evaluation, agent-as-tool), Summary Agent (Gemini Flash, end-of-session summary, handoff agent). App code manages all state, DB writes, and mem0 updates. Agents receive read-only context. See engineering brief for details.

**Design principles:**
- Agents reason; app code manages data (no DB/mem0 tools on agents)
- Per-turn `Runner.run()` calls; app code tracks session state deterministically
- Defensive score extraction: scores taken from feedback agent's raw tool output, not orchestrator text
- Confidence score formula: `newScore = clamp(currentScore + correctnessFactor * qualityMultiplier * learningRate, 0, 1)`
- `isCorrect` threshold: `grammarScore == 10 AND usageScore >= 8`
- Words per session: configurable (default 10), stored per-session on `UserSession.words_per_session`
- Word selection: random from words with `confidence_score < 0.9` (excludes mastered)

| # | Task | Status |
|---|---|---|
| | **Database & Config** | |
| 3.1 | Backend: Add `summary_text`, `words_per_session` columns to `UserSession` model | [ ] |
| 3.2 | Backend: Add `word_order`, `grammar_score`, `usage_score`, `naturalness_score`, `is_correct` columns to `SessionWord` model. Update `format_data()` for both models. Scores on SessionWord are averages computed from attempts when user clicks "Next Word". | [ ] |
| 3.2b | Backend: Create new `SessionWordAttempt` model -- PK: `attempt_id` (auto-increment), FKs: `word_id` + `session_id` (linking to SessionWord composite key). Columns: attempt_number, sentence, grammar_score, usage_score, naturalness_score, is_correct, feedback_text, created_ds. Multiple rows per word per session. | [ ] |
| 3.3 | Backend: Run Alembic migration for new models and columns | [ ] |
| 3.4 | Backend: Add `DEFAULT_WORDS_PER_SESSION` to `config.py` (REDIS_URI stays in `.env` only -- contains credentials) | [ ] |
| | **AI Layer -- Context & Agents** | |
| 3.5 | Backend: Expand `ai_layer/context.py` -- add `WordContext` dataclass and full `UserSessionContext` (current_word, session_word_dict, words_completed, words_total, session_complete, mem0_preferences, word_roster) | [ ] |
| 3.6 | Backend: Rework Feedback Agent (`ai_layer/chat_agents.py`) -- dynamic prompt injecting current word from context, structured JSON output schema (grammarScore, usageScore, naturalnessScore, isCorrect, feedback, corrections, explanations, exampleSentences), DeepSeek model | [ ] |
| 3.7 | Backend: Rework Orchestrator Agent (`ai_layer/chat_agents.py`) -- sassy Mandarin teacher persona, intent classification (sentence vs chat), feedback agent wired as tool, handoff to summary agent when session_complete, dynamic prompt injecting student name/progress/mem0 | [ ] |
| 3.8 | Backend: Rework Summary Agent (`ai_layer/chat_agents.py`) -- dynamic prompt, returns `{summary_text, mem0_updates}` JSON, wired as handoff target from orchestrator | [ ] |
| 3.9 | Backend: Clean up `chat_agents.py` module-level code (remove hardcoded dotenv path, clean env loading) | [ ] |
| | **AI Layer -- Practice Runner** | |
| 3.10 | Backend: Create `ai_layer/practice_runner.py` -- `run_async()` wrapper for sync Flask, validation helpers (`validate_feedback`, `validate_summary`), retry with exponential backoff | [ ] |
| 3.11 | Backend: Implement `initialize_session(user_id, words_count)` -- random word selection (confidence < 0.9), create UserSession + SessionWord rows, fetch mem0 preferences, init Redis session, generate greeting via Runner.run() | [ ] |
| 3.12 | Backend: Implement `handle_message(session_id, user_id, message)` -- hydrate context from SessionWord, call Runner.run(), defensive score extraction from tool output, write per-attempt scores to `SessionWordAttempt` | [ ] |
| 3.13 | Backend: Implement `advance_word(session_id, user_id)` ("Next Word" action) -- if attempts exist: average all attempt scores, write averages to SessionWord, set is_correct, update Word.confidence_score, set status=1. If no attempts: set is_skipped=True, status=-1. Advance to next word. Check session completion. | [ ] |
| 3.14 | Backend: Implement `complete_session(session_id, user_id)` -- trigger orchestrator->summary handoff, extract summary JSON, write summary_text to UserSession, write mem0 updates, set session_end_ds | [ ] |
| | **API Endpoints** | |
| 3.15 | Backend: Create `practice_resources.py` with `PracticeSessionResource` (POST `/practice/sessions`), `PracticeMessageResource` (POST `/practice/sessions/<id>/messages`), `PracticeNextWordResource` (POST `/practice/sessions/<id>/next-word`), `PracticeSummaryResource` (GET `/practice/sessions/<id>/summary`) | [ ] |
| 3.16 | Backend: Register practice resources in `app.py` | [ ] |
| 3.17 | Backend: Manual smoke test of full session flow | [ ] |
| | **Frontend** | |
| 3.18 | Frontend: Add practice TypeScript types to `types/api.ts` (`WordContext`, `PracticeSessionResponse`, `FeedbackData`, `PracticeMessageResponse`, `PracticeSummaryResponse`) | [ ] |
| 3.19 | Frontend: Add `practiceApi` helper functions to `lib/api.ts` (startSession, sendMessage, nextWord, getSummary) | [ ] |
| 3.20 | Frontend: Rewrite `Practice.tsx` data flow -- remove mock data, session lifecycle (init/practicing/completed), wire to real APIs, get words_total from API (not hardcoded) | [ ] |
| 3.21 | Frontend: Add typing indicator and loading states during agent calls | [ ] |
| 3.22 | Frontend: Create `FeedbackCard.tsx` component -- score badges, corrections, example sentences inside chat bubbles | [ ] |
| 3.23 | Frontend: Create `SessionSummary.tsx` component -- summary prose, word results table, navigation buttons | [ ] |
| | **Testing** | |
| 3.24 | Backend: Unit tests for `practice_runner.py` with mocked agent calls | [ ] |
| 3.25 | Backend: Integration tests for practice API endpoints | [ ] |
| 3.26 | Frontend: Component tests for FeedbackCard and SessionSummary | [ ] |
| 3.27 | End-to-end manual test: full session flow (start, practice, skip, complete, summary, verify DB scores and mem0 writes) | [ ] |

**Pre-existing frontend work (from earlier development, carried forward):**
- Practice page word card with toggle pinyin/definition [x]
- Practice page chat interface layout [x]
- Practice page 'Next Word' button UI [x]
- Practice page progress bar UI [x]
- Practice page practiced/skipped words trays UI [x]

---

### Milestone 4: Home Page Stats & Settings
**Status:** Partially Done
**Spec folder:** `.claudedocs/m4-stats-settings/`
**PRD stories:** #15 (Home page stats), #18 (Configure words per session), #19 (BYOK API key)

| # | Task | Status |
|---|---|---|
| 4.1 | Backend: GET `/progress/stats` -- return words practiced today, overall mastery percentage, words ready for review | [ ] |
| 4.2 | Frontend: Home page stats cards wired to real data from 4.1 (UI exists, currently shows hardcoded zeros) | [~] |
| 4.3 | Frontend: Home page -- conditionally disable "Start Practice" when no words exist | [x] |
| 4.4 | Backend: User settings model/endpoint -- store `words_per_session` and `api_key` per user | [ ] |
| 4.5 | Frontend: Settings page -- words per session configuration | [ ] |
| 4.6 | Frontend: Settings page -- BYOK API key input with save/clear | [ ] |
| 4.7 | Backend: Use user's custom API key (if set) when calling DeepSeek/Gemini, fall back to default free-tier keys | [ ] |

---

## Phase 2 -- Enhanced Features (future, not yet broken into tasks)

### Milestone 5: Collections & Pre-defined Vocab Sets
**PRD stories:** #4 (Browse/import pre-defined sets), #5 (Custom collections), #8 (Select collection to start session)

### Milestone 6: Saved Sentences & Detailed Progress
**PRD stories:** #14 (Save correct sentences to word), #16 (Detailed progress dashboard)

---

## Phase 3 -- Smart Learning (future)

### Milestone 7: Spaced Repetition & Community Sets
**PRD stories:** SuperMemo algorithm for flashcard scheduling, community-contributed vocabulary sets

---

## Phase 4 -- Rich Media & Voice (future)

### Milestone 8: Contextual Hints & Voice Chat
**PRD stories:** #20 (Photos/notes on words), voice chat for spoken sentence practice

---

## PRD Story-to-Milestone Map

| Story | Description | Milestone | Phase |
|---|---|---|---|
| #1 | Register & login | M1 | 1 |
| #2 | Guided onboarding | M1 | 1 |
| #3 | Upload CSV vocabulary | M2 | 1 |
| #4 | Browse/import pre-defined sets | M5 | 2 |
| #5 | Create custom collections | M5 | 2 |
| #6 | Search, filter, sort vocabulary | M2 | 1 |
| #7 | Edit/delete words | M2 | 1 |
| #8 | Select collection & start practice | M3 (basic) / M5 (full) | 1 / 2 |
| #9 | AI flashcard + sentence prompt | M3 | 1 |
| #10 | AI evaluates naturalness | M3 | 1 |
| #11 | Detailed feedback | M3 | 1 |
| #12 | Skip words | M3 | 1 |
| #13 | Toggle pinyin/definition | M3 | 1 |
| #14 | Save correct sentences | M6 | 2 |
| #15 | Home page stats | M4 | 1 |
| #16 | Detailed progress dashboard | M6 | 2 |
| #17 | Confidence scores per word | M3 | 1 |
| #18 | Configure words per session | M4 | 1 |
| #19 | BYOK API key | M4 | 1 |
| #20 | Photos/notes on words | M8 | 4 |

---

## Known Issues

| Issue | Impact | Resolved In | Status |
|---|---|---|---|
| Frontend calls `/api/vocabulary/*`, backend serves `/words/*` | All vocabulary features broken end-to-end | M0 task 0.1 | Resolved |
| Frontend calls `/api/practice/*`, `/api/progress/*` -- endpoints don't exist | Practice and stats pages use mock/hardcoded data | M0 task 0.1 (paths aligned), M3, M4 (endpoints to be built) | Partially resolved |
| No JWT Authorization header sent from frontend | All authenticated endpoints return 401 | M0 task 0.2 | Resolved |
| Frontend `definition` field vs backend `meaning` field | Word data not displayed after fetch | M0 task 0.6 | Resolved |
| Old PROJECT_PLAN.md referenced MongoDB, Gemini as primary model, localStorage auth | Outdated -- old file deleted | This document replaces it | Resolved |
