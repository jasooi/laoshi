# M5 Decks -- Tasks

> Granular implementation checklist for Milestone 5: Decks (Collections Redesign)
> Task status legend: `[x]` done | `[~]` partially done | `[ ]` not started

---

## Phase A: Database Schema

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Backend: Create `Deck` model (id, name, description, user_id FK, laoshi_message, created_ds, updated_ds) with relationships to User, Word, UserSession | [x] | In `backend/models.py` |
| 5.2 | Backend: Add `deck_id` FK (nullable) + SRS fields (`repetitions`, `interval_days`, `ease_factor`, `next_review_date`) + mastery fields (`last_quality`, `marked_as_known`, `is_mastered`) to `Word` model, **remove** `confidence_score` | [x] | Nullable deck_id only during migration |
| 5.3 | Backend: Add `deck_id` FK (nullable) to `UserSession` model + `deck` relationship | [x] | Null for legacy sessions |
| 5.4 | Backend: Add `current_streak` (Integer, default=0) and `last_practice_date` (Date, nullable) to `UserProfile` | [x] | For day streak tracking |
| 5.5 | Backend: Add `Word.update_mastery_status()` method (quality 5 → mastered, quality ≤3 → not mastered, quality 4 preserves state) | [x] | |
| 5.5a | Backend: Update `Word.format_data()` and `UserSession.format_data()` to include `deck_id` and SRS/mastery fields | [x] | |
| 5.6 | Backend: Create Alembic migration for Deck table + SRS/mastery fields on Word + FK columns + **drop** `confidence_score` + data migration (create "My Words" deck per user, assign existing words, SRS fields auto-initialized via server defaults) | [x] | In `backend/migrations/versions/` |
| 5.7 | Backend: Run migration and verify existing data migrated correctly | [x] | Test with dev database |

---

## Phase B: Backend Deck API

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.8 | Backend: Create `deck_resources.py` — `GET /api/decks` with computed stats (word_count, mastered_count where `is_mastered=true`, mastery_percentage, last_practiced_at) using SQLAlchemy subqueries to avoid N+1 | [x] | Use `scalar_subquery()` |
| 5.9 | Backend: `POST /api/decks` — create empty deck (name, description) | [x] | |
| 5.10 | Backend: `GET /api/decks/:id` — deck detail + stats | [x] | |
| 5.11 | Backend: `PUT /api/decks/:id` — update name/description | [x] | |
| 5.12 | Backend: `DELETE /api/decks/:id` — delete deck + cascade delete words | [x] | SQLAlchemy cascade='all, delete-orphan' |
| 5.13 | Backend: `GET /api/decks/:id/words` — paginated word list for deck (reuse `paginate_query`) | [x] | |
| 5.14 | Backend: `POST /api/decks/:id/words` — create words inside deck (replaces old `POST /api/words`) | [x] | Bulk create endpoint |
| 5.15 | Backend: `POST /api/decks/combine` — create new deck + copy words from source decks | [x] | Loop through source_deck_ids, copy words |
| 5.16 | Backend: `GET /api/progress/streak` — return current_streak and last_practice_date | [x] | In `report_card_resources.py` or new `streak_resources.py` |
| 5.17 | Backend: Register all deck resources in `app.py` | [x] | `api.add_resource(...)` |
| 5.18 | Backend: **Remove** `POST /api/words` and `DELETE /api/words` endpoints from `resources.py` | [x] | Remove `WordListResource.post()` and `.delete()` methods |
| 5.19 | Backend: Update `GET /api/words` to accept optional `deck_id` query param for filtering | [x] | Filter by deck_id if provided |

---

