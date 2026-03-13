# M5 Decks -- Tasks

> Granular implementation checklist for Milestone 5: Decks (Collections Redesign)
> Task status legend: `[x]` done | `[~]` partially done | `[ ]` not started

---

## Phase A: Database Schema

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Backend: Create `Deck` model (id, name, description, user_id FK, laoshi_message, created_ds, updated_ds) with relationships to User, Word, UserSession | [ ] | In `backend/models.py` |
| 5.2 | Backend: Add `deck_id` FK (nullable) + SRS fields (`repetitions`, `interval_days`, `ease_factor`, `next_review_date`) + mastery fields (`last_quality`, `marked_as_known`, `is_mastered`) to `Word` model, **remove** `confidence_score` | [ ] | Nullable deck_id only during migration |
| 5.3 | Backend: Add `deck_id` FK (nullable) to `UserSession` model + `deck` relationship | [ ] | Null for legacy sessions |
| 5.4 | Backend: Add `current_streak` (Integer, default=0) and `last_practice_date` (Date, nullable) to `UserProfile` | [ ] | For day streak tracking |
| 5.5 | Backend: Add `Word.update_mastery_status()` method (quality 5 → mastered, quality ≤3 → not mastered, quality 4 preserves state) | [ ] | |
| 5.5a | Backend: Update `Word.format_data()` and `UserSession.format_data()` to include `deck_id` and SRS/mastery fields | [ ] | |
| 5.6 | Backend: Create Alembic migration for Deck table + SRS/mastery fields on Word + FK columns + **drop** `confidence_score` + data migration (create "My Words" deck per user, assign existing words, SRS fields auto-initialized via server defaults) | [ ] | In `backend/migrations/versions/` |
| 5.7 | Backend: Run migration and verify existing data migrated correctly | [ ] | Test with dev database |

---

## Phase B: Backend Deck API

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.8 | Backend: Create `deck_resources.py` — `GET /api/decks` with computed stats (word_count, mastered_count where `is_mastered=true`, mastery_percentage, last_practiced_at) using SQLAlchemy subqueries to avoid N+1 | [ ] | Use `scalar_subquery()` |
| 5.9 | Backend: `POST /api/decks` — create empty deck (name, description) | [ ] | |
| 5.10 | Backend: `GET /api/decks/:id` — deck detail + stats | [ ] | |
| 5.11 | Backend: `PUT /api/decks/:id` — update name/description | [ ] | |
| 5.12 | Backend: `DELETE /api/decks/:id` — delete deck + cascade delete words | [ ] | SQLAlchemy cascade='all, delete-orphan' |
| 5.13 | Backend: `GET /api/decks/:id/words` — paginated word list for deck (reuse `paginate_query`) | [ ] | |
| 5.14 | Backend: `POST /api/decks/:id/words` — create words inside deck (replaces old `POST /api/words`) | [ ] | Bulk create endpoint |
| 5.15 | Backend: `POST /api/decks/combine` — create new deck + copy words from source decks | [ ] | Loop through source_deck_ids, copy words |
| 5.16 | Backend: `GET /api/progress/streak` — return current_streak and last_practice_date | [ ] | In `report_card_resources.py` or new `streak_resources.py` |
| 5.17 | Backend: Register all deck resources in `app.py` | [ ] | `api.add_resource(...)` |
| 5.18 | Backend: **Remove** `POST /api/words` and `DELETE /api/words` endpoints from `resources.py` | [ ] | Remove `WordListResource.post()` and `.delete()` methods |
| 5.19 | Backend: Update `GET /api/words` to accept optional `deck_id` query param for filtering | [ ] | Filter by deck_id if provided |

---

