# Milestone 7: Practice Session Redesign -- Requirements Document

## Feature Overview

Milestone 7 transforms the practice session from an inline split-panel view (rendered inside the Home page alongside the deck list) into an immersive full-screen experience. The practice screen should feel like entering a messaging conversation -- the user picks a deck, enters practice fully, and returns when done.

**What already exists:**
- `PracticePanel.tsx` renders inline at `/home/deck/:deckId/practice/:sessionId` with deck list visible on the left.
- `HomeContext.tsx` manages deck selection and practice session state via URL routing.
- `SessionSummary.tsx` renders inline within PracticePanel.
- `FeedbackCard.tsx` shows grammar/usage/naturalness scores after AI responses.
- `QualityRatingModal` (inside PracticePanel) shows a centered modal with 6 emoji-based options (0-5).
- `WordPanel` (inside PracticePanel) shows current word in a collapsible right sidebar (288px).
- `practiceApi` in `lib/api.ts` handles all practice session API calls.
- `framer-motion` is already installed.
- Warm color scheme (sage, warm-black, warm-gray, etc.) is already configured in Tailwind.

**What this milestone delivers:**
1. **State-driven practice overlay**: Practice renders as full-screen content (filling the Layout content area, sidebar remains). No URL change -- session state stored in HomeContext + localStorage for persistence.
2. **Loading ritual screen**: Animated transition with pulsing Laoshi logo and rotating messages before practice begins.
3. **Floating word pill**: Replaces the right sidebar WordPanel with a sticky pill at the top of the chat area (collapsed/expanded states).
4. **Inline confidence rating**: Replaces the modal QualityRatingModal with rating buttons attached directly below a Laoshi message inside the chat.
5. **Redesigned chat UI**: Updated message bubble styling, progress bar, chat header, compound input area, word dividers.
6. **Restyled session summary**: Full-screen layout with spec-matched colors and typography.

**No backend changes required for practice API.** The practice API (startSession, sendMessage, nextWord, endSession, getSummary) remains unchanged.

---

## User Stories

### US-01: Immersive practice experience
**As a** learner, **I want** the practice session to fill the entire screen (minus sidebar) when I start practicing **so that** I can focus on the conversation without distraction from the deck list.

**Acceptance Criteria:**
- Clicking "Start Practice" on DeckDetailPanel shows a loading ritual, then the full-screen practice chat.
- The deck list panel is NOT visible during practice.
- The app navigation sidebar remains visible on the left.
- The URL does NOT change when entering/exiting practice (stays at `/home/deck/:deckId`).
- No deck ID or session ID appears in the URL.

### US-02: Loading ritual transition
**As a** learner, **I want** a brief animated loading screen between clicking "Start Practice" and seeing the chat **so that** the transition feels intentional and warm, not abrupt.

**Acceptance Criteria:**
- A loading screen appears with the Laoshi logo pulsing gently.
- Rotating text messages appear below the logo: "Digging up the scrolls...", "Preparing the tea...", "Lighting the candles...", "Setting the mood..."
- Messages rotate every 1200ms.
- After all messages cycle (~4800ms), the loading screen transitions to the practice chat.

### US-03: Floating word pill
**As a** learner, **I want** to see the current vocabulary word in a compact pill pinned to the top of the chat **so that** I can reference it without a side panel taking up screen space.

**Acceptance Criteria:**
- The word pill is sticky at the top of the scrollable chat area.
- Collapsed state shows: Chinese character, pinyin, em dash, English meaning, expand chevron.
- Clicking the pill expands it to show larger character (48px), pinyin, full meaning, and user note (if exists).
- Clicking outside the expanded pill collapses it.
- When advancing to the next word, the pill content transitions smoothly (slide out left, slide in right).

### US-04: Inline confidence rating with retroactive editing
**As a** learner, **I want** to rate my confidence directly in the chat flow (not in a popup modal) and be able to edit past ratings **so that** the rating feels like part of the conversation and I can correct mistakes.

**Acceptance Criteria:**
- After clicking "Next Word", a typing indicator shows briefly (800ms).
- Laoshi sends a message: "Before we move on -- how confident are you using **WORD**?"
- 6 rating buttons (0-5) appear attached below the message bubble: Blackout, Wrong, Hard, OK, Good, Easy.
- After selecting a rating, the button row collapses and a **color-coded pill** shows the selected rating:
  - 0-2 (Blackout/Wrong/Hard): coral/red tones (struggling)
  - 3 (OK): amber/yellow (okay)
  - 4-5 (Good/Easy): sage/green (confident)
- A small **edit icon** (pencil) appears next to the pill.
- Clicking the edit icon reopens the rating buttons.
- Selecting a new rating collapses the buttons and updates the pill with the new color + label.
- **Retroactive editing**: The user can scroll back to any previously rated word during the session and edit its rating. The edit calls a separate backend API (`POST /api/words/:id/rerate`) that restores the word's SRS state from a snapshot and applies the new quality. This does not affect the current word or practice flow.
- The text input area shows a "locked" state during the rating flow.

### US-05: Session persistence across refresh
**As a** learner, **I want** my active practice session to survive a page refresh **so that** I don't lose progress if I accidentally reload.

**Acceptance Criteria:**
- Active session ID and deck ID are stored in localStorage.
- On page load, if an active session exists in localStorage, the practice overlay resumes.
- When a session ends normally (complete or ended early), localStorage is cleared.

### US-06: Redesigned chat UI
**As a** learner, **I want** the chat to look and feel like a real messaging app **so that** practice feels warm and familiar.

**Acceptance Criteria:**
- 3px progress bar at the top of the chat column, sage green fill, animates with word progress.
- Chat header (56px) with: back chevron (triggers End Session modal), Laoshi avatar + name + online dot, deck name + word counter on right.
- User message bubbles: sage green background (#6B8F71) with white text.
- AI message bubbles: white background with warm-gray border, Laoshi avatar (28px) aligned to bottom-left.
- FeedbackCard continues to render inline below AI messages (unchanged).
- Compound input area with textarea (top) and action bar (bottom: Next Word button left, char count + Submit right).
- "Next Word" button disabled until feedback is received.
- Thin word divider line with "next word" text appears between words.

### US-07: End session flow
**As a** learner, **I want** the back button in the practice header to confirm before ending my session **so that** I don't accidentally lose progress.

**Acceptance Criteria:**
- Clicking the back chevron opens the End Session modal.
- Modal has yellow warning icon, "End Current Session?" title, body text, Cancel and "End Session" (red) buttons.
- Confirming ends the session via API, clears practice state, returns to deck detail view.
- Canceling dismisses the modal and returns to the chat.

### US-08: Session summary
**As a** learner, **I want** the session summary to display as a full content area view **so that** I can review my results before returning home.

**Acceptance Criteria:**
- After session completion, the practice chat transitions to the session summary view.
- Summary shows: "Session Complete!" header, summary text in sage-tint box, results table, action buttons.
- "Start New Session" begins a new practice session on the same deck.
- "Back to Home" returns to the deck detail view and fires feedback generation.
