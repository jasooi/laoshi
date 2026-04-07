# Milestone 8: Final UI Fixes -- Design Document

> **Source of truth for architecture**: `.claude/architecture.md`
> This document describes M8-specific technical design decisions.

---

## 1. Architecture Overview

### 1.1 Core Problem: Sharing Deck Count

`EmptyDeckPlaceholder` needs to know whether the user has decks to display the correct title text. Currently, deck data is fetched only in `DeckListPanel` and is not shared with sibling components.

**Solution:** Add `deckCount` and `setDeckCount` to `HomeContext`. `DeckListPanel` calls `setDeckCount` after loading decks. `EmptyDeckPlaceholder` reads `deckCount` from the context via `useHome()`.

This is the minimal change -- no new API calls, no prop drilling, and the context already connects both components.

### 1.2 No Backend Changes

All changes are frontend-only. No new endpoints, models, or migrations.

---

## 2. Component Changes

### 2.1 Modified Components

| Component | File | Changes |
|-----------|------|---------|
| Sidebar | `components/Sidebar.tsx` | Remove Laoshi logo image and its import |
| HomeContext | `pages/home/HomeContext.tsx` | Add `deckCount` state + `setDeckCount` to context value |
| DeckListPanel | `pages/home/DeckListPanel.tsx` | Call `setDeckCount(decks.length)` after fetching decks |
| EmptyDeckPlaceholder | `pages/home/EmptyDeckPlaceholder.tsx` | Replace content: Laoshi logo, conditional title, new subtitle, remove button + tip |

### 2.2 No New Components

No new files are created.

### 2.3 No Removed Components

No files are deleted.

---

## 3. Component Details

### 3.1 Sidebar (logo removal)

Remove the `<div className="mb-4">` block containing the `<img>` tag (lines 66-73). Remove the `laoshiLogo` import (line 3). The navigation items and logout button are untouched.

### 3.2 HomeContext (deckCount state)

Add to `HomeContextValue` interface:
```typescript
deckCount: number
setDeckCount: (count: number) => void
```

Add state in `HomeProvider`:
```typescript
const [deckCount, setDeckCount] = useState(0)
```

Expose both in the context provider value.

### 3.3 DeckListPanel (report deck count)

After `setDecks(decksRes.data.decks)` in `loadData`, add:
```typescript
setDeckCount(decksRes.data.decks.length)
```

Where `setDeckCount` is destructured from `useHome()`.

### 3.4 EmptyDeckPlaceholder (redesign)

**Before:**
- BookOpen icon in gray circle
- "Welcome to Laoshi Coach!" heading
- Description paragraph
- "Create New Deck" button
- Tip text

**After:**
- Laoshi logo in a circular container with border (w-32 h-32, rounded-full, border-4 border-warm-gray/30)
- Conditional heading with emoji: `deckCount === 0 ? "Add a deck to begin" : "Select a deck to begin"`
- Subtitle: "Laoshi is waiting for you in the classroom."
- No button, no tip text

The component imports `laoshiLogo` from assets and reads `deckCount` from `useHome()`.

---

## 4. File Impact Summary

### Files Modified
| File | Scope of Change |
|------|----------------|
| `frontend/src/components/Sidebar.tsx` | Remove logo image + import (~8 lines removed) |
| `frontend/src/pages/home/HomeContext.tsx` | Add `deckCount` + `setDeckCount` (~6 lines added) |
| `frontend/src/pages/home/DeckListPanel.tsx` | Call `setDeckCount` after loading (~2 lines added) |
| `frontend/src/pages/home/EmptyDeckPlaceholder.tsx` | Rewrite component content (~20 lines changed) |

### Files NOT Changed
| File | Reason |
|------|--------|
| `frontend/src/pages/home/index.tsx` | HomeLayout routing unchanged |
| `frontend/src/pages/home/DeckDetailPanel.tsx` | Deck detail view unchanged |
| `frontend/src/pages/home/PracticePanel.tsx` | Practice flow unchanged |
| `frontend/src/components/Layout.tsx` | Layout structure unchanged |
| All backend files | No backend changes |

---

## 5. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sharing deck count | HomeContext state | Minimal change; context already connects DeckListPanel and EmptyDeckPlaceholder |
| Logo styling | Circular with border | Matches the mockup reference image |
| Emoji in title | Pointing-left hand emoji | Draws user attention to the deck list on the left |
| Remove duplicate button | Yes | DeckListPanel already has "+ New Deck" at the bottom; duplicating it on the placeholder is redundant |