## Phase C: Backend Practice & AI Changes

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.20 | Backend: Update `POST /api/practice/sessions` to require `deck_id` in request body | [ ] | In `practice_resources.py` |
| 5.21 | Backend: Modify `initialize_session()` to use SRS word selection (40% new words where `next_review_date IS NULL`, 60% review words where `next_review_date <= today`, sorted by date ASC, buffer pools if insufficient, fallback to future words) | [ ] | In `practice_runner.py` |
| 5.22 | Backend: Set `session.deck_id = deck_id` in `initialize_session()` | [ ] | |
| 5.23 | Backend: Create `POST /api/practice/sessions/:id/end` endpoint — marks remaining SessionWords as skipped, calls `complete_session()` | [ ] | New resource in `practice_resources.py` |
| 5.24 | Backend: Update `build_summary_prompt()` in `chat_agents.py` to add `deck_oneliner` to JSON output spec (max 80 chars, progress + next focus) | [ ] | |
| 5.25 | Backend: Modify `complete_session()` in `practice_runner.py` to extract `deck_oneliner` from summary JSON and update `Deck.laoshi_message` | [ ] | |
| 5.26 | Backend: Implement streak update logic in `complete_session()` — check last_practice_date, increment or reset current_streak, update last_practice_date to today | [ ] | Create `update_streak()` helper with SELECT FOR UPDATE locking |
| 5.26a | Backend: Implement `update_srs(word, quality)` function — SM-2 algorithm with modified intervals (1d → 3d → 7d → ~18d), quality <3 resets, ease_factor updates, fast-track quality 5 on rep 0 | [ ] | In `practice_runner.py` |
| 5.26b | Backend: Implement `mark_word_as_mastered(word)` and `unmark_word_as_mastered(word)` functions — sets repetitions=5, interval=90, is_mastered=true, last_quality=5 | [ ] | In `practice_runner.py` |
| 5.26c | Backend: Modify `advance_word()` to accept `quality` parameter, call `update_srs()`, call `word.update_mastery_status()`, handle skip (defer by 1 day) | [ ] | In `practice_runner.py` |
| 5.26d | Backend: Update `POST /api/practice/sessions/:id/next-word` signature to accept `{quality: int}` in request body | [ ] | In `practice_resources.py` |
| 5.26e | Backend: Create `POST /api/words/:id/mark-as-mastered` endpoint — toggles mastered status, returns word data | [ ] | In `resources.py` (word resources) |

---

## Phase D: Frontend Types & API Client

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.27 | Frontend: Add `DeckListItem`, `DeckDetail`, `DeckWithStats` interfaces to `types/api.ts`, update `Word` interface with SRS fields (repetitions, interval_days, ease_factor, next_review_date, last_quality, marked_as_known, is_mastered), **remove** `confidence_score` | [ ] | |
| 5.28 | Frontend: Create `deckApi` helper group in `lib/api.ts` (getDecks, createDeck, updateDeck, deleteDeck, getDeckWords, addWordsToDeck, combineDecks) | [ ] | |
| 5.29 | Frontend: Add `getStreak()` to `progressApi` in `lib/api.ts` | [ ] | |
| 5.30 | Frontend: Update `practiceApi.startSession()` to accept `deckId` parameter | [ ] | Send `{deck_id, words_count?}` in body |
| 5.31 | Frontend: Update `practiceApi.advanceWord()` to accept `quality` parameter | [ ] | Send `{quality}` in body to POST /next-word |
| 5.32 | Frontend: Add `practiceApi.endSession(sessionId)` for new POST /end endpoint | [ ] | |
| 5.33 | Frontend: Add `wordsApi.markAsMastered(wordId)` for new POST /words/:id/mark-as-mastered endpoint | [ ] | |
| 5.34 | Frontend: **Remove** old bulk word creation API calls from codebase | [ ] | Search for usages of old `POST /api/words` |

---

## Phase E: Frontend Home Page Rewrite

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.35 | Frontend: Create `pages/home/HomeContext.tsx` — React context with selectedDeckId, activePracticeSessionId, selectDeck(), startPractice(), endPractice() | [ ] | |
| 5.36 | Frontend: Create `pages/home/DeckListPanel.tsx` — left panel with GET /api/decks, streak badge, DeckListItem components, "+ New Deck" button | [ ] | |
| 5.37 | Frontend: Create `pages/home/DeckListItem.tsx` — growth icon (🌱 seedling 0-24%, 🌿 leaves 25-74%, 🌸 flower 75-100% based on mastery %), recency color (green/yellow/red/grey), progress bar, word count, laoshi message preview | [ ] | |
| 5.38 | Frontend: Create `pages/home/DeckDetailPanel.tsx` — right panel with circular progress ring (SVG), stats, full laoshi message, "Start Practice" and "Manage in Library →" buttons | [ ] | |
| 5.39 | Frontend: Create `pages/home/EmptyDeckPlaceholder.tsx` — default right panel with Laoshi avatar, "Select a deck to begin", streak counter | [ ] | |
| 5.40 | Frontend: Create `pages/home/EndSessionModal.tsx` — confirmation modal for mid-session deck switch | [ ] | "End Session & Switch" / "Cancel" |
| 5.41 | Frontend: Rewrite `pages/Home.tsx` — split-panel layout with DeckListPanel (left) + Outlet (right), wrap in HomeProvider | [ ] | |
| 5.42 | Frontend: Update `App.tsx` routing — nested routes under /home (`/home`, `/home/deck/:deckId`, `/home/deck/:deckId/practice`), remove standalone `/practice` route | [ ] | |

