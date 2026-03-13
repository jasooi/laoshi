# M5 Decks -- Requirements

> Milestone 5: Decks (Collections Redesign)
> Acceptance criteria extracted from [PRD.md](../../.claude/PRD.md) stories #5, #8, and day streak feature

---

## Overview

Milestone 5 transforms Laoshi's UX from a traditional learning app into a chat-app-style interface. Vocabulary is organized into "decks" (themed collections), the home screen becomes a split-panel layout (WhatsApp/Telegram web style), and practice sessions appear inline rather than as a separate page. The warm, muted color scheme and growth-oriented visual metaphors (seedling → blooming flower) create a friendly, inviting feel.

**Key changes:**
- Vocabulary organized into **decks** (1:many Word-to-Deck)
- Home screen: **split-panel layout** (deck list left, detail/practice right)
- Practice sessions: **inline** in right panel, not full-screen
- **Spaced Repetition System (SRS)** using SM-2 algorithm replaces arbitrary confidence scores
- **User self-rating** of word mastery (0-5 quality scale) after each word
- **Day streak** tracking for consecutive practice days
- AI-generated **deck one-liners** about progress
- Vocabulary page renamed to **Library**
- **Warm color scheme** (sage green, muted amber, warm grays) replaces purple
- **Preloaded Laoshi library deferred** to future milestone

---

## User Stories

### #5: Custom Collections (as "Decks")
**As a learner**, I want to create custom decks (e.g. "Business Mandarin", "Restaurant & Food") and organize my words into them so that I can practice contextually related vocabulary together.

**Acceptance Criteria:**
- Users can create a new deck with a name and description
- Decks can be populated via:
  - CSV upload (2-step: create deck, then upload words into it)
  - Manual word addition
  - Combining words from existing decks (words are copied, not linked)
- Each word belongs to exactly one deck
- When combining decks, an info note informs the user that copied words are independent of the originals
- Users can view all decks in the Library page
- Users can edit deck name/description
- Users can delete a deck (cascade deletes its words)
- Users can view all words in a deck (table view with search/sort/paginate)
- Users can edit/delete individual words within a deck

###  #8: Select Deck & Start Practice (Full Implementation)
**As a learner**, I want to select a deck and start a practice session so that I can practice words in a specific context.

**Acceptance Criteria:**
- Home screen shows a list of all user's decks, sorted by reverse recency (least recently practiced first)
- Each deck card displays:
  - Growth icon (🌱 seedling, 🌿 leaves, or 🌸 flower based on mastery %)
  - Recency color (green <48h, yellow 48-120h, red >120h, grey never practiced)
  - Progress bar (same color as icon)
  - Word count (mastered/total)
  - AI-generated one-liner message preview
  - Last practiced timestamp
- Clicking a deck shows deck detail panel with:
  - Circular progress ring
  - Total/mastered word counts
  - Full AI one-liner message
  - "Start Practice" button
  - "Manage in Library →" button
- Clicking "Start Practice" starts a session with words from that deck using SRS algorithm (40% new words, 60% due/overdue review words)
- Practice session appears inline in the right panel (chat interface)
- Session words are filtered by the selected deck
- Users can close the session early via close button (remaining words marked as skipped)
- If user tries to switch decks mid-session, a confirmation modal asks whether to end the current session
- Session summary shows inline (not full-screen) with "Back to Home" navigating to the deck detail view

### Day Streak Tracking
**As a learner**, I want to see my day streak (consecutive days with practice) so that I stay motivated to practice daily.

**Acceptance Criteria:**
- Streak counter visible on home screen (empty state and deck list)
- Streak increments by 1 when the user completes their first practice session of a calendar day
- Completing multiple sessions on the same day does not increment the streak further
- If the user practiced yesterday, streak increments on today's first session
- If the user hasn't practiced in 2+ days, streak resets to 1 on the next session
- Streak data persists across sessions (stored in `UserProfile.current_streak` and `last_practice_date`)

### Deck One-Liner Messages
**As a learner**, I want to see personalized progress messages for each deck so that I understand where I'm improving and what to focus on next.

**Acceptance Criteria:**
- At the end of each practice session, the AI summary agent generates a deck-specific one-liner (max 80 chars)
- The one-liner describes the deck's progress and suggests a next focus area
- Examples: "Your 把 sentences are getting natural! Try 被 constructions next."
- The one-liner is stored on the `Deck.laoshi_message` field
- The message is displayed on the deck card in the left panel (truncated preview)
- The full message is shown in the deck detail panel

### Spaced Repetition System (SRS)
**As a learner**, I want my practice sessions to intelligently prioritize words based on when I need to review them so that I learn more efficiently and retain vocabulary long-term.