## Phase C: Backend Practice & AI Changes

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.20 | Backend: Update `POST /api/practice/sessions` to require `deck_id` in request body | [x] | In `practice_resources.py` |
| 5.21 | Backend: Modify `initialize_session()` to use SRS word selection (40% new words where `next_review_date IS NULL`, 60% review words where `next_review_date <= today`, sorted by date ASC, buffer pools if insufficient, fallback to future words) | [x] | In `practice_runner.py` |
| 5.22 | Backend: Set `session.deck_id = deck_id` in `initialize_session()` | [x] | |
| 5.23 | Backend: Create `POST /api/practice/sessions/:id/end` endpoint — marks remaining SessionWords as skipped, calls `complete_session()` | [x] | New resource in `practice_resources.py` |
| 5.24 | Backend: Update `build_summary_prompt()` in `chat_agents.py` to add `deck_oneliner` to JSON output spec (max 80 chars, progress + next focus) | [x] | |
| 5.25 | Backend: Modify `complete_session()` in `practice_runner.py` to extract `deck_oneliner` from summary JSON and update `Deck.laoshi_message` | [x] | |
| 5.26 | Backend: Implement streak update logic in `complete_session()` — check last_practice_date, increment or reset current_streak, update last_practice_date to today | [x] | Create `update_streak()` helper with SELECT FOR UPDATE locking |
| 5.26a | Backend: Implement `update_srs(word, quality)` function — SM-2 algorithm with modified intervals (1d → 3d → 7d → ~18d), quality <3 resets, ease_factor updates, fast-track quality 5 on rep 0 | [x] | In `practice_runner.py` |
| 5.26b | Backend: Implement `mark_word_as_mastered(word)` and `unmark_word_as_mastered(word)` functions — sets repetitions=5, interval=90, is_mastered=true, last_quality=5 | [x] | In `practice_runner.py` |
| 5.26c | Backend: Modify `advance_word()` to accept `quality` parameter, call `update_srs()`, call `word.update_mastery_status()`, handle skip (defer by 1 day) | [x] | In `practice_runner.py` |
| 5.26d | Backend: Update `POST /api/practice/sessions/:id/next-word` signature to accept `{quality: int}` in request body | [x] | In `practice_resources.py` |
| 5.26e | Backend: Create `POST /api/words/:id/mark-as-mastered` endpoint — toggles mastered status, returns word data | [x] | In `resources.py` (word resources) |

---

## Phase D: Frontend Types & API Client

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.27 | Frontend: Add `DeckListItem`, `DeckDetail`, `DeckWithStats` interfaces to `types/api.ts`, update `Word` interface with SRS fields (repetitions, interval_days, ease_factor, next_review_date, last_quality, marked_as_known, is_mastered), **remove** `confidence_score` | [x] | |
| 5.28 | Frontend: Create `deckApi` helper group in `lib/api.ts` (getDecks, createDeck, updateDeck, deleteDeck, getDeckWords, addWordsToDeck, combineDecks) | [x] | |
| 5.29 | Frontend: Add `getStreak()` to `progressApi` in `lib/api.ts` | [x] | |
| 5.30 | Frontend: Update `practiceApi.startSession()` to accept `deckId` parameter | [x] | Send `{deck_id, words_count?}` in body |
| 5.31 | Frontend: Update `practiceApi.advanceWord()` to accept `quality` parameter | [x] | Send `{quality}` in body to POST /next-word |
| 5.32 | Frontend: Add `practiceApi.endSession(sessionId)` for new POST /end endpoint | [x] | |
| 5.33 | Frontend: Add `wordsApi.markAsMastered(wordId)` for new POST /words/:id/mark-as-mastered endpoint | [x] | |
| 5.34 | Frontend: **Remove** old bulk word creation API calls from codebase | [x] | Search for usages of old `POST /api/words` |

---

## Phase E: Frontend Home Page Rewrite

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.35 | Frontend: Create `pages/home/HomeContext.tsx` — React context with selectedDeckId, activePracticeSessionId, selectDeck(), startPractice(), endPractice() | [x] | |
| 5.36 | Frontend: Create `pages/home/DeckListPanel.tsx` — left panel with GET /api/decks, streak badge, DeckListItem components, "+ New Deck" button | [x] | |
| 5.37 | Frontend: Create `pages/home/DeckListItem.tsx` — growth icon (🌱 seedling 0-24%, 🌿 leaves 25-74%, 🌸 flower 75-100% based on mastery %), recency color (green/yellow/red/grey), progress bar, word count, laoshi message preview | [x] | Embedded in DeckListPanel.tsx |
| 5.38 | Frontend: Create `pages/home/DeckDetailPanel.tsx` — right panel with circular progress ring (SVG), stats, full laoshi message, "Start Practice" and "Manage in Library →" buttons | [x] | |
| 5.39 | Frontend: Create `pages/home/EmptyDeckPlaceholder.tsx` — default right panel with Laoshi avatar, "Select a deck to begin", streak counter | [x] | |
| 5.40 | Frontend: Create `pages/home/EndSessionModal.tsx` — confirmation modal for mid-session deck switch | [x] | Embedded in home/index.tsx |
| 5.41 | Frontend: Rewrite `pages/Home.tsx` — split-panel layout with DeckListPanel (left) + Outlet (right), wrap in HomeProvider | [x] | |
| 5.42 | Frontend: Update `App.tsx` routing — nested routes under /home (`/home`, `/home/deck/:deckId`, `/home/deck/:deckId/practice`), remove standalone `/practice` route | [x] | |

