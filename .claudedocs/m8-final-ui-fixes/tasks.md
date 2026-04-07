# Milestone 8: Final UI Fixes -- Task Breakdown

## Task Overview

**Total tasks**: 6 tasks (8.1-8.6) across 3 phases
**All changes are frontend-only.** No backend changes.

---

## Prerequisites

Before starting any tasks:

1. Ensure Milestone 7 is complete and all tests pass.
2. Ensure the dev server starts without errors: `npm run dev` (from `frontend/`).

---

## Phase 1: Context Foundation

Add deck count sharing to HomeContext. This enables the conditional title in EmptyDeckPlaceholder.

---

### T-8.1: Add deckCount state to HomeContext

**Status**: [ ] Not started

**Description**: Add `deckCount` and `setDeckCount` to the HomeContext so that `DeckListPanel` can report how many decks exist and `EmptyDeckPlaceholder` can read it.

**Files affected**:
- `frontend/src/pages/home/HomeContext.tsx` -- add state + expose in context

**Changes**:

1. Add to `HomeContextValue` interface:
```typescript
deckCount: number
setDeckCount: (count: number) => void
```

2. Add state in `HomeProvider` (after existing state declarations):
```typescript
const [deckCount, setDeckCountState] = useState(0)
```

3. Create a stable setter with useCallback:
```typescript
const setDeckCount = useCallback((count: number) => {
  setDeckCountState(count)
}, [])
```

4. Add `deckCount` and `setDeckCount` to the provider value object.

**Acceptance criteria**:
- `useHome()` returns `deckCount` (number) and `setDeckCount` (function).
- Default `deckCount` is 0.
- No TypeScript errors.

**Dependencies**: None.

---

### T-8.2: Report deck count from DeckListPanel

**Status**: [ ] Not started

**Description**: After fetching decks in `DeckListPanel`, report the count to HomeContext.

**Files affected**:
- `frontend/src/pages/home/DeckListPanel.tsx` -- add `setDeckCount` call

**Changes**:

1. Destructure `setDeckCount` from `useHome()` (line 125):
```typescript
const { selectedDeckId, selectDeck, setDeckCount } = useHome()
```

2. After `setDecks(decksRes.data.decks)` in `loadData` (after line 138), add:
```typescript
setDeckCount(decksRes.data.decks.length)
```

**Acceptance criteria**:
- After DeckListPanel finishes loading, `deckCount` in HomeContext reflects the actual number of decks.
- Existing deck list rendering unchanged.
- No TypeScript errors.

**Dependencies**: T-8.1.

---

## Phase 2: UI Changes

Remove the sidebar logo and redesign the placeholder. These two tasks are independent and can be done in parallel.

---

### T-8.3: Remove Laoshi logo from Sidebar

**Status**: [ ] Not started

**Description**: Remove the Laoshi logo image that appears above the navigation items in the sidebar.

**Files affected**:
- `frontend/src/components/Sidebar.tsx` -- remove logo block + import

**Changes**:

1. Remove the import (line 3):
```typescript
// DELETE: import laoshiLogo from '../assets/laoshi-logo.png'
```

2. Remove the logo block (lines 66-73):
```tsx
// DELETE:
{/* Logo/Brand */}
<div className="mb-4">
  <img
    src={laoshiLogo}
    alt="Laoshi Logo"
    className="w-16 h-16 rounded-2xl object-cover"
  />
</div>
```

**Acceptance criteria**:
- No Laoshi logo appears in the sidebar.
- Navigation items (Home, Library, Report Card, Settings) render correctly.
- Logout button at the bottom renders correctly.
- No unused imports.

**Dependencies**: None. Can be done in parallel with T-8.4.

---

### T-8.4: Redesign EmptyDeckPlaceholder

**Status**: [ ] Not started

**Description**: Replace the current placeholder content with the Laoshi logo, conditional title text, and new subtitle. Remove the "Create New Deck" button and tip text.

**Files affected**:
- `frontend/src/pages/home/EmptyDeckPlaceholder.tsx` -- rewrite component

**Changes**:

Replace the entire component with:

```tsx
import laoshiLogo from '../../assets/laoshi-logo.png'
import { useHome } from './HomeContext'

export default function EmptyDeckPlaceholder() {
  const { deckCount } = useHome()

  return (
    <div className="flex-1 flex items-center justify-center bg-warm-offwhite p-8">
      <div className="max-w-md w-full text-center">
        {/* Laoshi logo */}
        <div className="w-32 h-32 rounded-full border-4 border-warm-gray/30 overflow-hidden mx-auto mb-8">
          <img
            src={laoshiLogo}
            alt="Laoshi"
            className="w-full h-full object-cover"
          />
        </div>

        {/* Conditional title */}
        <h2 className="text-2xl font-bold text-warm-black mb-2">
          {deckCount === 0 ? '\u{1F449} Add a deck to begin' : '\u{1F449} Select a deck to begin'}
        </h2>

        {/* Subtitle */}
        <p className="text-warm-muted">
          Laoshi is waiting for you in the classroom.
        </p>
      </div>
    </div>
  )
}
```

**Key changes from current:**
- Removed: `useNavigate` import and usage
- Removed: `BookOpen`, `Plus` imports from lucide-react
- Removed: "Create New Deck" button
- Removed: Tip text paragraph
- Added: `laoshiLogo` import + circular image display
- Added: `useHome()` for `deckCount`
- Added: Conditional title with pointing emoji
- Added: New subtitle text

**Acceptance criteria**:
- Laoshi logo displays in a circular container with a subtle border.
- Title shows "Add a deck to begin" when user has no decks.
- Title shows "Select a deck to begin" when user has decks.
- Both titles are prefixed with the pointing-left emoji.
- Subtitle reads "Laoshi is waiting for you in the classroom."
- No "Create New Deck" button on the placeholder.
- No tip text on the placeholder.
- No unused imports.

**Dependencies**: T-8.1 (deckCount in context). Can be done in parallel with T-8.3.

---

## Phase 3: Verification

---

### T-8.5: Run TypeScript build check

**Status**: [ ] Not started

**Description**: Ensure all changes compile without TypeScript errors.

**Steps**:
1. Run `npx tsc --noEmit` from `frontend/`.
2. Fix any TypeScript errors.

**Acceptance criteria**:
- `npx tsc --noEmit` succeeds with zero errors.
- No new warnings introduced.

**Dependencies**: T-8.1, T-8.2, T-8.3, T-8.4.

---

### T-8.6: Run existing frontend tests

**Status**: [ ] Not started

**Description**: Ensure no regressions in existing tests.

**Steps**:
1. Run `npx vitest run` from `frontend/`.
2. Verify all previously passing tests still pass.
3. Note: `ProtectedRoute.test.tsx` is known to hang -- skip if needed.

**Acceptance criteria**:
- All previously passing frontend tests still pass.
- No regressions introduced by M8 changes.

**Dependencies**: T-8.5.

---

## Dependency Graph

```
Phase 1:
  T-8.1  (HomeContext: deckCount)  ──┐
  T-8.2  (DeckListPanel: report)   ──┤── depends on T-8.1
                                     │
Phase 2 (parallel):                  │
  T-8.3  (Sidebar: remove logo)    ──┤── no deps
  T-8.4  (Placeholder: redesign)   ──┤── depends on T-8.1
                                     │
Phase 3 (sequential):               │
  T-8.5  (TypeScript build)        ──┤── depends on T-8.1-T-8.4
  T-8.6  (Run tests)              ──┘── depends on T-8.5
```