**Acceptance Criteria:**
- Words are scheduled for review using the SM-2 spaced repetition algorithm
- Each word tracks: `repetitions`, `interval_days`, `ease_factor`, `next_review_date`
- Word selection uses 40% new words (never reviewed), 60% due/overdue words (sorted by `next_review_date`)
- If either pool is insufficient, use the other pool as buffer
- If both pools insufficient, select words with nearest future `next_review_date`
- After practicing each word, user self-rates their understanding (0-5 quality scale)
- Quality rating updates SRS state: interval increases on success, resets on failure
- "Mark as Mastered" button allows fast-tracking already-known words to 90-day interval
- Mastery status (`is_mastered`) is based on user's quality ratings, not arbitrary confidence scores
- Practice sessions do NOT exclude mastered words (practice is always beneficial)

### Quality Self-Rating
**As a learner**, I want to rate how well I understand each word after practicing it so that the system can schedule reviews appropriately.

**Acceptance Criteria:**
- After clicking "Next Word," user is prompted with a quality rating menu (0-5)
- Rating options:
  - [0] 😣 I don't understand how to use this word
  - [1] 😕 Very unclear - I'm mostly guessing
  - [2] 😐 Somewhat unclear - I struggle to use this word
  - [3] 🙂 Rough understanding - I can use this word but it's awkward
  - [4] 😊 Good grasp - it's mostly natural to me
  - [5] 🤩 Perfect command - I use this word naturally all the time
- User must select a rating before next word appears
- Rating updates word's SRS state (interval, ease_factor, next_review_date)
- Rating updates word's mastery status (quality 5 → mastered, quality ≤3 → not mastered)
- Skipped words (no attempts) are deferred by 1 day without quality rating

---

## Functional Requirements

### FR-1: Deck Management
1. Users can create decks with a name (required) and description (optional)
2. Users can edit deck name and description
3. Users can delete decks (cascade deletes all words in the deck)
4. Users can view a list of all their decks with computed stats:
   - Total word count
   - Mastered word count (where `is_mastered = true`)
   - Mastery percentage (mastered / total)
   - Growth icon based on mastery %: 🌱 (0-24%), 🌿 (25-74%), 🌸 (75-100%)
   - Last practiced timestamp
5. Deck list is sorted by reverse recency (least recently practiced first, nulls first)

### FR-2: Word-to-Deck Relationship
1. Each word belongs to exactly one deck (1:many relationship)
2. Words are created as a deck sub-resource: `POST /api/decks/:id/words`
3. Old `POST /api/words` bulk-create endpoint is removed
4. Individual word operations remain unchanged: `GET/PUT/DELETE /api/words/:id`
5. Deleting a deck cascade-deletes all its words

### FR-3: CSV Import Flow (2-Step)
1. User creates a deck via `POST /api/decks` (returns deck ID)
2. User uploads CSV file via frontend (PapaParse parses client-side)
3. Frontend sends parsed words to `POST /api/decks/:id/words`
4. If step 3 fails, the deck still exists and the user can retry

### FR-4: Deck Combining
1. Users can select multiple source decks
2. System creates a new deck with a user-provided name and description
3. System copies all words from source decks into the new deck (words are duplicated, not linked)
4. An info note informs the user: "Words in this deck are not linked to the origin deck(s)"
5. Changes to words in the new deck do not affect the originals

### FR-5: Home Screen Split-Panel Layout
1. Left panel: Deck list
   - All user's decks sorted by reverse recency
   - Streak badge at top
   - "+ New Deck" button at bottom (navigates to Library)
   - Clicking a deck highlights it and shows detail in right panel
2. Right panel: Nested routes
   - Empty state (`/home`): Laoshi avatar, "Select a deck to begin", streak counter
   - Deck detail (`/home/deck/:deckId`): Progress ring, stats, "Start Practice", "Manage in Library →"
   - Practice session (`/home/deck/:deckId/practice`): Inline chat interface

### FR-6: Inline Practice Sessions
1. Practice sessions appear in the right panel (not full-screen `/practice` route)
2. Chat area in center with messages, feedback cards, typing indicator, input
3. Collapsible word panel on right side showing only current word (character, pinyin, meaning)
4. No practiced/skipped word lists during session
5. Close button (top right) ends session early:
   - Marks remaining unpracticed words as skipped
   - Calls `POST /api/practice/sessions/:id/end`
   - Shows session summary inline
6. Session summary "Back to Home" navigates to `/home/deck/:deckId`

### FR-7: Mid-Session Deck Switch
1. If user clicks a different deck while a session is active, show confirmation modal
2. Modal text: "You have an active practice session. End it and switch decks?"
3. Buttons: "End Session & Switch" / "Cancel"
4. If confirmed, end current session (mark remaining words as skipped), then navigate to new deck

