# Milestone 7: Practice Session Redesign -- Task Breakdown

## Task Overview

**Total tasks**: 28 tasks (7.1-7.28) across 8 phases
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be parallelised where noted.
**Small backend addition**: One new column + one new endpoint to support retroactive rating editing.

---

## Prerequisites

Before starting any tasks:

1. Ensure Milestones 5 and 6 are complete and all tests pass.
2. Ensure `npm install` has been run in the project root.
3. Ensure the dev server starts without errors: `npm run dev`.
4. Read the design spec: `practice-session-redesign-spec.txt` (repo root).
5. Read the design document: `.claudedocs/m7-practice-redesign/design.md`.

---

## Phase 1: Tailwind & CSS Foundation

Small config changes. No component changes yet.

---

### T-7.1: Add chat background color token to Tailwind config

**Description**: Add the `#F5F3EE` chat background color to Tailwind so components can use `bg-chat-bg`.

**Files affected**:
- `tailwind.config.js` -- add color token under `extend.colors`

**Changes**:

In the `extend.colors` object, add:
```javascript
chat: {
  bg: '#F5F3EE',
},
```

Also add to the `safelist` array:
```javascript
'bg-chat-bg',
```

**Acceptance criteria**:
- `bg-chat-bg` produces `background-color: #F5F3EE` in compiled CSS.
- Existing color tokens unchanged.
- Dev server starts without errors.

**Dependencies**: None.

---

### T-7.2: Add CSS animation keyframes

**Description**: Add the pulse-scale animation for the loading ritual logo.

**Files affected**:
- `frontend/src/index.css` -- add keyframe and utility class

**Changes**:

Add at the end of the file (after the existing `@layer components` block):
```css
@keyframes pulse-scale {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.animate-pulse-scale {
  animation: pulse-scale 2s ease-in-out infinite;
}
```

**Acceptance criteria**:
- `.animate-pulse-scale` class is available and produces a gentle scale oscillation.
- Existing styles unchanged.

**Dependencies**: None. Can be done in parallel with T-7.1.

---

## Phase 1B: Backend -- SRS Snapshot + Rerate Endpoint

Small backend addition to support retroactive rating editing. Can be done in parallel with Phase 1.

---

### T-7.25: Add srs_snapshot column to SessionWord model

**Description**: Add a JSON column to SessionWord that stores the word's SRS state before a quality rating is applied. This enables true undo+redo when the user edits a past rating.

**Files affected**:
- `backend/models.py` -- add column to `SessionWord` class

**Changes**:

Add to `SessionWord` class (after `status` column):
```python
srs_snapshot = db.Column(db.JSON, nullable=True)  # Pre-rating SRS state for undo+redo
```

Also add to `format_data()` return dict:
```python
'srs_snapshot': self.srs_snapshot,
```

**Acceptance criteria**:
- `SessionWord` model has `srs_snapshot` JSON column.
- Column is nullable (null for words not yet rated).
- Existing tests pass.

**Dependencies**: None.

---

### T-7.26: Run Alembic migration for srs_snapshot column

**Description**: Generate and run migration for the new column.

**Steps**:
1. `flask db migrate -m "add_srs_snapshot_to_session_word"`
2. Review generated migration file.
3. `flask db upgrade`

**Acceptance criteria**:
- Migration runs without errors.
- `session_word` table has `srs_snapshot` column.
- Existing data is unaffected.

**Dependencies**: T-7.25.

---

### T-7.27: Save SRS snapshot in advance_word before applying rating

**Description**: Modify `advance_word()` in `practice_runner.py` to save the word's SRS state to `SessionWord.srs_snapshot` before calling `update_srs()`.

**Files affected**:
- `backend/practice_runner.py` -- modify `advance_word()` function

**Changes**:

In `advance_word()`, after `word = Word.get_by_id(current_sw.word_id)` and before the `if quality is not None:` block, add:

```python
        # Save SRS snapshot before rating (for undo+redo on retroactive edits)
        if quality is not None:
            current_sw.srs_snapshot = {
                'repetitions': word.repetitions,
                'interval_days': word.interval_days,
                'ease_factor': float(word.ease_factor),
                'next_review_date': str(word.next_review_date) if word.next_review_date else None,
                'is_mastered': word.is_mastered,
                'last_quality': word.last_quality,
            }
            current_sw.update()
```

This snapshot is saved BEFORE `update_srs(word, quality)` runs, so it captures the pre-rating state.

**Acceptance criteria**:
- After `advance_word()` is called with a quality rating, the corresponding `SessionWord.srs_snapshot` contains the word's pre-rating SRS state.
- The snapshot has keys: repetitions, interval_days, ease_factor, next_review_date, is_mastered, last_quality.
- Existing `advance_word` behavior unchanged (SRS still updates, next word still loads).

**Dependencies**: T-7.25.

---

### T-7.28: Create POST /api/words/:id/rerate endpoint

**Description**: New endpoint that restores a word to its pre-rating SRS state (from snapshot) and applies a new quality rating. This enables retroactive rating editing.

**Files affected**:
- `backend/resources.py` -- add `RerateWordResource` class
- `backend/app.py` -- register the new endpoint

**Changes**:

In `resources.py`, add:

```python
class RerateWordResource(Resource):
    @jwt_required()
    def post(self, id):
        """Rerate a word by restoring SRS snapshot and applying new quality."""
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        quality = data.get('quality')
        session_id = data.get('session_id')

        if quality is None or session_id is None:
            return {'error': 'quality and session_id are required'}, 400
        if not isinstance(quality, int) or quality < 0 or quality > 5:
            return {'error': 'quality must be an integer between 0 and 5'}, 400

        # Verify word belongs to user
        word = Word.get_by_id(id)
        if not word or word.user_id != user_id:
            return {'error': 'Word not found'}, 404

        # Get the session word to find the snapshot
        session_word = SessionWord.get_by_session_word_id(id, session_id)
        if not session_word:
            return {'error': 'Session word not found'}, 404

        if not session_word.srs_snapshot:
            return {'error': 'No SRS snapshot available for this word'}, 400

        # Restore SRS state from snapshot
        snapshot = session_word.srs_snapshot
        word.repetitions = snapshot['repetitions']
        word.interval_days = snapshot['interval_days']
        word.ease_factor = snapshot['ease_factor']
        word.next_review_date = (
            date.fromisoformat(snapshot['next_review_date'])
            if snapshot['next_review_date'] else None
        )
        word.is_mastered = snapshot['is_mastered']
        word.last_quality = snapshot['last_quality']

        # Apply new quality rating
        word.last_quality = quality
        word.update_srs(quality)
        word.update_mastery_status()
        word.update()

        # Update the snapshot to reflect this new rating's pre-state
        # (in case user edits again, we want to restore to the ORIGINAL pre-rating state)
        # Note: we keep the original snapshot, not overwrite it.
        # This ensures multiple edits always restore to the same baseline.

        return {'word': word.format_data(viewer=User.get_by_id(user_id))}, 200
```

Add import at top of `resources.py`:
```python
from datetime import date
from models import SessionWord
```

In `app.py`, register:
```python
api.add_resource(RerateWordResource, '/api/words/<int:id>/rerate')
```

**Acceptance criteria**:
- `POST /api/words/:id/rerate` with `{quality: 3, session_id: 42}` restores the word's SRS state from the snapshot, then applies the new quality.
- Repetition count is correct (not double-counted).
- Returns the updated word data.
- Returns 400 if no snapshot available.
- Returns 404 if word doesn't belong to user.
- Endpoint requires JWT auth.

**Dependencies**: T-7.25, T-7.27.

---

## Phase 2: HomeContext Refactor

Update the state management to support view-state-driven rendering and localStorage persistence. This is the foundation for all subsequent phases.

---

### T-7.3: Refactor HomeContext with viewState and localStorage

**Description**: Replace URL-based practice routing with a `viewState` enum. Add localStorage persistence for active sessions. Remove deck-switch-during-practice logic (deck list is hidden during practice).

