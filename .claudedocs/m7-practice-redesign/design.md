# Milestone 7: Practice Session Redesign -- Design Document

> **Source of truth for architecture**: `.claude/architecture.md`
> **Design spec**: `practice-session-redesign-spec.txt` (root of repo)
> This document describes M7-specific technical design decisions and component architecture.

---

## 1. Architecture Overview

### 1.1 Core Change: State-Driven Overlay (No Route)

**Before (M5):** Practice is a React Router route at `/home/deck/:deckId/practice/:sessionId`. HomeLayout renders DeckListPanel + PracticePanel side by side.

**After (M7):** Practice is a `viewState`-driven conditional render inside HomeLayout. No URL change occurs. The URL stays at `/home/deck/:deckId` throughout the entire practice lifecycle.

```
HomeLayout rendering logic:
  viewState === 'home'        → DeckListPanel + Routes (DeckDetailPanel)
  viewState === 'loading'     → LoadingRitual (full content area)
  viewState === 'practicing'  → PracticeChat (full content area)
  viewState === 'summary'     → SessionSummary (full content area)
```

The Layout component (Sidebar + main content area) remains untouched. Practice replaces only the main content inside HomeLayout, so the sidebar stays visible naturally.

### 1.2 Backend Changes (Minor)

All existing practice APIs remain unchanged:
- `POST /api/practice/sessions` (start session)
- `POST /api/practice/sessions/:id/messages` (send message)
- `POST /api/practice/sessions/:id/next-word` (advance word with quality)
- `POST /api/practice/sessions/:id/end` (end session early)
- `GET /api/practice/sessions/:id/summary` (get summary)

The quality rating scale remains 0-5 (SM-2 standard).

**New for M7:** One new endpoint + one new column to support retroactive rating editing:

1. **New column**: `srs_snapshot` (JSON, nullable) on `SessionWord` -- stores the word's SRS state (repetitions, interval_days, ease_factor, next_review_date, is_mastered) **before** the quality rating is applied in `advance_word()`.
2. **New endpoint**: `POST /api/words/:id/rerate` -- accepts `{quality: number, session_id: number}`. Restores the word to its pre-rating SRS state from the snapshot, then applies `update_srs(word, newQuality)`. This gives true undo+redo semantics (no double-counting repetitions).
3. **Modified function**: `advance_word()` in `practice_runner.py` -- saves SRS snapshot to `SessionWord.srs_snapshot` before calling `update_srs()`.

This allows users to edit any past rating during a session without affecting the next-word flow.

### 1.3 Session Persistence via localStorage

To survive page refreshes without URL-based routing:

```typescript
// On session start:
localStorage.setItem('laoshi_active_session', JSON.stringify({
  sessionId: number,
  deckId: number,
  deckName: string,
}))

// On page load (HomeProvider mount):
const saved = localStorage.getItem('laoshi_active_session')
if (saved) → restore viewState to 'practicing', load session from API

// On session end (complete, ended early, or navigated away):
localStorage.removeItem('laoshi_active_session')
```

---

## 2. Component Architecture

### 2.1 Modified Components (edit in place)

| Component | File | Changes |
|-----------|------|---------|
| HomeContext | `pages/home/HomeContext.tsx` | Add `viewState` enum, `activeSessionData`, localStorage persistence. Remove `requestDeckSwitch`, `pendingDeckId` (deck list hidden during practice). |
| HomeLayout | `pages/home/index.tsx` | Conditional rendering based on `viewState`. Remove practice route from Routes. Move EndSessionModal into PracticeChat. |
| DeckDetailPanel | `pages/home/DeckDetailPanel.tsx` | `handleStartPractice` sets context `viewState='loading'` instead of `navigate()`. Passes session data to context. |
| PracticePanel → PracticeChat | `pages/home/PracticePanel.tsx` | Major refactor: new layout, state machine, integrate new sub-components. Rename to PracticeChat internally. |
| SessionSummary | `components/SessionSummary.tsx` | Restyle to match spec. Full content area layout. Accept `onBackToHome` callback. |
| FeedbackCard | `components/FeedbackCard.tsx` | No changes. Continues to render inline below AI messages. |
| Sidebar | `components/Sidebar.tsx` | No changes. Existing white sidebar preserved. |
| Layout | `components/Layout.tsx` | No changes. |

