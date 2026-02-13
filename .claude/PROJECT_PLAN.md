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
| AI Coach | DeepSeek API (primary), Gemini 2.5 Flash (backup) |
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
**Status:** Partially Done
**Spec folder:** `.claudedocs/m1-auth-onboarding/`
**PRD stories:** #1 (Register & login), #2 (Guided onboarding)

| # | Task | Status |
|---|---|---|
| 1.1 | Backend: POST `/users` registration endpoint | [x] |
| 1.2 | Backend: POST `/token` login endpoint (returns JWT) | [x] |
| 1.3 | Backend: GET `/me` current-user endpoint | [x] |
| 1.4 | Frontend: Create Login page (`/login`) with username + password form | [ ] |
| 1.5 | Frontend: Create Register page (`/register`) with username, email, password form | [ ] |
| 1.6 | Frontend: Implement protected route wrapper -- redirect unauthenticated users to `/login` | [ ] |
| 1.7 | Frontend: Update Welcome page to route new users through registration, then onboarding | [ ] |
| 1.8 | Frontend: Onboarding flow -- after first login, guide user to import vocabulary (Welcome.tsx partially does this) | [x] |
| 1.9 | Frontend: Add logout button to Sidebar/Header, clear token on logout | [ ] |

---

### Milestone 2: Vocabulary Management
**Status:** In Progress
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
| 2.10 | Frontend: Edit word modal (handleEdit is a stub with TODO comment) | [ ] |
| 2.11 | Frontend: Delete word via DELETE `/api/words/<id>` | [x] |
| 2.12 | Frontend: Wire vocabulary fetch to backend with correct auth headers (via centralized Axios instance from M0) | [x] |

---

### Milestone 3: AI Practice Sessions
**Status:** Not Started (frontend UI shell exists with mock data fallback)
**Spec folder:** `.claudedocs/m3-practice-sessions/`
**PRD stories:** #8 (Select collection & start session), #9 (AI flashcard + sentence prompt), #10 (AI evaluates naturalness), #11 (Detailed feedback), #12 (Skip words), #13 (Toggle pinyin/definition), #17 (Confidence scores per word)

| # | Task | Status |
|---|---|---|
| 3.1 | Backend: AI model integration -- service module to call DeepSeek chat completions (with Gemini 2.5 Flash fallback) with system prompt for Mandarin sentence evaluation | [ ] |
| 3.2 | Backend: GET `/practice/next-word` -- select next word for session using confidence-based algorithm (lower confidence = higher priority) | [ ] |
| 3.3 | Backend: POST `/practice/evaluate` -- accept `{word_id, sentence}`, call DeepSeek (or Gemini fallback), return structured feedback (grammar, naturalness, usage scores, corrections, examples) | [ ] |
| 3.4 | Backend: Update word confidence score after evaluation using score update algorithm | [ ] |
| 3.5 | Backend: Create/update UserSession and SessionWord records to track practice session state | [~] |
| 3.6 | Backend: Session completion -- generate teacher-style summary (2 strengths, 1 area for improvement) via DeepSeek (or Gemini fallback) | [ ] |
| 3.7 | Frontend: Practice page -- word card with toggle pinyin/definition | [x] |
| 3.8 | Frontend: Practice page -- chat interface for sentence input and AI feedback display | [x] |
| 3.9 | Frontend: Practice page -- skip word functionality | [x] |
| 3.10 | Frontend: Practice page -- progress bar (X/N words practiced) | [x] |
| 3.11 | Frontend: Practice page -- practiced/skipped words trays | [x] |
| 3.12 | Frontend: Replace mock data fallback with real API calls to `/practice/next-word` and `/practice/evaluate` | [ ] |
| 3.13 | Frontend: Display structured AI feedback (grammar score, naturalness score, corrections, example sentences) | [ ] |
| 3.14 | Frontend: Session completion screen with summary from 3.6 | [ ] |

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