**Files affected**:
- `frontend/src/pages/home/HomeContext.tsx` -- rewrite

**Changes**:

Replace the current HomeContext with:

```typescript
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { WordContext, PracticeSummaryResponse } from '../../types/api'

export type ViewState = 'home' | 'loading' | 'practicing' | 'summary'

interface ActiveSessionData {
  sessionId: number
  deckId: number
  deckName: string
  greeting?: string
  currentWord?: WordContext
}

interface HomeContextValue {
  selectedDeckId: number | null
  viewState: ViewState
  activeSessionData: ActiveSessionData | null
  summaryData: PracticeSummaryResponse | null
  selectDeck: (deckId: number) => void
  startPractice: (data: ActiveSessionData) => void
  onLoadingComplete: () => void
  endPractice: () => void
  showSummary: (summary: PracticeSummaryResponse) => void
  backToHome: () => void
}

const STORAGE_KEY = 'laoshi_active_session'

function saveSession(data: ActiveSessionData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    sessionId: data.sessionId,
    deckId: data.deckId,
    deckName: data.deckName,
  }))
}

function loadSession(): ActiveSessionData | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return null
    return JSON.parse(saved)
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEY)
}

const HomeContext = createContext<HomeContextValue | undefined>(undefined)

export function HomeProvider({ children }: { children: React.ReactNode }) {
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)
  const [viewState, setViewState] = useState<ViewState>('home')
  const [activeSessionData, setActiveSessionData] = useState<ActiveSessionData | null>(null)
  const [summaryData, setSummaryData] = useState<PracticeSummaryResponse | null>(null)

  // Restore active session from localStorage on mount
  useEffect(() => {
    const saved = loadSession()
    if (saved) {
      setActiveSessionData(saved)
      setSelectedDeckId(saved.deckId)
      setViewState('practicing')
    }
  }, [])

  const selectDeck = useCallback((deckId: number) => {
    setSelectedDeckId(deckId)
  }, [])

  const startPractice = useCallback((data: ActiveSessionData) => {
    setActiveSessionData(data)
    setSelectedDeckId(data.deckId)
    saveSession(data)
    setViewState('loading')
  }, [])

  const onLoadingComplete = useCallback(() => {
    setViewState('practicing')
  }, [])

  const endPractice = useCallback(() => {
    setActiveSessionData(null)
    setSummaryData(null)
    clearSession()
    setViewState('home')
  }, [])

  const showSummary = useCallback((summary: PracticeSummaryResponse) => {
    setSummaryData(summary)
    clearSession()
    setViewState('summary')
  }, [])

  const backToHome = useCallback(() => {
    setActiveSessionData(null)
    setSummaryData(null)
    setViewState('home')
  }, [])

  return (
    <HomeContext.Provider
      value={{
        selectedDeckId,
        viewState,
        activeSessionData,
        summaryData,
        selectDeck,
        startPractice,
        onLoadingComplete,
        endPractice,
        showSummary,
        backToHome,
      }}
    >
      {children}
    </HomeContext.Provider>
  )
}

export function useHome() {
  const context = useContext(HomeContext)
  if (context === undefined) {
    throw new Error('useHome must be used within a HomeProvider')
  }
  return context
}
```

**Key changes from current:**
- `viewState` enum replaces URL-based practice detection.
- `activeSessionData` holds session info (replaces `activePracticeSessionId`).
- `startPractice` accepts full session data and saves to localStorage.
- `onLoadingComplete` transitions loading → practicing.
- `showSummary` accepts summary data and transitions to summary view.
- `backToHome` clears everything and returns to home.
- `endPractice` clears everything (used when ending early via modal).
- **Removed**: `requestDeckSwitch`, `pendingDeckId`, `showEndSessionModal`, `confirmEndSession`, `cancelEndSession` -- deck list isn't visible during practice, so mid-session deck switching doesn't apply.
- **Added**: localStorage save/load/clear for session persistence.

**Acceptance criteria**:
- `useHome()` returns `viewState`, `activeSessionData`, `summaryData` and all action functions.
- On mount, if localStorage has a saved session, `viewState` is `'practicing'` and `activeSessionData` is populated.
- `startPractice()` saves to localStorage and sets viewState to `'loading'`.
- `endPractice()` clears localStorage and sets viewState to `'home'`.
- No TypeScript errors.

**Dependencies**: None.

---

## Phase 3: New Sub-Components

Three new standalone components. Can be built in parallel.

---

### T-7.4: Create LoadingRitual component

**Description**: Animated loading screen shown between clicking "Start Practice" and entering the chat.

**Files affected**:
- Create: `frontend/src/pages/home/LoadingRitual.tsx`

**Full implementation**:

```tsx
import { useEffect, useState, useRef } from 'react'
import laoshiLogo from '../../assets/laoshi-logo.png'

const MESSAGES = [
  'Digging up the scrolls...',
  'Preparing the tea...',
  'Lighting the candles...',
  'Setting the mood...',
]

const MESSAGE_DURATION = 1200

interface LoadingRitualProps {
  onReady: () => void
}

export default function LoadingRitual({ onReady }: LoadingRitualProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const [visible, setVisible] = useState(true)
  const onReadyRef = useRef(onReady)
  onReadyRef.current = onReady

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex(prev => {
        const next = prev + 1
        if (next >= MESSAGES.length) {
          clearInterval(interval)
          // Small delay before calling onReady for the exit fade
          setTimeout(() => {
            setVisible(false)
            setTimeout(() => onReadyRef.current(), 300)
          }, MESSAGE_DURATION)
          return prev
        }
        return next
      })
    }, MESSAGE_DURATION)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      className={`h-full flex flex-col items-center justify-center bg-warm-offwhite transition-opacity duration-300 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {/* Pulsing Laoshi logo */}
      <div className="w-32 h-32 rounded-2xl shadow-lg bg-white flex items-center justify-center mb-8 animate-pulse-scale">
        <img src={laoshiLogo} alt="Laoshi" className="w-24 h-24 object-contain" />
      </div>

      {/* Rotating message */}
      <div className="h-8 flex items-center justify-center">
        <p
          key={messageIndex}
          className="font-serif text-lg text-warm-black/60 animate-fade-in"
        >
          {MESSAGES[messageIndex]}
        </p>
      </div>
    </div>
  )
}
```

Also add to `frontend/src/index.css`:
```css
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in-up 300ms ease-out;
}
```

**Acceptance criteria**:
- Component renders with pulsing logo and first message.
- Messages rotate every 1200ms.
- After all 4 messages, screen fades out and `onReady` is called.
- Component cleans up interval on unmount.

**Dependencies**: T-7.2 (CSS animations).

---

### T-7.5: Create FloatingWordPill component

**Description**: Sticky word pill with collapsed (default) and expanded states. Uses framer-motion for layout animations.

**Files affected**:
- Create: `frontend/src/pages/home/FloatingWordPill.tsx`

**Full implementation**:

```tsx
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { WordContext } from '../../types/api'

interface FloatingWordPillProps {
  word: WordContext
  notes?: string | null
}