### 2.2 New Components (extracted from PracticePanel)

| Component | File | Purpose |
|-----------|------|---------|
| LoadingRitual | `pages/home/LoadingRitual.tsx` | Animated loading screen between "Start Practice" and chat. |
| FloatingWordPill | `pages/home/FloatingWordPill.tsx` | Sticky collapsed/expanded word display at top of chat. |
| ConfidenceRating | `pages/home/ConfidenceRating.tsx` | 6 inline rating buttons (0-5) attached below Laoshi message. |

### 2.3 Removed Components (deleted from PracticePanel)

| Component | Replaced By |
|-----------|-------------|
| `QualityRatingModal` (function inside PracticePanel) | `ConfidenceRating` (inline buttons) |
| `WordPanel` (function inside PracticePanel) | `FloatingWordPill` (sticky pill) |

### 2.4 Component Tree (during practice)

```
Layout
├── Sidebar (unchanged, 80px white)
└── main content area
    └── Home
        └── HomeProvider
            └── HomeLayout
                └── PracticeChat (viewState === 'practicing')
                    ├── ProgressBar (3px, top)
                    ├── ChatHeader (56px)
                    │   ├── Back chevron → EndSessionModal
                    │   ├── Laoshi avatar + name + online dot
                    │   └── Deck name + word counter
                    ├── ChatArea (scrollable, flex-1)
                    │   ├── FloatingWordPill (sticky top)
                    │   ├── ChatBubble[] (messages)
                    │   ├── TypingIndicator (conditional)
                    │   ├── ConfidenceRating (conditional, inline)
                    │   └── WordDivider (conditional)
                    ├── InputArea (bottom)
                    │   ├── Textarea
                    │   └── ActionBar (Next Word + char count + Submit)
                    └── EndSessionModal (conditional overlay)
```

---

## 3. State Machine

### 3.1 View State (HomeContext level)

```
'home' → [click Start Practice] → 'loading' → [4800ms] → 'practicing' → [session complete or ended] → 'summary' → [click action] → 'home'
```

### 3.2 Practice Status (PracticeChat level)

Replaces the boolean flags (`submitting`, `awaitingNextWord`, `showQualityModal`) with a single `status` enum:

```typescript
type PracticeStatus =
  | 'ai_typing'         // Laoshi is generating response (typing indicator shown)
  | 'waiting_for_user'  // User can type and submit a sentence
  | 'feedback_given'    // Feedback received, "Next Word" enabled in action bar
  | 'rating_typing'     // Laoshi "typing" before showing rating prompt (800ms)
  | 'awaiting_rating'   // Rating buttons visible, input locked
  | 'rating_selected'   // User selected rating, buttons collapsing
  | 'transitioning'     // Word divider shown, transitioning to next word
  | 'session_complete'  // "View Session Summary" button shown
```

### 3.3 Full Flow