---

## Phase F: Frontend Inline Practice Panel

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.43 | Frontend: Create `pages/home/PracticePanel.tsx` — refactor Practice.tsx logic inline, chat area center, collapsible word panel right side, close button top right | [x] | |
| 5.44 | Frontend: Create quality rating menu component — 6 buttons (0-5) with emoji + labels, appears after user clicks "Next Word", blocks progression until selection, calls `advanceWord(quality)` | [x] | See design.md Section 7.1 |
| 5.45 | Frontend: Add "Mark as Mastered" button to word card — always visible, toggles between "Mark as Mastered" and "Unmark as Mastered", calls `wordsApi.markAsMastered()`, removes word from session, shows next word | [x] | See design.md Section 7.2 |
| 5.46 | Frontend: Extract practice session state logic into custom `usePracticeSession` hook for reusability | [ ] | Optional but recommended - NOT DONE |
| 5.47 | Frontend: Remove practiced/skipped word lists from session UI (keep only current word panel) | [x] | |
| 5.48 | Frontend: Wire close button to `POST /api/practice/sessions/:id/end`, show SessionSummary inline | [x] | |
| 5.49 | Frontend: Update `SessionSummary.tsx` to support inline rendering mode (not full-screen overlay) | [x] | Inline summary rendered in PracticePanel |
| 5.50 | Frontend: Update SessionSummary "Back to Home" to navigate to `/home/deck/:deckId` instead of `/home` | [x] | |
| 5.51 | Frontend: **Delete** `pages/Practice.tsx` (logic fully moved to PracticePanel) | [x] | |

---

## Phase G: Frontend Library Page

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.52 | Frontend: Create `pages/Library.tsx` — grid layout (3-4 cols), deck cards with growth icon + recency colors + progress bar + kebab menu (⋮), "+ Create New Deck" dropdown (Manual Creation, Upload CSV, Combine Decks, Shared Decks), empty state ("No decks yet..."), NO laoshi_message | [~] | Split-panel layout (not grid). Kebab menu ✅, dropdown menu ✅, recency colors ✅, inline edit ✅. Grid layout still TODO. |
| 5.53 | Frontend: Create `pages/library/CreateDeckModal.tsx` — triggered by dropdown menu items (Manual Creation, Upload CSV, Combine Decks), name + description fields | [x] | Embedded in library/index.tsx |
| 5.54 | Frontend: Create `pages/library/DeckWordsView.tsx` — "← Back to Library" breadcrumb, simplified stats ("102 / 156 mastered (65%)" + growth icon + stage name), words table (reuse Vocabulary.tsx pattern) with Status column (New/In Review/Mastered), search/sort/paginate, edit/delete words, "+ Add Word" + "Export" buttons, info banner for combined decks | [~] | Word list with Status column implemented. Missing search/sort, edit/delete individual words, Export button |
| 5.55 | Frontend: Create `pages/library/CombineDecksModal.tsx` — multi-select decks, name + description for new deck, info note about word copying | [x] | |
| 5.56 | Frontend: Move `pages/vocabulary/UploadModal.tsx` to `pages/library/UploadModal.tsx`, update to accept `deckId` prop, call new 2-step CSV flow (create deck → upload words) | [~] | Upload modal embedded in library/index.tsx but not moved from vocabulary/ |
| 5.57 | Frontend: Move `pages/vocabulary/EditWordModal.tsx` to `pages/library/EditWordModal.tsx` | [ ] | NOT YET IMPLEMENTED |
| 5.58 | Frontend: Update `App.tsx` routing — add `/library` and `/library/deck/:deckId`, **remove** `/vocabulary` route | [x] | |
| 5.59 | Frontend: **Delete** `pages/Vocabulary.tsx` (replaced by Library.tsx) | [x] | |

---

## Phase H: Frontend Sidebar, Color Scheme & Library UI Polish

### H1: Tailwind Config & Sidebar

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.60 | Frontend: Update `tailwind.config.js` — replace old `primary-*` (purple) and custom `stone-*` tokens with Quiet Study theme: `warm-*` (offwhite, black, gray, muted), `sage` + `sage-tint`, `amber` + `amber-tint`, `coral` + `coral-tint`, `neutral` + `neutral-tint`. Add `fontFamily` (Inter sans, Lora serif). | [x] | See design.md Section 6.1. Also added safelist + Google Fonts `<link>` in index.html |
| 5.61 | Frontend: Update `components/Sidebar.tsx` — reorder items to Home, **Library**, Report Card, Settings. Replace `bg-purple-100 text-purple-600` active state with `bg-sage-tint text-sage`. | [x] | Library moved above Report Card |