export default function FloatingWordPill({ word, notes }: FloatingWordPillProps) {
  const [expanded, setExpanded] = useState(false)
  const pillRef = useRef<HTMLDivElement>(null)

  // Click outside to collapse
  useEffect(() => {
    if (!expanded) return

    const handleClickOutside = (e: MouseEvent) => {
      if (pillRef.current && !pillRef.current.contains(e.target as Node)) {
        setExpanded(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [expanded])

  return (
    <div className="sticky top-0 z-10 flex justify-center px-6 pt-3 pb-2"
      style={{
        background: 'linear-gradient(to bottom, rgba(245,243,238,0.95) 60%, transparent)',
      }}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={word.word_id}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        >
          <motion.div
            ref={pillRef}
            layout
            transition={{ duration: 0.28, ease: [0.25, 0.1, 0.25, 1] }}
            className={`bg-white border border-warm-gray/60 ${
              expanded ? 'rounded-2xl max-w-[42rem] w-full' : 'rounded-full cursor-pointer hover:border-warm-gray'
            }`}
            onClick={() => !expanded && setExpanded(true)}
          >
            {expanded ? (
              /* Expanded state */
              <div className="p-6">
                <div className="flex gap-8">
                  {/* Left column */}
                  <div className="flex-shrink-0 min-w-[100px] flex flex-col justify-center">
                    <span className="text-5xl font-serif text-warm-black leading-none mb-2">
                      {word.word}
                    </span>
                    <span className="text-sm font-medium text-sage">
                      {word.pinyin}
                    </span>
                  </div>

                  {/* Right column */}
                  <div className="flex-1 min-w-0">
                    <p className="text-base text-warm-black/80 leading-relaxed mb-4">
                      {word.meaning}
                    </p>

                    {notes && (
                      <div className="bg-warm-offwhite rounded-lg p-3 mb-3">
                        <p className="text-xs text-warm-black/40 mb-1">Your note</p>
                        <p className="text-sm text-warm-black/70">{notes}</p>
                      </div>
                    )}
                  </div>

                  {/* Collapse button */}
                  <button
                    onClick={(e) => { e.stopPropagation(); setExpanded(false) }}
                    className="self-start p-1.5 text-warm-black/30 hover:text-warm-black/60 transition-colors"
                  >
                    <ChevronUp className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              /* Collapsed state */
              <div className="flex items-center gap-3 px-5 py-2">
                <span className="text-xl font-serif font-medium text-warm-black">
                  {word.word}
                </span>
                <span className="text-sm text-warm-black/40">
                  {word.pinyin}
                </span>
                <span className="text-warm-black/20">&mdash;</span>
                <span className="text-sm text-warm-black/50 truncate max-w-[240px]">
                  {word.meaning}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-warm-black/25 flex-shrink-0" />
              </div>
            )}
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
```

**Acceptance criteria**:
- Pill renders in collapsed state by default showing character, pinyin, meaning.
- Clicking expands to show full details.
- Clicking outside collapses.
- When `word` prop changes (new word_id), content slides out left and new word slides in right.
- No TypeScript errors.

**Dependencies**: None. Can be done in parallel with T-7.4 and T-7.6.

---

### T-7.6: Create ConfidenceRating component

**Description**: Inline rating buttons (0-5) that render as a Laoshi message with attached button row. Supports retroactive editing with color-coded pills and edit icon.

**Files affected**:
- Create: `frontend/src/pages/home/ConfidenceRating.tsx`

**Full implementation**:

```tsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Pencil } from 'lucide-react'
import laoshiLogo from '../../assets/laoshi-logo.png'

const RATINGS = [
  { value: 0, label: 'Blackout' },
  { value: 1, label: 'Wrong' },
  { value: 2, label: 'Hard' },
  { value: 3, label: 'OK' },
  { value: 4, label: 'Good' },
  { value: 5, label: 'Easy' },
]

/** 3-tier color coding: 0-2 coral, 3 amber, 4-5 sage */
function getRatingColor(quality: number): { bg: string; text: string } {
  if (quality <= 2) return { bg: 'bg-coral/15', text: 'text-coral' }
  if (quality === 3) return { bg: 'bg-amber/15', text: 'text-amber' }
  return { bg: 'bg-sage/15', text: 'text-sage' }
}

interface ConfidenceRatingProps {
  messageId: string          // Chat message ID
  wordId: number             // For rerate API call
  wordText: string           // Chinese character for display
  quality?: number           // Current selected rating (undefined = not yet rated)
  isLatest: boolean          // Is this the currently active rating prompt?
  onRate: (messageId: string, wordId: number, quality: number, isEdit: boolean) => void
}

export default function ConfidenceRating({
  messageId, wordId, wordText, quality, isLatest, onRate,
}: ConfidenceRatingProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [highlightedValue, setHighlightedValue] = useState<number | null>(null)

  const showButtons = (quality === undefined && isLatest) || isEditing
  const selectedLabel = quality !== undefined
    ? RATINGS.find(r => r.value === quality)?.label
    : null

  const handleClick = (value: number) => {
    setHighlightedValue(value)
    setTimeout(() => {
      const isEdit = !isLatest || quality !== undefined
      onRate(messageId, wordId, value, isEdit)
      setIsEditing(false)
      setHighlightedValue(null)
    }, 150)
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const colors = quality !== undefined ? getRatingColor(quality) : null

  return (
    <div className="flex gap-3 mb-4">
      {/* Laoshi avatar */}
      <img
        src={laoshiLogo}
        alt="Laoshi"
        className="w-7 h-7 rounded-full flex-shrink-0 self-end mb-5"
      />

      <div className="max-w-[75%]">
        {/* Message bubble */}
        <div
          className={`bg-white border border-warm-gray/40 shadow-sm px-4 py-3 ${
            showButtons
              ? 'rounded-2xl rounded-tl-sm rounded-b-[4px]'
              : 'rounded-2xl rounded-tl-sm'
          }`}
        >
          <p className="text-[15px] text-warm-black leading-relaxed">
            Before we move on &mdash; how confident are you using{' '}
            <span className="font-serif font-medium">{wordText}</span>?
          </p>

          {/* Color-coded rating pill + edit icon (shown after rating) */}
          {quality !== undefined && !isEditing && colors && (
            <div className="flex items-center gap-2 mt-2">
              <motion.span
                key={quality}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.2, delay: 0.05 }}
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
              >
                {quality} &mdash; {selectedLabel}
              </motion.span>
              <button
                onClick={handleEdit}
                className="text-warm-black/30 hover:text-warm-black/50 transition-colors"
                title="Edit rating"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Rating button row */}
        <AnimatePresence>
          {showButtons && (
            <motion.div
              initial={{ opacity: isEditing ? 0 : 1, height: isEditing ? 0 : 'auto' }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="flex border border-t-0 border-warm-gray/40 rounded-b-2xl bg-white shadow-sm">
                {RATINGS.map((rating, idx) => (
                  <button
                    key={rating.value}
                    onClick={() => handleClick(rating.value)}
                    className={`flex-1 flex flex-col items-center justify-center py-3 min-h-[56px] transition-colors ${
                      idx < RATINGS.length - 1 ? 'border-r border-warm-gray/30' : ''
                    } ${
                      highlightedValue === rating.value
                        ? 'bg-sage/15'
                        : quality === rating.value
                          ? 'bg-warm-offwhite'
                          : 'hover:bg-warm-offwhite/80'
                    }`}
                  >
                    <span className="text-lg font-medium text-warm-black">
                      {rating.value}
                    </span>
                    <span className="text-[10px] font-medium text-warm-black/40">
                      {rating.label}
                    </span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Timestamp */}
        <p className="text-[10px] text-warm-black/30 mt-1">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
```

**Acceptance criteria**:
- **First rating**: When `quality === undefined` and `isLatest`: 6 buttons shown. Clicking a button collapses them, shows a color-coded pill + edit icon.
- **Color coding**: 0-2 coral, 3 amber, 4-5 sage.
- **Edit icon**: Small pencil icon next to the pill. Clicking it reopens the buttons.
- **Re-rating**: Clicking a new button collapses buttons, updates the pill with new color + label.
- **Past ratings**: `isLatest === false` — buttons hidden, pill shown, edit icon available.
- **onRate callback**: Passes `isEdit: true` when editing (for rerate API) vs `isEdit: false` when first-time rating (for nextWord API).
- No TypeScript errors.

**Dependencies**: None. Can be done in parallel with T-7.4 and T-7.5.

---

## Phase 4: PracticeChat Refactor

The largest phase. Refactors PracticePanel.tsx with the new state machine, layout, and sub-components.

---

### T-7.7: Add PracticeStatus type and replace boolean state flags

**Description**: Replace `submitting`, `awaitingNextWord`, `showQualityModal` booleans with a single `status` enum in PracticePanel.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- refactor state management

**Changes**:

1. Add the type at the top of the file:
```typescript
type PracticeStatus =
  | 'ai_typing'
  | 'waiting_for_user'
  | 'feedback_given'
  | 'rating_typing'
  | 'awaiting_rating'
  | 'rating_selected'
  | 'transitioning'
  | 'session_complete'
```

2. Replace the state declarations:
```typescript
// REMOVE these:
const [submitting, setSubmitting] = useState(false)
const [awaitingNextWord, setAwaitingNextWord] = useState(false)
const [showQualityModal, setShowQualityModal] = useState(false)
const [showSummary, setShowSummary] = useState(false)

// REPLACE with:
const [status, setStatus] = useState<PracticeStatus>('ai_typing')
```

3. Update `handleSubmit`:
- Replace `setSubmitting(true)` with `setStatus('ai_typing')`
- Replace `setAwaitingNextWord(true)` with `setStatus('feedback_given')`
- Replace `setSubmitting(false)` in finally block -- set `setStatus('waiting_for_user')` only on error, status is already set on success

4. Update `handleNextWord` (no longer opens modal):
```typescript
const handleNextWord = () => {
  setStatus('rating_typing')
  // Add the Laoshi rating prompt message after 800ms delay
  setTimeout(() => {
    setStatus('awaiting_rating')
  }, 800)
}
```

5. Update `handleQualityRate`:
```typescript
const handleQualityRate = async (quality: number) => {
  setStatus('rating_selected')
  if (!session) return

  try {
    const response = await practiceApi.nextWord(session.id, quality)
    const data = response.data

    setSessionStats({
      words_practiced: data.words_practiced,
      words_total: data.words_total,
    })

    if (data.session_complete) {
      if (data.summary) {
        showSummaryFn(data.summary)
      } else {
        const summaryResponse = await practiceApi.getSummary(session.id)
        showSummaryFn(summaryResponse.data)
      }
    } else {
      // Delay before transitioning to next word
      setTimeout(() => {
        setStatus('transitioning')
        setTimeout(() => {
          if (data.current_word) {
            setCurrentWord(data.current_word)
          }
          if (data.laoshi_response) {
            addMessage('laoshi', data.laoshi_response)
          }
          setStatus('waiting_for_user')
          setUserInput('')
        }, 600)
      }, 500)
    }
  } catch (error) {
    console.error('Failed to get next word:', error)
    setStatus('feedback_given') // Allow retry
  }
}
```

6. Update all conditional checks:
- `submitting` → `status === 'ai_typing'`
- `awaitingNextWord` → `status === 'feedback_given'`
- `showQualityModal` → removed (inline rating uses `status === 'awaiting_rating'`)
- `showSummary` → removed (viewState handles this now)

**Acceptance criteria**:
- All boolean flags removed. Single `status` state drives the UI.
- The practice flow works end-to-end with the new state machine.
- No TypeScript errors.

**Dependencies**: T-7.3 (HomeContext refactor).

---

### T-7.8: Update PracticeChat to use HomeContext instead of URL routing

**Description**: Remove react-router dependencies (useParams, useNavigate, useLocation). Get session data from HomeContext instead.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`

**Changes**:

1. Remove router imports and usage:
```typescript
// REMOVE:
import { useParams, useNavigate, useLocation } from 'react-router-dom'
const { deckId, sessionId } = useParams<{ deckId: string; sessionId: string }>()
const location = useLocation()
const navigate = useNavigate()
const navState = location.state as { ... } | null
```

2. Replace with HomeContext:
```typescript
import { useHome } from './HomeContext'

const { activeSessionData, endPractice, showSummary: showSummaryFn } = useHome()
```

3. Update `loadSession` to use `activeSessionData.sessionId` instead of URL param.

4. Use `activeSessionData.greeting` and `activeSessionData.currentWord` for initial state (replaces `navState`).

5. Update `handleEndSession`:
```typescript
const handleEndSession = async () => {
  if (!session) return
  try {
    await practiceApi.endSession(session.id)
  } catch (error) {
    console.error('Failed to end session:', error)
  } finally {
    endPractice()
  }
}
```

6. Update `handleNewSession`:
```typescript
const handleNewSession = () => {
  endPractice() // Returns to home, user can start new session from DeckDetailPanel
}
```

7. Session complete → call `showSummaryFn(summary)` instead of local `setShowSummary(true)`.

**Acceptance criteria**:
- No `useParams`, `useNavigate`, `useLocation` imports in PracticePanel.
- Session loads from `activeSessionData` context.
- End session calls `endPractice()` from context.
- Session complete calls `showSummary()` from context.
- No TypeScript errors.

**Dependencies**: T-7.3, T-7.7.

---

### T-7.9: Replace WordPanel with FloatingWordPill

**Description**: Remove the `WordPanel` right sidebar component and integrate `FloatingWordPill` inside the scrollable chat area.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`

**Changes**:

1. Remove the entire `WordPanel` function (~70 lines) and its usage.

2. Remove imports: `PanelRightOpen`, `PanelRightClose` from lucide-react.

3. Remove state: `const [wordPanelOpen, setWordPanelOpen] = useState(true)`

4. Add import:
```typescript
import FloatingWordPill from './FloatingWordPill'
```

5. Inside the scrollable chat area, add the pill as the first child (before messages):
```tsx
<div className="flex-1 overflow-y-auto bg-chat-bg">
  <div className="max-w-3xl mx-auto px-6">
    {currentWord && (
      <FloatingWordPill word={currentWord} />
    )}
    {/* Messages... */}
  </div>
</div>
```

6. Remove the outer flex wrapper that previously held chat + WordPanel side by side.

**Acceptance criteria**:
- WordPanel sidebar no longer renders.
- FloatingWordPill appears sticky at the top of the scrollable chat area.
- Word pill updates when `currentWord` changes.

**Dependencies**: T-7.5 (FloatingWordPill component), T-7.7.

---

### T-7.10: Replace QualityRatingModal with inline ConfidenceRating + rerate support

**Description**: Remove the modal-based rating and integrate the inline ConfidenceRating component into the chat message flow. Each rating is tracked as a message with `ratingData`, enabling retroactive editing. Add `rerateWord` to the API client.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`
- `frontend/src/lib/api.ts` -- add `rerateWord` function

**Changes**:

1. Remove the entire `QualityRatingModal` function (~75 lines) and its JSX usage.

2. Add import:
```typescript
import ConfidenceRating from './ConfidenceRating'
```

3. Update the `ChatMessage` interface to support rating data:
```typescript
interface ChatMessage {
  id: string
  role: 'laoshi' | 'user'
  content: string
  feedback?: FeedbackData | null
  ratingData?: {
    wordId: number
    wordText: string
    quality?: number
  }
}
```

4. In `handleNextWord`, add a rating prompt message to the messages array:
```typescript
const handleNextWord = () => {
  setStatus('rating_typing')
  setTimeout(() => {
    // Add rating prompt as a message (tracked for retroactive editing)
    const ratingMsgId = `rating-${Date.now()}`
    setMessages(prev => [...prev, {
      id: ratingMsgId,
      role: 'laoshi',
      content: '', // Content rendered by ConfidenceRating component
      ratingData: {
        wordId: currentWord!.word_id,
        wordText: currentWord!.word,
        quality: undefined,
      },
    }])
    setStatus('awaiting_rating')
  }, 800)
}
```

5. In the messages rendering area, render ConfidenceRating for messages with `ratingData`:
```tsx
{messages.map((msg) => (
  msg.ratingData ? (
    <ConfidenceRating
      key={msg.id}
      messageId={msg.id}
      wordId={msg.ratingData.wordId}
      wordText={msg.ratingData.wordText}
      quality={msg.ratingData.quality}
      isLatest={msg.id === messages.filter(m => m.ratingData).at(-1)?.id && status !== 'waiting_for_user'}
      onRate={handleRate}
    />
  ) : (
    <ChatBubble key={msg.id} message={msg} />
  )
))}
```

6. Create unified `handleRate` that dispatches to nextWord or rerate:
```typescript
const handleRate = async (messageId: string, wordId: number, quality: number, isEdit: boolean) => {
  // Update the rating in the message
  setMessages(prev => prev.map(m =>
    m.id === messageId
      ? { ...m, ratingData: { ...m.ratingData!, quality } }
      : m
  ))

  if (isEdit) {
    // Retroactive edit: call rerate API (independent of practice flow)
    try {
      await practiceApi.rerateWord(wordId, session!.id, quality)
    } catch (error) {
      console.error('Failed to rerate word:', error)
    }
  } else {
    // First-time rating: advance to next word
    setStatus('rating_selected')
    try {
      const response = await practiceApi.nextWord(session!.id, quality)
      const data = response.data

      setSessionStats({
        words_practiced: data.words_practiced,
        words_total: data.words_total,
      })

      if (data.session_complete) {
        if (data.summary) {
          showSummaryFn(data.summary)
        } else {
          const summaryResponse = await practiceApi.getSummary(session!.id)
          showSummaryFn(summaryResponse.data)
        }
      } else {
        setTimeout(() => {
          setShowDivider(true)
          setStatus('transitioning')
          setTimeout(() => {
            setShowDivider(false)
            if (data.current_word) setCurrentWord(data.current_word)
            if (data.laoshi_response) addMessage('laoshi', data.laoshi_response)
            setStatus('waiting_for_user')
            setUserInput('')
          }, 600)
        }, 500)
      }
    } catch (error) {
      console.error('Failed to get next word:', error)
      setStatus('feedback_given')
    }
  }
}
```

7. Add `rerateWord` to `frontend/src/lib/api.ts` in the `practiceApi` object:
```typescript
rerateWord: (wordId: number, sessionId: number, quality: number) =>
  api.post(`/api/words/${wordId}/rerate`, { quality, session_id: sessionId }),
```

**Acceptance criteria**:
- QualityRatingModal no longer renders.
- Each rating prompt is stored as a message with `ratingData`.
- Messages with `ratingData` render as `ConfidenceRating` components.
- First-time rating calls `practiceApi.nextWord()` and advances the practice flow.
- Editing a past rating calls `practiceApi.rerateWord()` independently.
- The rating pill + edit icon appears for all past ratings in the chat history.
- Color coding: 0-2 coral, 3 amber, 4-5 sage.

**Dependencies**: T-7.6 (ConfidenceRating component), T-7.7, T-7.28 (rerate endpoint).

---

### T-7.11: Restyle ChatBubble for spec compliance

**Description**: Update user and AI message bubble styling to match the design spec.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- `ChatBubble` function

**Changes**:

Replace the ChatBubble function:

```tsx
function ChatBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%]">
          <div className="bg-sage rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-[15px] text-white leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
          <p className="text-[10px] text-warm-black/30 mt-1 text-right">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 mb-4">
      <img
        src={laoshiLogo}
        alt="Laoshi"
        className="w-7 h-7 rounded-full flex-shrink-0 self-end mb-5"
      />
      <div className="max-w-[75%]">
        <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 border border-warm-gray/40 shadow-sm">
          <p className="text-[15px] text-warm-black leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
        {message.feedback && (
          <div className="mt-2">
            <FeedbackCard feedback={message.feedback} />
          </div>
        )}
        <p className="text-[10px] text-warm-black/30 mt-1">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
```

**Key changes from current:**
- User bubbles: `bg-sage` (solid green) + `text-white` (was `bg-sage-tint` + dark text)
- User bubbles: `rounded-tr-sm` (was `rounded-br-sm`)
- AI bubbles: `rounded-tl-sm` corner (was `rounded-bl-sm`)
- AI avatar: `w-7 h-7` (was `w-8 h-8`), `self-end mb-5` (aligned to bottom above timestamp)
- Max width: 75% (was 80%)
- Text size: `text-[15px]` (explicit)
- Added timestamps below both bubble types
- FeedbackCard remains inline below AI messages

**Acceptance criteria**:
- User bubbles are sage green with white text.
- AI bubbles are white with warm-gray border and shadow.
- Laoshi avatar appears to the left of AI messages, aligned near bottom.
- Timestamps appear below both message types.
- FeedbackCard still renders below AI feedback messages.

**Dependencies**: T-7.7.

---

### T-7.12: Redesign progress bar and chat header

**Description**: Replace the current header with a 3px progress bar + 56px chat header.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- header section

**Changes**:

Replace the current header with:

```tsx
{/* Progress bar */}
<div className="h-[3px] bg-warm-gray/30">
  <div
    className="h-full bg-sage transition-all duration-500 ease-out"
    style={{ width: `${progressPercent}%` }}
  />
</div>

{/* Chat header */}
<div className="h-14 bg-white/90 backdrop-blur-sm border-b border-warm-gray/50 flex items-center flex-shrink-0">
  <div className="max-w-3xl w-full mx-auto px-6 flex items-center justify-between">
    {/* Left side */}
    <div className="flex items-center gap-3">
      {/* Back button */}
      <button
        onClick={() => setShowEndModal(true)}
        className="text-warm-black/50 hover:text-warm-black transition-colors"
      >
        <ChevronLeft className="w-[18px] h-[18px]" />
      </button>

      {/* Laoshi identity */}
      <div className="w-8 h-8 rounded-full bg-warm-offwhite border border-warm-gray/50 flex items-center justify-center">
        <img src={laoshiLogo} alt="Laoshi" className="w-6 h-6 object-contain" />
      </div>
      <div>
        <p className="text-sm font-medium text-warm-black leading-tight">Laoshi</p>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
          <span className="text-[10px] text-green-600 font-medium">Online</span>
        </div>
      </div>
    </div>

    {/* Right side */}
    <div className="text-right">
      <p className="text-[11px] text-warm-black/50 font-medium">{deckName}</p>
      <p className="text-[10px] text-warm-black/30">
        {sessionStats.words_practiced} / {sessionStats.words_total}
      </p>
    </div>
  </div>
</div>
```

Add import: `ChevronLeft` from lucide-react.

Add state for modal: `const [showEndModal, setShowEndModal] = useState(false)`

**Acceptance criteria**:
- 3px progress bar at top, fills left-to-right with sage green.
- Header shows back chevron, Laoshi avatar+name+online dot, deck name, word counter.
- Back chevron opens End Session modal.
- Header content centered at max-width 768px.

**Dependencies**: T-7.7.

---

### T-7.13: Redesign input area

**Description**: Replace the current simple input with a compound container (textarea + action bar).

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- input area section

**Changes**:

Determine input area state:
```typescript
const isInputLocked = ['rating_typing', 'awaiting_rating', 'rating_selected', 'transitioning', 'session_complete'].includes(status)
const isSessionComplete = status === 'session_complete'
```

Replace input area JSX:

```tsx
{/* Input area */}
<div className="bg-white border-t border-warm-gray/50 px-6 py-4 flex-shrink-0">
  <div className="max-w-3xl mx-auto">
    {isSessionComplete ? (
      /* Session complete: View Summary button */
      <div className="flex justify-center">
        <motion.button
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={() => {/* trigger summary view */}}
          className="flex items-center gap-2 bg-sage hover:bg-sage/90 text-white font-medium px-8 py-3.5 rounded-xl shadow-sm transition-colors"
        >
          View Session Summary
        </motion.button>
      </div>
    ) : isInputLocked ? (
      /* Locked state during rating */
      <div className="bg-warm-offwhite/60 border border-warm-gray/50 rounded-2xl py-5 flex items-center justify-center opacity-60">
        <p className="text-sm text-warm-black/40">Rate your confidence to continue</p>
      </div>
    ) : (
      /* Normal input */
      <div className="border border-warm-gray rounded-2xl focus-within:border-sage focus-within:ring-1 focus-within:ring-sage overflow-hidden transition-colors">
        {/* Textarea */}
        <textarea
          ref={inputRef}
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          placeholder="Type your sentence here..."
          className="w-full px-4 pt-4 pb-2 bg-warm-offwhite resize-none text-[15px] text-warm-black placeholder:text-warm-black/30 focus:outline-none min-h-[80px]"
          disabled={status !== 'waiting_for_user'}
          style={{ opacity: status !== 'waiting_for_user' ? 0.5 : 1 }}
        />

        {/* Action bar */}
        <div className="bg-white border-t border-warm-gray/50 px-4 py-2.5 flex items-center justify-between">
          {/* Left: Next Word button */}
          <button
            onClick={handleNextWord}
            disabled={status !== 'feedback_given'}
            className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
              status === 'feedback_given'
                ? 'text-warm-black/50 hover:text-warm-black'
                : 'text-warm-black/30 cursor-not-allowed'
            }`}
          >
            <ChevronsRight className="w-4 h-4" />
            Next Word
          </button>

          {/* Right: char count + submit */}
          <div className="flex items-center gap-4">
            <span className="text-xs text-warm-black/40">
              {userInput.length} characters
            </span>
            <button
              onClick={handleSubmit}
              disabled={!userInput.trim() || status !== 'waiting_for_user'}
              className="flex items-center gap-1.5 px-6 py-2 rounded-full text-sm font-medium transition-colors bg-warm-gray/50 text-warm-black/50 hover:bg-sage hover:text-white disabled:opacity-50 disabled:hover:bg-warm-gray/50 disabled:hover:text-warm-black/50"
            >
              Submit
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    )}
  </div>
</div>
```

**Acceptance criteria**:
- Normal state: textarea on top, action bar below with Next Word (left) + char count + Submit (right).
- Next Word disabled unless `status === 'feedback_given'`.
- Submit disabled unless text entered and `status === 'waiting_for_user'`.
- Locked state during rating: gentle visual lock with hint text.
- Session complete: centered "View Session Summary" button.

**Dependencies**: T-7.7.

---

### T-7.14: Add word divider and typing indicator updates

**Description**: Add the "next word" divider between words and update the typing indicator to work with the new status states.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`

**Changes**:

1. Add `showDivider` state:
```typescript
const [showDivider, setShowDivider] = useState(false)
```

2. In the `handleQualityRate` success path (non-complete), set divider before transitioning:
```typescript
setTimeout(() => {
  setShowDivider(true)
  setStatus('transitioning')
  setTimeout(() => {
    setShowDivider(false)
    // ... load next word
  }, 600)
}, 500)
```

3. Add divider JSX in the chat area (after confidence rating, before chat end ref):
```tsx
{/* Word divider */}
{showDivider && (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.3 }}
    className="flex items-center gap-4 my-6"
  >
    <div className="flex-1 h-px bg-warm-gray/50" />
    <span className="text-[11px] text-warm-black/25 font-medium tracking-wide uppercase">
      next word
    </span>
    <div className="flex-1 h-px bg-warm-gray/50" />
  </motion.div>
)}
```

4. Update typing indicator to show during `rating_typing` as well:
```tsx
{(status === 'ai_typing' || status === 'rating_typing') && (
  <div className="flex gap-3 mb-4">
    {/* ... existing typing indicator */}
  </div>
)}
```

**Acceptance criteria**:
- Typing indicator shows for both `ai_typing` and `rating_typing` statuses.
- Word divider appears between words during transition (thin line with "next word" text).
- Divider fades in over 300ms.

**Dependencies**: T-7.7.

---

### T-7.15: Add EndSessionModal into PracticeChat

**Description**: Move the EndSessionModal from `home/index.tsx` into PracticePanel and restyle it.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- add modal

**Changes**:

Add the modal inside PracticeChat's return JSX:

```tsx
{/* End Session Modal */}
{showEndModal && (
  <div className="fixed inset-0 z-[60] bg-warm-black/20 backdrop-blur-sm flex items-center justify-center p-4">
    <motion.div
      initial={{ scale: 0.95, opacity: 0, y: 10 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      className="bg-white rounded-2xl shadow-xl max-w-md w-full p-8"
    >
      <div className="flex items-center gap-4 mb-6">
        <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-yellow-600" />
        </div>
        <h3 className="text-xl font-medium text-warm-black">End Current Session?</h3>
      </div>
      <p className="text-base text-warm-black/60 leading-relaxed mb-8">
        You have an active practice session. Ending it will save your progress so far. Are you sure you want to continue?
      </p>
      <div className="flex gap-4 justify-end">
        <button
          onClick={() => setShowEndModal(false)}
          className="px-6 py-2.5 text-warm-black/60 hover:text-warm-black font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => { setShowEndModal(false); handleEndSession() }}
          className="px-6 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl shadow-sm font-medium transition-colors"
        >
          End Session
        </button>
      </div>
    </motion.div>
  </div>
)}
```

Add import: `AlertTriangle` from lucide-react.

**Acceptance criteria**:
- Modal appears when back chevron is clicked in the chat header.
- Cancel dismisses the modal.
- "End Session" calls the end session API and returns to home.
- Modal has backdrop blur, yellow warning icon, rounded-2xl card.

**Dependencies**: T-7.12 (header with back button).

---

### T-7.16: Assemble PracticeChat outer layout

**Description**: Combine all the pieces into the final PracticeChat layout. This is the overall container that replaces the current split-panel structure.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx` -- main return JSX

**Changes**:

The complete render structure:

```tsx
return (
  <div className="h-full flex flex-col bg-chat-bg">
    {/* Progress bar */}
    <div className="h-[3px] bg-warm-gray/30 flex-shrink-0">
      <div className="h-full bg-sage transition-all duration-500 ease-out" style={{ width: `${progressPercent}%` }} />
    </div>

    {/* Chat header */}
    {/* ... (from T-7.12) */}

    {/* Chat area (scrollable) */}
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6">
        {/* Floating word pill */}
        {currentWord && <FloatingWordPill word={currentWord} />}

        {/* Messages */}
        {messages.map((msg) => (
          <ChatBubble key={msg.id} message={msg} />
        ))}

        {/* Typing indicator */}
        {(status === 'ai_typing' || status === 'rating_typing') && (
          <TypingIndicator />
        )}

        {/* Confidence rating (inline) */}
        {(status === 'awaiting_rating' || status === 'rating_selected') && currentWord && (
          <ConfidenceRating
            word={currentWord.word}
            status={status as 'awaiting_rating' | 'rating_selected'}
            selectedRating={selectedRating}
            onRate={handleQualityRate}
          />
        )}

        {/* Word divider */}
        {showDivider && <WordDivider />}

        <div ref={chatEndRef} />
      </div>
    </div>

    {/* Input area */}
    {/* ... (from T-7.13) */}

    {/* End session modal */}
    {/* ... (from T-7.15) */}
  </div>
)
```

Remove the old outer `<div className="flex-1 flex flex-col h-full">` and the inner flex wrapper that held chat + WordPanel.

**Acceptance criteria**:
- Practice chat fills the entire content area (no deck list, no word sidebar).
- Progress bar at top, header below, scrollable chat in middle, input at bottom.
- Word pill sticky at top of scrollable area.
- All sub-components integrate correctly.
- Auto-scroll works on new messages.

**Dependencies**: T-7.7 through T-7.15.

---

## Phase 5: Home Page Integration

Wire the new practice flow into the home page routing and deck detail panel.

---

### T-7.17: Update HomeLayout for conditional rendering

**Description**: HomeLayout conditionally renders different views based on `viewState` instead of always showing DeckListPanel + Routes.

**Files affected**:
- `frontend/src/pages/home/index.tsx` -- rewrite `HomeLayout`

**Changes**:

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { HomeProvider, useHome } from './HomeContext'
import DeckListPanel from './DeckListPanel'
import DeckDetailPanel from './DeckDetailPanel'
import PracticeChat from './PracticePanel'
import EmptyDeckPlaceholder from './EmptyDeckPlaceholder'
import LoadingRitual from './LoadingRitual'
import { SessionSummary } from '../../components/SessionSummary'

function HomeLayout() {
  const { viewState, activeSessionData, summaryData, onLoadingComplete, endPractice, startPractice, backToHome, selectedDeckId } = useHome()

  // Loading ritual
  if (viewState === 'loading') {
    return <LoadingRitual onReady={onLoadingComplete} />
  }

  // Practice chat
  if (viewState === 'practicing' && activeSessionData) {
    return <PracticeChat />
  }

  // Session summary
  if (viewState === 'summary' && summaryData) {
    return (
      <SessionSummary
        summary={summaryData}
        onNewSession={() => {
          // Start a new session on the same deck
          // DeckDetailPanel handles the API call, so just go back to home
          backToHome()
        }}
      />
    )
  }

  // Default: Home view with deck list + detail
  return (
    <div className="flex h-full">
      <DeckListPanel />
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={
            selectedDeckId ? (
              <Navigate to={`/home/deck/${selectedDeckId}`} replace />
            ) : (
              <EmptyDeckPlaceholder />
            )
          } />
          <Route path="deck/:deckId" element={<DeckDetailPanel />} />
        </Routes>
      </div>
    </div>
  )
}

export default function Home() {
  return (
    <HomeProvider>
      <HomeLayout />
    </HomeProvider>
  )
}
```

**Key changes from current:**
- **Removed**: practice route (`deck/:deckId/practice/:sessionId`).
- **Removed**: `EndSessionModal` from HomeLayout (moved into PracticeChat).
- **Added**: Conditional rendering for `loading`, `practicing`, `summary` viewStates.
- When `viewState !== 'home'`, the DeckListPanel and Routes don't render at all -- the entire content area is taken by the active view.

**Acceptance criteria**:
- In `'home'` state: deck list + deck detail panel render (unchanged behavior).
- In `'loading'` state: LoadingRitual fills the content area.
- In `'practicing'` state: PracticeChat fills the content area.
- In `'summary'` state: SessionSummary fills the content area.
- No practice route in the URL. Navigation works via context state.
- The `/home/deck/:deckId/practice/:sessionId` route no longer exists.

**Dependencies**: T-7.3, T-7.4, T-7.16.

---

### T-7.18: Update DeckDetailPanel to trigger viewState

**Description**: Change "Start Practice" to set viewState in context instead of navigating to a practice route.

**Files affected**:
- `frontend/src/pages/home/DeckDetailPanel.tsx`

**Changes**:

Update `handleStartPractice`:

```typescript
const handleStartPractice = async () => {
  if (!deck) return

  setStartingPractice(true)
  try {
    const response = await practiceApi.startSession(deck.id)
    const sessionId = response.data.session.id
    startPractice({
      sessionId,
      deckId: deck.id,
      deckName: deck.name,
      greeting: response.data.greeting_message,
      currentWord: response.data.current_word,
    })
    // No navigate() call -- HomeLayout handles the view transition
  } catch (error) {
    console.error('Failed to start practice:', error)
    alert('Failed to start practice session. Please try again.')
  } finally {
    setStartingPractice(false)
  }
}
```

Also remove or update imports:
- Remove `useNavigate` if no longer used elsewhere in this component (check: `navigate` is used for "Back to Home" and "Manage in Library" links -- keep if still needed).
- Remove `startPractice` from destructured `useHome()` if the function signature changed, and use the new one.

**Acceptance criteria**:
- Clicking "Start Practice" triggers the loading ritual via context, not a URL navigation.
- Session data (greeting, currentWord, deckName) is passed via context.
- No practice-related URL change occurs.

**Dependencies**: T-7.3.

---

### T-7.19: Update DeckListPanel to remove practice-awareness

**Description**: DeckListPanel no longer needs to know about active practice sessions since it's hidden during practice.

**Files affected**:
- `frontend/src/pages/home/DeckListPanel.tsx`

**Changes**:

1. Replace `requestDeckSwitch` with `selectDeck` in the `useHome()` destructuring (if `requestDeckSwitch` was used).
2. Use `selectDeck` directly for deck clicks instead of `requestDeckSwitch`.
3. Remove any references to `activePracticeSessionId` if present.

Check the current DeckListPanel to see if it uses `requestDeckSwitch`. If so, replace with `selectDeck`:

```typescript
// Before:
const { requestDeckSwitch } = useHome()
// Deck click handler:
requestDeckSwitch(deckId)

// After:
const { selectDeck } = useHome()
// Deck click handler:
selectDeck(deckId)
```

**Acceptance criteria**:
- DeckListPanel uses `selectDeck` from the new HomeContext.
- No references to `requestDeckSwitch`, `activePracticeSessionId`, or practice-related context values.
- Deck selection works as before (navigates to deck detail).
- No TypeScript errors.

**Dependencies**: T-7.3.

---

## Phase 6: Session Summary Restyle

---

### T-7.20: Restyle SessionSummary component

**Description**: Update SessionSummary to match the design spec styling with warm color scheme.

**Files affected**:
- `frontend/src/components/SessionSummary.tsx`

**Changes**:

Update the component JSX (keep the same props interface and data flow):

```tsx
import { progressApi } from '../lib/api'
import type { PracticeSummaryResponse } from '../types/api'
import { useHome } from '../pages/home/HomeContext'
import { Check, X } from 'lucide-react'
import { motion } from 'framer-motion'

interface SessionSummaryProps {
  summary: PracticeSummaryResponse
  onNewSession: () => void
}

export function SessionSummary({ summary, onNewSession }: SessionSummaryProps) {
  const { backToHome } = useHome()

  const handleBackToHome = () => {
    progressApi.generateFeedback().catch(() => {})
    backToHome()
  }

  return (
    <div className="h-full overflow-y-auto bg-warm-offwhite">
      <div className="max-w-[56rem] mx-auto py-16 px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <h2 className="font-serif text-3xl font-medium text-warm-black">
            Session Complete!
          </h2>
          <p className="text-warm-black/50 mt-2">
            {summary.words_practiced} practiced, {summary.words_skipped} skipped
          </p>
        </div>

        {/* AI Summary */}
        <div className="bg-sage-tint border border-sage/15 rounded-2xl p-8 mb-10">
          <p className="italic text-base text-warm-black/70 leading-relaxed">
            {summary.summary_text}
          </p>
        </div>

        {/* Results table */}
        <div className="bg-white border border-warm-gray rounded-2xl shadow-sm overflow-hidden mb-12">
          {/* Header row */}
          <div className="bg-warm-offwhite/50 border-b border-warm-gray/50 grid grid-cols-5 gap-4 py-4 px-6">
            {['Word', 'Grammar', 'Usage', 'Naturalness', 'Status'].map((col) => (
              <span key={col} className="text-[11px] uppercase font-bold tracking-wider text-warm-black/40">
                {col}
              </span>
            ))}
          </div>

          {/* Data rows */}
          {summary.word_results.map((result, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + idx * 0.05 }}
              className={`grid grid-cols-5 gap-4 py-4 px-6 items-center ${
                idx < summary.word_results.length - 1 ? 'border-b border-warm-gray/30' : ''
              }`}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-serif text-lg text-warm-black">{result.word}</span>
              </div>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '—' : result.grammar_score?.toFixed(1) ?? '—'}
              </span>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '—' : result.usage_score?.toFixed(1) ?? '—'}
              </span>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '—' : result.naturalness_score?.toFixed(1) ?? '—'}
              </span>
              <div>
                {result.is_skipped ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warm-gray/30 text-warm-black/50">
                    Skipped
                  </span>
                ) : result.is_correct ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage-tint text-sage">
                    <Check className="w-3 h-3" /> Correct
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-coral/10 text-coral">
                    <X className="w-3 h-3" /> Needs work
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={onNewSession}
            className="px-8 py-3.5 bg-sage hover:bg-sage/90 text-white font-medium rounded-xl shadow-sm transition-colors"
          >
            Start New Session
          </button>
          <button
            onClick={handleBackToHome}
            className="px-8 py-3.5 bg-white border border-warm-gray text-warm-black font-medium rounded-xl hover:bg-warm-offwhite transition-colors"
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  )
}
```

**Key changes from current:**
- Uses `useHome().backToHome()` instead of `<Link to="/home">`.
- Serif font for header.
- Sage-tint summary box with sage/15 border.
- Results table uses grid layout with warm color scheme.
- Status pills: sage-tint/sage for correct, coral/10/coral for needs work.
- Staggered row animations (50ms delay per row).
- "Back to Home" is a button (calls `backToHome()`) not a Link.
- Check/X icons from lucide-react for status pills.

**Acceptance criteria**:
- Summary fills the content area with warm color styling.
- Results table rows animate in with stagger.
- "Back to Home" returns to home view via context and fires feedback generation.
- "Start New Session" calls the `onNewSession` callback.

**Dependencies**: T-7.3.

---

## Phase 7: Cleanup and Testing

---

### T-7.21: Remove dead code from PracticePanel

**Description**: Remove the old `QualityRatingModal` and `WordPanel` function definitions from PracticePanel.tsx. Remove unused imports.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`

**Changes**:

1. Delete the `QualityRatingModal` function definition (~75 lines, lines 19-75 approximately).
2. Delete the `WordPanel` function definition (~70 lines, lines 77-146 approximately).
3. Remove unused imports: `X`, `PanelRightOpen`, `PanelRightClose` from lucide-react (verify each is truly unused first).
4. Remove unused state: `wordPanelOpen`.
5. Remove `useParams`, `useNavigate`, `useLocation` imports if still present.

**Acceptance criteria**:
- No dead code remains in PracticePanel.
- No unused imports.
- File compiles without errors.
- `npm run build` succeeds (TypeScript check).

**Dependencies**: T-7.16 (all PracticeChat changes complete).

---

### T-7.22: Remove EndSessionModal from home/index.tsx

**Description**: The EndSessionModal was moved into PracticeChat. Remove it from home/index.tsx.

**Files affected**:
- `frontend/src/pages/home/index.tsx`

**Changes**:

1. Remove the `EndSessionModal` function definition.
2. Remove the `<EndSessionModal />` usage from the old code (should already be gone after T-7.17).
3. Remove `AlertTriangle` import from lucide-react (if unused).

**Acceptance criteria**:
- No EndSessionModal in home/index.tsx.
- No unused imports.
- File compiles without errors.

**Dependencies**: T-7.17.

---

### T-7.23: Verify full flow end-to-end

**Description**: Manual end-to-end test of the complete practice flow.

**Test plan**:

1. **Start practice**:
   - Navigate to `/home`, select a deck with words.
   - Click "Start Practice".
   - Verify: Loading ritual appears with pulsing logo and rotating messages.
   - Verify: URL stays at `/home/deck/:deckId` (no practice/session ID).
   - Verify: After ~5 seconds, practice chat appears.
   - Verify: Deck list panel is NOT visible.
   - Verify: Sidebar is still visible on the left.

2. **Chat interaction**:
   - Verify: Word pill at top shows current word (collapsed).
   - Click word pill → verify it expands to show details.
   - Click outside → verify it collapses.
   - Type a sentence and submit.
   - Verify: Typing indicator shows, then AI response + FeedbackCard appears.
   - Verify: User bubble is sage green with white text.
   - Verify: "Next Word" button in action bar becomes enabled.

3. **Confidence rating**:
   - Click "Next Word".
   - Verify: Typing indicator shows briefly.
   - Verify: Laoshi asks confidence question with 6 inline buttons.
   - Verify: Input area shows locked state.
   - Click a rating button.
   - Verify: Buttons collapse, inline pill shows selection.
   - Verify: Word divider appears ("next word").
   - Verify: Word pill transitions to new word.
   - Verify: New word greeting message appears.

4. **Session complete**:
   - Practice through all words in the deck.
   - After last rating, verify: Laoshi sends wrap-up message.
   - Verify: "View Session Summary" button appears in input area.
   - Click it → verify: Session Summary displays with styled table.
   - Click "Back to Home" → verify: Returns to deck detail.

5. **End session early**:
   - Start a new session.
   - Click back chevron in header.
   - Verify: End Session modal appears with yellow warning icon.
   - Click "Cancel" → verify: Returns to chat.
   - Click back chevron again → click "End Session" → verify: Returns to home.

6. **Session persistence**:
   - Start a new session.
   - Refresh the page (F5).
   - Verify: Practice chat resumes (loads session from API using localStorage data).
   - End the session normally.
   - Verify: localStorage key is cleared.

7. **Sidebar navigation during practice**:
   - Start a practice session.
   - Click "Library" in the sidebar.
   - Verify: Navigates to Library page (session state cleared or persisted in localStorage for later resume).
   - Navigate back to `/home`.
   - Verify: If session was persisted, practice resumes. Otherwise, shows deck detail.

**Dependencies**: All previous tasks.

---

### T-7.24: Run build and fix any TypeScript errors

**Description**: Ensure the project builds successfully with no TypeScript errors.

**Steps**:
1. Run `npm run build` from the project root.
2. Fix any TypeScript errors that arise.
3. Run existing tests: `npm test -- --run` and ensure no regressions.

**Acceptance criteria**:
- `npm run build` succeeds with zero errors.
- All existing tests pass.
- No console warnings related to M7 changes.

**Dependencies**: T-7.21, T-7.22.

---

## Dependency Graph

```
Phase 1 (parallel):
  T-7.1  (tailwind)       ──┐
  T-7.2  (CSS)             ──┤
                             │
Phase 1B (parallel, backend):│
  T-7.25 (srs_snapshot col)──┤── no frontend deps
  T-7.26 (migration)       ──┤── depends on T-7.25
  T-7.27 (save snapshot)   ──┤── depends on T-7.25
  T-7.28 (rerate endpoint) ──┤── depends on T-7.25, T-7.27
                             │
Phase 2:                     │
  T-7.3  (HomeContext)      ──┤
                             │
Phase 3 (parallel):          │
  T-7.4  (Loading)          ──┤── depends on T-7.2
  T-7.5  (WordPill)         ──┤── no deps
  T-7.6  (Rating+Edit)      ──┤── no deps
                             │
Phase 4 (sequential):        │
  T-7.7  (status enum)      ──┤── depends on T-7.3
  T-7.8  (context)          ──┤── depends on T-7.3, T-7.7
  T-7.9  (word pill)        ──┤── depends on T-7.5, T-7.7
  T-7.10 (rating+rerate)    ──┤── depends on T-7.6, T-7.7, T-7.28
  T-7.11 (bubbles)          ──┤── depends on T-7.7
  T-7.12 (header)           ──┤── depends on T-7.7
  T-7.13 (input)            ──┤── depends on T-7.7
  T-7.14 (divider)          ──┤── depends on T-7.7
  T-7.15 (modal)            ──┤── depends on T-7.12
  T-7.16 (assemble)         ──┤── depends on T-7.7-T-7.15
                             │
Phase 5 (parallel):          │
  T-7.17 (HomeLayout)       ──┤── depends on T-7.3, T-7.4, T-7.16
  T-7.18 (DeckDetail)       ──┤── depends on T-7.3
  T-7.19 (DeckList)         ──┤── depends on T-7.3
                             │
Phase 6:                     │
  T-7.20 (Summary)          ──┤── depends on T-7.3
                             │
Phase 7 (sequential):        │
  T-7.21 (cleanup)          ──┤── depends on T-7.16
  T-7.22 (cleanup)          ──┤── depends on T-7.17
  T-7.23 (e2e test)         ──┤── depends on all
  T-7.24 (build)            ──┘── depends on all
```