```
[Session loads]
  → status: 'ai_typing' (first word greeting)
  → AI response arrives
  → status: 'waiting_for_user'

[User submits sentence]
  → status: 'ai_typing' (typing indicator)
  → AI response + feedback arrives
  → status: 'feedback_given' (Next Word button enabled)

[User clicks "Next Word"]
  → status: 'rating_typing' (typing indicator, 800ms delay)
  → Laoshi message: "Before we move on..."
  → status: 'awaiting_rating' (6 buttons visible, input locked)

[User clicks rating button]
  → status: 'rating_selected' (buttons collapse, color-coded pill + edit icon appears)
  → API call: practiceApi.nextWord(sessionId, quality) fires immediately
  → 500ms delay

[If NOT last word]
  → Word divider appears
  → status: 'transitioning' (600ms)
  → Next word loads, pill transitions
  → status: 'ai_typing' (new word greeting)
  → ...loop

[If LAST word]
  → status: 'ai_typing' (800ms, typing indicator)
  → Laoshi wrap-up message
  → status: 'session_complete'
  → Input area shows "View Session Summary" button
  → [click] → viewState: 'summary'

[User edits a PAST rating (at any point)]
  → User scrolls to old rating, clicks edit icon
  → Buttons reopen under that specific message (local component state)
  → User clicks new rating
  → Buttons collapse, pill updates with new color + label
  → API call: practiceApi.rerateWord(wordId, sessionId, newQuality) fires independently
  → Backend restores SRS snapshot → applies new quality (true undo+redo)
  → No effect on current word or practice flow
```

---

## 4. Component Details

### 4.1 LoadingRitual

Small self-contained component (~60 lines).

```typescript
interface LoadingRitualProps {
  onReady: () => void  // Called after all messages cycle
}
```

- Container fills content area (`h-full flex flex-col items-center justify-center`)
- Background: `warm-offwhite`
- Laoshi logo: 128px container, `rounded-2xl`, `shadow-lg`, white bg, logo at 96px
- Logo animation: CSS scale pulse (1.0 ↔ 1.05, 2s infinite ease-in-out)
- Messages: Array of 4 strings, cycle every 1200ms via `setInterval`
- Each message fades in/out via CSS transition or framer-motion
- After `4 * 1200ms = 4800ms`, call `onReady()`
- Cleanup: clear interval on unmount

### 4.2 FloatingWordPill

Moderately complex component (~150 lines). Uses framer-motion for layout animations.

```typescript
interface FloatingWordPillProps {
  word: WordContext
  notes?: string | null
  isTransitioning?: boolean  // True during word change animation
}
```

**Collapsed state (default):**
- Pill shape (`rounded-full`), white bg, `warm-gray/60` border
- Content row: character (20px serif) + pinyin (14px) + "—" + meaning (14px, truncated 240px) + chevron-down
- Click to expand

**Expanded state:**
- `rounded-2xl`, max-width 672px, white bg, 24px padding
- Left column: character (48px serif), pinyin (14px sage)
- Right column: meaning (16px), user note block (conditional)
- Collapse button (chevron-up) top-right
- Click outside to collapse (document mousedown listener)

**Animations:**
- Expand/collapse: `framer-motion` `layout` prop, 280ms cubic-bezier
- Word change: `AnimatePresence` with slide-out-left / slide-in-right

### 4.3 ConfidenceRating

Inline rating component (~180 lines). Renders as part of the chat message flow. Supports retroactive editing of past ratings.

```typescript
interface ConfidenceRatingProps {
  messageId: string        // Chat message ID (for identifying which rating to update)
  wordId: number           // Word ID (for rerate API call on past ratings)
  wordText: string         // Chinese character for display
  sessionId: number        // Session ID (for rerate API call)
  quality?: number         // Current selected rating (undefined = not yet rated)
  isLatest: boolean        // Is this the currently active rating prompt?
  onRate: (messageId: string, wordId: number, quality: number, isEdit: boolean) => void
}
```

**Structure:**
- Renders as a Laoshi message (avatar + bubble)
- Message text: "Before we move on, how confident are you using **{word}**?"
- Bubble has modified bottom corners when buttons visible (bottom-left 4px, bottom-right 16px)
- Button row directly below bubble (no gap), shared borders, `rounded-b-2xl`
- 6 buttons, each `flex-1`, min-height 56px: number (18px bold) + label (10px)
- Labels: 0="Blackout", 1="Wrong", 2="Hard", 3="OK", 4="Good", 5="Easy"
- Hover: `warm-offwhite/80` background
- On click: highlight (150ms), fire `onRate`, buttons animate out (height 0, opacity 0)