### FR-8: Day Streak Logic
1. On session end, check `UserProfile.last_practice_date`:
   - If today: no change (already counted)
   - If yesterday: increment `current_streak` by 1, set `last_practice_date` = today
   - If older or null: reset `current_streak` to 1, set `last_practice_date` = today
2. Streak data persists in database
3. `GET /api/progress/streak` returns `{current_streak, last_practice_date}`

### FR-9: Deck One-Liner Generation
1. Summary agent JSON output includes new field: `deck_oneliner` (string, max 80 chars)
2. `complete_session()` extracts `deck_oneliner` from summary JSON
3. System updates `Deck.laoshi_message = deck_oneliner`
4. One-liner describes deck progress and suggests next focus

### FR-10: Library Page (Replaces Vocabulary Page)
1. Route changes from `/vocabulary` to `/library`
2. Sidebar link renamed from "Vocabulary" to "Library"
3. **Main Library view** shows:
   - Grid of deck cards (3-4 columns on desktop, responsive)
   - No top-level summary stats
   - "+ Create New Deck" button (top-right) opens dropdown menu with:
     - Manual Creation
     - Upload CSV
     - Combine Decks
     - Shared Decks (deferred to future milestone)
   - Empty state (0 decks): "No decks yet. Create your first deck to start practicing!"
4. **Deck card content** (Library):
   - Deck name (bold, 1-2 lines, truncated)
   - Description (muted gray, 1-2 lines, truncated)
   - Stats row: `{word_count} words  •  {growth_icon} {mastery_percentage}% mastered`
   - Progress bar (colored by recency, NOT mastery)
   - Recency badge (🟢/🟡/🔴/⚫ + time ago, bottom-left)
   - Kebab menu (⋮, top-right): Edit Deck, Delete Deck
   - **NO laoshi_message** (only shown on Home screen)
5. **Recency colors** (applied to growth icon + progress bar):
   - Green: <48h since last practice
   - Yellow: 48-120h
   - Red: >120h
   - Grey: never practiced
6. Clicking a deck navigates to `/library/deck/:deckId` (words table view)
7. **Deck detail view** (`/library/deck/:id`):
   - "← Back to Library" breadcrumb
   - Simplified stats: `{mastered} / {total} mastered ({percentage}%)` + growth icon + stage name
   - Actions: "+ Add Word", "Export"
   - Search bar
   - Words table:
     - Reuses Vocabulary.tsx table pattern
     - Columns: #, 中文, Pinyin, Meaning, Notes, Actions (edit/delete)
     - Search, sort, paginate
     - Edit/delete individual words
   - Info banner (for combined decks): "Words in this deck are copies. Changes here won't affect the original decks."

### FR-11: Data Migration
1. On migration, for each user with words:
   - Create a "My Words" deck
   - Set all existing words' `deck_id` to this default deck
2. Existing sessions remain accessible in Report Card (null `deck_id` for legacy sessions)