---

## Phase F: Frontend Inline Practice Panel

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.43 | Frontend: Create `pages/home/PracticePanel.tsx` — refactor Practice.tsx logic inline, chat area center, collapsible word panel right side, close button top right | [ ] | |
| 5.44 | Frontend: Create quality rating menu component — 6 buttons (0-5) with emoji + labels, appears after user clicks "Next Word", blocks progression until selection, calls `advanceWord(quality)` | [ ] | See design.md Section 7.1 |
| 5.45 | Frontend: Add "Mark as Mastered" button to word card — always visible, toggles between "Mark as Mastered" and "Unmark as Mastered", calls `wordsApi.markAsMastered()`, removes word from session, shows next word | [ ] | See design.md Section 7.2 |
| 5.46 | Frontend: Extract practice session state logic into custom `usePracticeSession` hook for reusability | [ ] | Optional but recommended |
| 5.47 | Frontend: Remove practiced/skipped word lists from session UI (keep only current word panel) | [ ] | |
| 5.48 | Frontend: Wire close button to `POST /api/practice/sessions/:id/end`, show SessionSummary inline | [ ] | |
| 5.49 | Frontend: Update `SessionSummary.tsx` to support inline rendering mode (not full-screen overlay) | [ ] | Add `inline?: boolean` prop |
| 5.50 | Frontend: Update SessionSummary "Back to Home" to navigate to `/home/deck/:deckId` instead of `/home` | [ ] | |
| 5.51 | Frontend: **Delete** `pages/Practice.tsx` (logic fully moved to PracticePanel) | [ ] | |

---

## Phase G: Frontend Library Page

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.52 | Frontend: Create `pages/Library.tsx` — grid layout (3-4 cols), deck cards with growth icon + recency colors + progress bar + kebab menu (⋮), "+ Create New Deck" dropdown (Manual Creation, Upload CSV, Combine Decks, Shared Decks), empty state ("No decks yet..."), NO laoshi_message | [ ] | Grid uses recency colors (🟢🟡🔴⚫) for icon + progress bar together |
| 5.53 | Frontend: Create `pages/library/CreateDeckModal.tsx` — triggered by dropdown menu items (Manual Creation, Upload CSV, Combine Decks), name + description fields | [ ] | Dropdown items have NO descriptions underneath |
| 5.54 | Frontend: Create `pages/library/DeckWordsView.tsx` — "← Back to Library" breadcrumb, simplified stats ("102 / 156 mastered (65%)" + growth icon + stage name), words table (reuse Vocabulary.tsx pattern) with Status column (New/In Review/Mastered), search/sort/paginate, edit/delete words, "+ Add Word" + "Export" buttons, info banner for combined decks | [ ] | Stats: single ratio line, no "Due Today" (avoid pressure) |
| 5.55 | Frontend: Create `pages/library/CombineDecksModal.tsx` — multi-select decks, name + description for new deck, info note about word copying | [ ] | |
| 5.56 | Frontend: Move `pages/vocabulary/UploadModal.tsx` to `pages/library/UploadModal.tsx`, update to accept `deckId` prop, call new 2-step CSV flow (create deck → upload words) | [ ] | |
| 5.57 | Frontend: Move `pages/vocabulary/EditWordModal.tsx` to `pages/library/EditWordModal.tsx` | [ ] | |
| 5.58 | Frontend: Update `App.tsx` routing — add `/library` and `/library/deck/:deckId`, **remove** `/vocabulary` route | [ ] | |
| 5.59 | Frontend: **Delete** `pages/Vocabulary.tsx` (replaced by Library.tsx) | [ ] | |

---