**After selection (rated state):**
- Buttons collapse. A **color-coded pill** appears inline in the message: "4 -- Good"
- **3-tier color coding:**
  - Ratings 0-2 (Blackout/Wrong/Hard): `bg-coral/15 text-coral` (struggling)
  - Rating 3 (OK): `bg-amber/15 text-amber` (okay)
  - Ratings 4-5 (Good/Easy): `bg-sage/15 text-sage` (confident)
- Small **pencil/edit icon** (14px, `warm-black/30`) appears to the right of the pill
- Clicking edit reopens the rating buttons below the message
- Selecting a new rating: buttons collapse, pill updates with new color + label

**Edit flow for past ratings:**
- When `isLatest === false` and user clicks edit: buttons reopen, but the `onRate` callback passes `isEdit: true`
- PracticeChat distinguishes: `isEdit: true` → call `practiceApi.rerateWord()`, `isEdit: false` → call `practiceApi.nextWord()`
- The next word flow is completely independent of retroactive edits

### 4.4 PracticeChat (Refactored PracticePanel)

The largest component (~400 lines). Keeps existing API call logic, replaces UI shell.

**Chat message model (updated for rating tracking):**

```typescript
interface ChatMessage {
  id: string
  role: 'laoshi' | 'user'
  content: string
  feedback?: FeedbackData | null
  ratingData?: {           // Present on rating prompt messages
    wordId: number         // For rerate API
    wordText: string       // Display in prompt
    quality?: number       // Current rating (undefined = not yet rated)
  }
}
```

Messages with `ratingData` render as `ConfidenceRating` components instead of normal bubbles. The `quality` field is mutable -- updated in place when the user rates or re-rates.

**Reused logic from current PracticePanel (no changes needed):**
- `loadSession()` -- fetch session from API
- `addMessage()` -- append to messages array
- `handleSubmit()` -- send sentence to API
- `handleEndSession()` -- end session via API

**Changed logic:**
- `handleNextWord()` -- no longer opens modal. Sets `status='rating_typing'`, waits 800ms, adds Laoshi prompt message, sets `status='awaiting_rating'`.
- `handleQualityRate()` -- sets `status='rating_selected'`, calls API, waits 500ms, then transitions or completes.
- State management: single `status` string replaces multiple booleans.

**New UI elements:**
- Progress bar (3px div at top)
- Chat header with centered content (max-width 48rem)
- Updated ChatBubble (user: sage bg + white text, AI: white + border + avatar)
- FloatingWordPill inside scrollable area
- ConfidenceRating inline in chat
- Word divider between words
- Compound input area
- Locked input state during rating
- "View Session Summary" button when complete

### 4.5 EndSessionModal (moved into PracticeChat)

Currently in `home/index.tsx`, moved into PracticeChat since it's only relevant during practice.

**Styling updates:**
- Backdrop: `warm-black/20`, `backdrop-blur-sm`
- Card: max-width 448px, `rounded-2xl`, `shadow-xl`, 32px padding
- Yellow warning circle: 48px, `yellow-100` bg, AlertTriangle icon (24px, `yellow-600`)
- Cancel: text button, `warm-black/60`
- End Session: `#EF4444` bg, hover `#DC2626`, white text, `rounded-xl`

### 4.6 SessionSummary (restyled)

**Changes from current:**
- Container: fills content area (`h-full overflow-y-auto bg-warm-offwhite`)
- Content: max-width 896px, centered, `py-16 px-6`
- Header: "Session Complete!" in serif font (30px)
- Summary box: `sage-tint` bg, `sage/15` border, 16px rounded, 32px padding, italic text
- Table: white bg, `warm-gray` border, `rounded-2xl`, `shadow-sm`
  - Header row: 11px uppercase bold, `warm-black/40`
  - Status pills: sage-tint/sage for correct, coral/10/coral for needs work