### FR-12: Color Scheme
1. Replace purple (#9333EA) with warm, muted tones:
   - Primary: warm sage/olive green (buttons, active states)
   - Accent: muted amber/terracotta (highlights)
   - Backgrounds: warm grays (stone-50, stone-100)
2. Apply consistently across all components

### FR-13: Spaced Repetition System (SM-2)
1. Each word stores SRS state:
   - `repetitions` (int, default 0) - number of successful reviews
   - `interval_days` (int, default 1) - days until next review
   - `ease_factor` (float, default 2.5) - difficulty multiplier
   - `next_review_date` (date, nullable) - NULL = new word, date = review scheduled
2. Word selection algorithm:
   - Calculate target: 40% new words, 60% review words
   - New pool: `next_review_date IS NULL`, random selection
   - Review pool: `next_review_date <= today`, sorted by date ASC (overdue first)
   - Buffer logic: if new pool insufficient, take extra from review pool (and vice versa)
   - Fallback: if both pools insufficient, select words with nearest future `next_review_date`
3. SM-2 update on advance_word():
   - Quality 5: Increase interval (1d → 3d → 7d → ~18d → ~45d → ...)
   - Quality 4: Preserve existing mastery, update ease_factor
   - Quality 3: Remove mastery, update ease_factor
   - Quality 0-2: Reset `repetitions = 0`, `interval_days = 1`, remove mastery
   - Ease factor: `ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))`, clamped to min 1.3
   - Next review: `next_review_date = today + interval_days`
4. Modified intervals for language learning:
   - `repetitions = 0` + quality = 5: `interval_days = 14` (fast-track for perfect first attempt)
   - `repetitions = 0` + quality 3-4: `interval_days = 1`
   - `repetitions = 1` + quality ≥ 3: `interval_days = 3`
   - `repetitions = 2` + quality ≥ 3: `interval_days = 7`
   - `repetitions ≥ 3` + quality ≥ 3: `interval_days = ceil(interval_days * ease_factor)` if < 7, else `round()`
5. Skip without attempts: `next_review_date += 1 day`, no other changes

### FR-14: Quality Self-Rating
1. After user clicks "Next Word," show quality rating menu (chat-style button menu)
2. Menu header: "How well do you understand how to use this word?"
3. 6 button options (0-5) with emoji + description:
   - [0] 😣 I don't understand how to use this word
   - [1] 😕 Very unclear - I'm mostly guessing
   - [2] 😐 Somewhat unclear - I struggle to use this word
   - [3] 🙂 Rough understanding - I can use this word but it's awkward
   - [4] 😊 Good grasp - it's mostly natural to me
   - [5] 🤩 Perfect command - I use this word naturally all the time
4. User must select before next word appears (blocks progression)
5. Selection triggers `update_srs(word, quality)` and `update_mastery_status(word)`
6. Next word is then loaded and displayed

### FR-15: Mastery Status (Dynamic)
1. Each word tracks:
   - `last_quality` (int 0-5, nullable) - most recent quality rating
   - `marked_as_known` (bool, default false) - manually marked by user
   - `is_mastered` (bool, default false) - computed mastery state
2. Mastery logic (Option B - Lenient):
   - Quality 5 → `is_mastered = true`
   - Quality 4 → preserve existing `is_mastered` (no change)
   - Quality ≤ 3 → `is_mastered = false`
   - `marked_as_known = true` → `is_mastered = true`
3. Mastery is display-only (used for stats, growth icons)
4. Mastered words are NOT excluded from practice sessions (SRS handles scheduling)
5. Growth icons based on mastery %:
   - 🌱 Seedling: 0-24% mastered
   - 🌿 Growing: 25-74% mastered
   - 🌸 Flower: 75-100% mastered

### FR-16: "Mark as Mastered" Button
1. "Mark as Mastered" button appears on word card during practice sessions
2. Clicking triggers immediate fast-track:
   - `marked_as_known = true`
   - `last_quality = 5`
   - `is_mastered = true`
   - `repetitions = 5`
   - `interval_days = 90`
   - `ease_factor = 2.5`
   - `next_review_date = today + 90 days`
3. Word is removed from current session (next word appears immediately)
4. No quality rating prompt shown for marked-as-mastered words
5. Button toggles: if word is already mastered, clicking shows "Unmark as Mastered" which resets `marked_as_known = false` and recalculates mastery status based on `last_quality`

---

## Non-Functional Requirements

### NFR-1: Performance
- `GET /api/decks` must use SQLAlchemy subqueries to compute stats in a single query (avoid N+1)
- Deck list must render without noticeable lag even with 50+ decks

### NFR-2: Data Integrity
- Deck deletion cascade-deletes words (no orphan words)
- Migration is idempotent (checks if user already has decks before creating default)

### NFR-3: API Consistency
- Words created via `POST /api/decks/:id/words` only (RESTful parent-child pattern)
- Individual word operations remain globally addressable via word ID

### NFR-4: Usability
- Confirmation required before destructive mid-session deck switch
- Info notes inform users about word copying behavior
- Empty states guide users (no decks, no words, etc.)

---

## Out of Scope (Deferred)

- **Preloaded Laoshi Library**: Browse and import officially curated vocabulary sets (deferred to future milestone)
- **Many-to-Many Word-Deck Relationship**: Each word belongs to exactly one deck in this milestone
- **Deck Sharing**: Users cannot share decks with other users
- **Deck Import/Export**: No deck-level CSV import/export beyond word-level operations

---

## Success Criteria

1. Users can create, edit, delete, and view decks
2. CSV import works via 2-step flow (create deck → upload words)
3. Users can combine decks (words are copied)
4. Home screen shows deck list and inline practice
5. Practice sessions use SRS algorithm to select 40% new, 60% review words
6. Quality rating menu (0-5) appears after each word, blocks progression until selected
7. Word SRS state updates correctly based on quality rating (intervals: 1d → 3d → 7d → ~18d)
8. Mastery status updates dynamically (quality 5 → mastered, quality ≤3 → not mastered)
9. "Mark as Mastered" button fast-tracks words to 90-day interval
10. Growth icons (🌱🌿🌸) reflect deck mastery percentage correctly
11. Day streak increments correctly on daily practice
12. Deck one-liners are generated and displayed
13. Existing words are migrated to "My Words" default deck with SRS fields initialized
14. Library page replaces Vocabulary page
15. Warm color scheme applied consistently
16. All tests pass (backend + frontend)