## Phase H: Frontend Sidebar & Color Scheme

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.60 | Frontend: Update `components/Sidebar.tsx` — rename "Vocabulary" to "Library", change path to `/library`, update icon if needed | [ ] | Use BookOpen icon from Lucide |
| 5.61 | Frontend: Define warm color scheme in `tailwind.config.ts` — primary (sage/olive green), accent (muted amber/terracotta), backgrounds (warm grays stone-50/100) | [ ] | |
| 5.62 | Frontend: Apply new color scheme across all components (replace purple #9333EA) | [ ] | Search for `purple-600`, `purple-500`, etc. |

---

## Phase I: Testing

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.63 | Backend: Create `tests/test_deck_api.py` — unit + integration tests for all deck endpoints | [ ] | Test auth, stats computation with `is_mastered`, sorting, cascade delete |
| 5.64 | Backend: Unit tests for `update_srs()` — quality 0-5, interval progression (1→3→7→18), ease_factor updates, fast-track quality 5 on rep 0, harsh reset on quality <3 | [ ] | In `tests/test_practice_runner.py` |
| 5.65 | Backend: Unit tests for `Word.update_mastery_status()` — quality 5 → mastered, quality ≤3 → not mastered, quality 4 preserves state | [ ] | In `tests/test_models.py` |
| 5.66 | Backend: Unit tests for `mark_word_as_mastered()` and `unmark_word_as_mastered()` — sets 90-day interval, is_mastered=true, last_quality=5, toggle behavior | [ ] | In `tests/test_practice_runner.py` |
| 5.67 | Backend: Unit tests for SRS word selection — 40/60 ratio, buffer pools, fallback to future words | [ ] | In `tests/test_practice_runner.py` |
| 5.68 | Backend: Unit tests for streak logic in `practice_runner.py` | [ ] | Test today, yesterday, older, null cases |
| 5.69 | Backend: Integration tests for `POST /api/practice/sessions/:id/next-word` with quality param — SRS state updates, mastery updates | [ ] | In `tests/test_practice_api.py` |
| 5.70 | Backend: Integration test for `POST /api/words/:id/mark-as-mastered` — verifies fast-track and toggle logic | [ ] | In `tests/test_words_api.py` |
| 5.71 | Backend: Update existing tests broken by API changes (removal of POST /api/words, removal of confidence_score, addition of deck_id to sessions, SRS fields) | [ ] | Fix failing tests in `tests/test_practice_api.py`, `tests/test_words_api.py` |
| 5.72 | Frontend: Component tests for new Home components (DeckListPanel, DeckDetailPanel, PracticePanel, quality rating menu) | [ ] | Use React Testing Library |
| 5.73 | Frontend: Component tests for Library page components (CreateDeckModal, CombineDecksModal, DeckWordsView) | [ ] | |
| 5.74 | End-to-end manual test: Fresh user → create deck via CSV → deck appears (🌱) → practice → quality rating menu → rate words → SRS intervals update → session end → streak incremented → mastery % updates → growth icon changes (🌱→🌿) | [ ] | |
| 5.75 | End-to-end manual test: New word → "Mark as Mastered" button → click → word removed from session → check 90-day interval → button changes to "Unmark as Mastered" | [ ] | |
| 5.76 | End-to-end manual test: Practice session → 40% new, 60% review words selected → overdue words appear first | [ ] | |
| 5.77 | End-to-end manual test: Rate word quality 5 → is_mastered=true → deck mastery % increases → rate quality 3 → is_mastered=false → mastery % decreases | [ ] | |
| 5.78 | End-to-end manual test: Existing user → words migrated to "My Words" deck with SRS fields initialized → old sessions visible in Report Card | [ ] | |
| 5.79 | End-to-end manual test: Mid-session close via close button → remaining words skipped → summary shown inline | [ ] | |
| 5.80 | End-to-end manual test: Mid-session deck switch → confirmation modal → session ends → new deck selected | [ ] | |
| 5.81 | End-to-end manual test: Combine decks → new deck created with word copies (SRS state preserved) → info note displayed | [ ] | |

---

## Implementation Order

Follow the phases in order (A → B → C → D → E → F → G → H → I) to minimize dependency issues.

**Critical path:**
1. Phase A (schema) must complete before any other phase
2. Phase B (deck API) must complete before Phase D (frontend API client)
3. Phase C (practice changes) must complete before Phase F (inline practice)
4. Phases E, F, G can partially overlap but share dependency on Phase D

**Estimated time:** 3-5 days for full implementation + testing (assuming single developer)

---

## Deployment Checklist

- [ ] Run database migration on staging
- [ ] Verify data migration (check "My Words" decks created, SRS fields initialized, confidence_score dropped)
- [ ] Run all backend tests (`pytest`)
- [ ] Run all frontend tests (`npm test`)
- [ ] Deploy backend to staging
- [ ] Deploy frontend to staging
- [ ] Run E2E manual tests on staging
- [ ] Verify SRS word selection (40/60 ratio, overdue first)
- [ ] Verify quality rating menu works
- [ ] Verify "Mark as Mastered" fast-tracks to 90 days
- [ ] Verify mastery status updates correctly (quality 5 → mastered)
- [ ] Verify growth icons reflect mastery % (🌱🌿🌸)
- [ ] Deploy backend to production
- [ ] Deploy frontend to production
- [ ] Monitor logs for errors
- [ ] Verify streak tracking works correctly
- [ ] Verify deck one-liner generation works

---

This checklist should be updated as tasks are completed. Move completed tasks to `[x]`, partially done to `[~]`, and add notes for blockers or edge cases discovered during implementation.