- Action buttons: "Start New Session" (sage bg) + "Back to Home" (white bg, warm-gray border)

---

## 5. Tailwind / CSS Changes

### 5.1 New Tailwind Color Token

Add to `tailwind.config.js` under `extend.colors`:
```javascript
chat: {
  bg: '#F5F3EE',
}
```

### 5.2 New CSS Animations

Add to `frontend/src/index.css`:
```css
@keyframes pulse-scale {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.animate-pulse-scale {
  animation: pulse-scale 2s ease-in-out infinite;
}
```

---

## 6. File Impact Summary

### Files Modified
| File | Scope of Change |
|------|----------------|
| `tailwind.config.js` | Add `chat.bg` color token |
| `frontend/src/index.css` | Add pulse-scale animation |
| `frontend/src/pages/home/HomeContext.tsx` | Add viewState, activeSessionData, localStorage persistence |
| `frontend/src/pages/home/index.tsx` | Conditional rendering by viewState, remove practice route, remove EndSessionModal |
| `frontend/src/pages/home/DeckDetailPanel.tsx` | handleStartPractice triggers viewState change |
| `frontend/src/pages/home/PracticePanel.tsx` | Major refactor: new layout, state machine, sub-components |
| `frontend/src/components/SessionSummary.tsx` | Restyle to match spec |

### Files Created
| File | Purpose |
|------|---------|
| `frontend/src/pages/home/LoadingRitual.tsx` | Animated loading screen |
| `frontend/src/pages/home/FloatingWordPill.tsx` | Sticky word pill (collapsed/expanded) |
| `frontend/src/pages/home/ConfidenceRating.tsx` | Inline rating buttons |

### Backend Files Modified
| File | Scope of Change |
|------|----------------|
| `backend/models.py` | Add `srs_snapshot` JSON column to SessionWord |
| `backend/practice_runner.py` | Save SRS snapshot in `advance_word()` before calling `update_srs()` |
| `backend/resources.py` | Add `RerateWordResource` for `POST /api/words/:id/rerate` |
| `backend/app.py` | Register the new rerate endpoint |

### Frontend Files Also Modified
| File | Scope of Change |
|------|----------------|
| `frontend/src/lib/api.ts` | Add `rerateWord()` to `practiceApi` |

### Files NOT Changed
| File | Reason |
|------|--------|
| `frontend/src/components/Sidebar.tsx` | Keep existing white sidebar as-is |
| `frontend/src/components/Layout.tsx` | No changes needed |
| `frontend/src/components/FeedbackCard.tsx` | Keep inline below AI messages |
| `frontend/src/types/api.ts` | Types unchanged |
| `frontend/src/App.tsx` | No routing changes |

---

## 7. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Practice URL | No URL change (state-driven) | User explicitly requested hiding IDs. State-driven overlay keeps URL clean. |
| Session persistence | localStorage | Survives refresh without URL routing. Simple key-value storage. |
| Rating scale | Keep 0-5 (6 buttons) | Matches SM-2 backend. No backend changes needed. |
| Sidebar during practice | Keep existing white sidebar | User explicitly requested no sidebar changes. |
| FeedbackCard | Keep inline (no changes) | User explicitly requested keeping it as-is. |
| Sidebar navigation during practice | Allow (no blocking) | Sidebar links navigate normally. Session persists in localStorage for resume. EndSessionModal only triggered by back chevron in chat header. |
| Rating edit approach | True undo+redo via SRS snapshot | `SessionWord.srs_snapshot` stores pre-rating SRS state. On rerate, restore snapshot then apply new quality. No double-counting repetitions. |
| Rating color coding | 3-tier | 0-2 coral (struggling), 3 amber (okay), 4-5 sage (confident). Clean and readable. |
| Rating editing scope | Any past word in session | Users can scroll back and edit any previous rating at any time during the session. Edit calls independent rerate API, does not affect next-word flow. |