### H2: Library Page UI Polish

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.62 | Frontend: Rewrite `DeckCard` in `pages/library/index.tsx` — white bg, `h-[240px]`, `border-l-[3px]` with recency color, description with `line-clamp-2`, stats row with growth emoji + mastery %, progress bar (recency fill + tint track), recency badge pill (bottom-left) | [x] | Use `getRecencyStyle()` and `getGrowthEmoji()` helpers |
| 5.62a | Frontend: Add `getRecencyStyle()` helper — returns `{ border, badgeBg, badgeText, progressFill, progressTrack }` using sage/amber/coral/neutral tokens based on hours since last practice | [x] | See design.md Section 6.4 |
| 5.62b | Frontend: Add `getGrowthEmoji()` helper — 🌱 (<25%), 🌿 (25-74%), 🌸 (75-100%) | [x] | |
| 5.62c | Frontend: Add `formatRecency()` helper — returns "2h ago", "Yesterday", "3 days ago", "Never" etc. | [x] | |
| 5.63a | Frontend: Add kebab menu (⋮) to deck cards — appears on card hover, dropdown with "Edit Deck" (PencilIcon) and "Delete Deck" (Trash2Icon, text-coral) | [x] | Use Lucide `MoreVertical`, `Pencil`, `Trash2` icons |
| 5.63b | Frontend: Implement inline edit mode on deck cards — card transforms in-place with `<input>` for name (auto-focus, select-all) and `<textarea>` for description (2 rows), `ring-2 ring-sage` highlight, Save/Cancel buttons, Enter/Esc keyboard shortcuts. Save calls `PUT /api/decks/:id`. | [x] | See design.md Section 6.6 |
| 5.63c | Frontend: Add delete confirmation with word count warning — `confirm("Delete '{name}'? This will permanently delete {count} words. This cannot be undone.")` | [x] | Replaces old `confirm('Are you sure?')` |

### H2b: Home Page UI Polish

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.66a | Frontend: Rewrite `DeckListItem` in `DeckListPanel.tsx` — change from card layout to chat-app list item layout (border-b separator, px-5 py-4), add recency-colored circle avatar (w-11 h-11 rounded-full) with Lucide growth icon (Sprout/Leaf/Flower2, white on colored bg), laoshi message preview below name, progress bar indented under avatar (pl-[60px], h-1.5, bg-warm-gray/60 track), tiny word count right of bar (text-[10px]), time ago right-aligned next to name | [x] | See design.md Section 5.2 DeckListItem spec |
| 5.66b | Frontend: Update `DeckListItem` active state — replace `border-primary-500 bg-primary-50` with `bg-sage-tint` + absolute left indicator `w-[3px]` colored by recency | [x] | |
| 5.66c | Frontend: Add `getRecencyColor()` function to DeckListPanel — returns `{ bg, bar, tint }` hex values for inline styles (sage=#6B8F71, amber=#C4973B, coral=#D4715E, neutral=#A8A5A0) | [x] | Different from Library's `getRecencyStyle()` which returns Tailwind classes |
| 5.66d | Frontend: Add `getGrowthIcon()` function — returns Lucide `<Sprout>` (<25%), `<Leaf>` (25-74%), `<Flower2>` (75-100%) components | [x] | 3 tiers, Lucide icons |
| 5.66e | Frontend: Update DeckListPanel header/streak/button — replace `bg-stone-50` with `bg-warm-offwhite`, `border-stone-200` with `border-warm-gray`, `bg-primary-600` with `bg-sage`, streak text with warm-black | [x] | |
| 5.67a | Frontend: Rewrite `DeckDetailPanel.tsx` as DeckLobby — max-w-3xl horizontal 2-column layout (progress ring left, content right), rounded-3xl p-12 card, decorative blurred sage-tint circle, gap-12 flex row | [x] | See design.md Section 5.2 DeckLobby spec |
| 5.67b | Frontend: Create `<ProgressRing>` component — reusable SVG circular progress, size/strokeWidth props, stroke-warm-gray track, stroke-sage fill, center text (percentage + "mastered") | [x] | Extract from current inline CircularProgress |
| 5.67c | Frontend: Update DeckLobby title to font-serif text-4xl (Lora), add "Last practiced" pill badge (bg-warm-gray/30 rounded-full), 3-column stats grid (Total Words, Practiced, Mastered in text-sage), laoshi message in quote box (bg-sage-tint/50 rounded-2xl border-warm-gray/50) | [x] | |
| 5.67d | Frontend: Update DeckLobby buttons — horizontal row: Start Practice (bg-sage rounded-xl px-8 py-4 text-lg with PlayIcon) + Manage in Library text link (text-warm-black/40 with ArrowRightIcon + hover translate-x animation) | [x] | Replaces stacked full-width buttons |
| 5.67e | Frontend: Add framer-motion entrance animation to DeckLobby — `initial={{ opacity: 0, scale: 0.98 }}`, `animate={{ opacity: 1, scale: 1 }}`, `transition={{ duration: 0.2 }}` | [x] | `framer-motion` already installed |
| 5.67f | Frontend: Update `EmptyDeckPlaceholder.tsx` — replace `bg-stone-50` with `bg-warm-offwhite`, `bg-stone-200` with `bg-warm-gray`, `bg-primary-600` with `bg-sage`, `text-stone-*` with `text-warm-*` | [x] | |

### H3: Theme Replacement — M5 New Components (`primary-*` → `sage`)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.64a | Frontend: Replace all `primary-*` classes in `pages/library/index.tsx` with sage theme equivalents | [x] | `bg-primary-600` → `bg-sage`, `text-primary-600` → `text-sage`, `focus:ring-primary-500` → `focus:ring-sage`, etc. |
| 5.64b | Frontend: Replace all `primary-*` classes in `pages/home/DeckListPanel.tsx` | [x] | |
| 5.64c | Frontend: Replace all `primary-*` classes in `pages/home/DeckDetailPanel.tsx` | [x] | |
| 5.64d | Frontend: Replace all `primary-*` classes in `pages/home/PracticePanel.tsx` | [x] | Also fixed leftover `stone-*` → `warm-*` in PracticePanel + home/index.tsx EndSessionModal |
| 5.64e | Frontend: Replace all `primary-*` classes in `pages/home/EmptyDeckPlaceholder.tsx` | [x] | |

### H4: Theme Replacement — Existing Components (`purple-*` → `sage`)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.65a | Frontend: Replace `purple-*` classes in `components/Sidebar.tsx` | [x] | Already handled by 5.61 |
| 5.65b | Frontend: Replace `purple-*` classes in `pages/Progress.tsx` (Report Card) | [x] | Charts, stats, score highlights |
| 5.65c | Frontend: Replace `purple-*` classes in `components/SessionSummary.tsx` | [x] | Summary cards, buttons |
| 5.65d | Frontend: Replace `purple-*` classes in `pages/Settings.tsx` | [x] | Form elements, buttons |
| 5.65e | Frontend: Replace `purple-*` classes in `pages/settings/EditApiKeyModal.tsx` | [x] | Modal buttons |
| 5.65f | Frontend: Replace `purple-*` classes in `components/FeedbackCard.tsx` | [x] | Score highlights |
| 5.65g | Frontend: Replace `purple-*` classes in `components/Pagination.tsx` | [x] | Active page, buttons |
| 5.65h | Frontend: Replace `purple-*` classes in `pages/Register.tsx` | [x] | Form, submit button |
| 5.65i | Frontend: Replace `purple-*` classes in `components/ProtectedRoute.tsx` | [x] | Loading spinner |
| 5.65j | Frontend: Replace `purple-*` classes in `pages/Login.tsx` | [x] | Form, submit button, links |
| 5.65k | Frontend: Replace `purple-*` classes in `pages/Welcome.tsx` | [x] | CTA buttons, hero section |
| 5.65l | Frontend: Update `test/Pagination.test.tsx` — fix CSS class assertions for new theme | [x] | Test may assert `purple-*` classes |

---

## Phase I: Testing

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.70 | Backend: Create `tests/test_deck_api.py` — unit + integration tests for all deck endpoints | [ ] | Test auth, stats computation with `is_mastered`, sorting, cascade delete |
| 5.71 | Backend: Unit tests for `update_srs()` — quality 0-5, interval progression (1→3→7→18), ease_factor updates, fast-track quality 5 on rep 0, harsh reset on quality <3 | [ ] | In `tests/test_practice_runner.py` |
| 5.72 | Backend: Unit tests for `Word.update_mastery_status()` — quality 5 → mastered, quality ≤3 → not mastered, quality 4 preserves state | [ ] | In `tests/test_models.py` |
| 5.73 | Backend: Unit tests for `mark_word_as_mastered()` and `unmark_word_as_mastered()` — sets 90-day interval, is_mastered=true, last_quality=5, toggle behavior | [ ] | In `tests/test_practice_runner.py` |
| 5.74 | Backend: Unit tests for SRS word selection — 40/60 ratio, buffer pools, fallback to future words | [ ] | In `tests/test_practice_runner.py` |
| 5.75 | Backend: Unit tests for streak logic in `practice_runner.py` | [ ] | Test today, yesterday, older, null cases |
| 5.76 | Backend: Integration tests for `POST /api/practice/sessions/:id/next-word` with quality param — SRS state updates, mastery updates | [ ] | In `tests/test_practice_api.py` |
| 5.77 | Backend: Integration test for `POST /api/words/:id/mark-as-mastered` — verifies fast-track and toggle logic | [ ] | In `tests/test_words_api.py` |
| 5.78 | Backend: Update existing tests broken by API changes (removal of POST /api/words, removal of confidence_score, addition of deck_id to sessions, SRS fields) | [ ] | Fix failing tests in `tests/test_practice_api.py`, `tests/test_words_api.py` |
| 5.79 | Frontend: Component tests for new Home components (DeckListPanel, DeckDetailPanel, PracticePanel, quality rating menu) | [ ] | Use React Testing Library |
| 5.80 | Frontend: Component tests for Library page components (CreateDeckModal, CombineDecksModal, DeckWordsView, inline edit, kebab menu) | [ ] | Include inline edit save/cancel, delete confirmation |
| 5.81 | End-to-end manual test: Fresh user → create deck via CSV → deck appears (🌱) → practice → quality rating menu → rate words → SRS intervals update → session end → streak incremented → mastery % updates → growth icon changes (🌱→🌿) | [ ] | |
| 5.82 | End-to-end manual test: New word → "Mark as Mastered" button → click → word removed from session → check 90-day interval → button changes to "Unmark as Mastered" | [ ] | |
| 5.83 | End-to-end manual test: Practice session → 40% new, 60% review words selected → overdue words appear first | [ ] | |
| 5.84 | End-to-end manual test: Rate word quality 5 → is_mastered=true → deck mastery % increases → rate quality 3 → is_mastered=false → mastery % decreases | [ ] | |
| 5.85 | End-to-end manual test: Existing user → words migrated to "My Words" deck with SRS fields initialized → old sessions visible in Report Card | [ ] | |
| 5.86 | End-to-end manual test: Mid-session close via close button → remaining words skipped → summary shown inline | [ ] | |
| 5.87 | End-to-end manual test: Mid-session deck switch → confirmation modal → session ends → new deck selected | [ ] | |
| 5.88 | End-to-end manual test: Combine decks → new deck created with word copies (SRS state preserved) → info note displayed | [ ] | |
| 5.89 | End-to-end manual test: Library deck card inline edit — click kebab → Edit Deck → name/desc input → Enter saves → Esc cancels | [ ] | |
| 5.90 | End-to-end manual test: Library deck card delete — click kebab → Delete Deck → confirm with word count → deck removed | [ ] | |
| 5.91 | End-to-end manual test: Quiet Study theme applied — all pages use sage/amber/coral/neutral tokens, no purple remnants | [ ] | Check all 20 files listed in design.md Section 6.3 |
| 5.92 | End-to-end manual test: Home DeckListItem — chat-app style list item, recency-colored circle avatar with Lucide growth icon, progress bar indented under avatar, laoshi message preview, active state with left indicator | [ ] | |
| 5.93 | End-to-end manual test: Home DeckLobby — horizontal 2-column layout, progress ring, serif title, 3-column stats, laoshi message quote box, horizontal button row, framer-motion entrance animation | [ ] | |

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
- [ ] Verify Quiet Study theme applied (no purple remnants across all 20 files)
- [ ] Verify Library deck card: inline edit (Enter/Esc), kebab menu, delete confirmation with word count
- [ ] Verify sidebar order: Home, Library, Report Card, Settings
- [ ] Verify recency colors use sage/amber/coral/neutral tokens
- [ ] Deploy backend to production
- [ ] Deploy frontend to production
- [ ] Monitor logs for errors
- [ ] Verify streak tracking works correctly
- [ ] Verify deck one-liner generation works

---

This checklist should be updated as tasks are completed. Move completed tasks to `[x]`, partially done to `[~]`, and add notes for blockers or edge cases discovered during implementation.
