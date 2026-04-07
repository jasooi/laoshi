# Milestone 8: Final UI Fixes -- Requirements Document

## Feature Overview

Milestone 8 is a small set of UI adjustments to the Home page that polish the layout before release. The changes affect the left navigation sidebar and the right-side placeholder screen shown when no deck is selected.

**What already exists:**
- `Sidebar.tsx` renders a Laoshi logo image above the nav items (Home, Library, Report Card, Settings).
- `EmptyDeckPlaceholder.tsx` renders when no deck is selected. It shows a BookOpen icon, "Welcome to Laoshi Coach!" title, a "Create New Deck" button, and a tip paragraph.
- `DeckListPanel.tsx` fetches the user's decks and renders them in the left panel. It already has a "+ New Deck" button at the bottom.
- `HomeContext.tsx` manages shared state across the Home page (selected deck, view state, etc.).

**What this milestone delivers:**
1. **Remove Laoshi logo from the sidebar** -- the logo above the Home nav item is removed.
2. **Add Laoshi logo to the placeholder screen** -- the right-side placeholder shows the Laoshi logo as a larger circular image (similar to the loading ritual style).
3. **Conditional title text** -- "Add a deck to begin" when the user has zero decks, "Select a deck to begin" when at least one deck exists.
4. **Remove duplicate elements** -- the "Create New Deck" button and tip text are removed from the placeholder (the DeckListPanel already has a "+ New Deck" button).
5. **Updated subtitle** -- "Laoshi is waiting for you in the classroom."

**No backend changes required.**

---

## User Stories

### US-01: Clean sidebar without logo

**As a** user, **I want** the navigation sidebar to show only navigation icons (no Laoshi logo above them) **so that** the sidebar is clean and compact.

**Acceptance Criteria:**
- The Laoshi logo image no longer appears in the sidebar.
- All navigation items (Home, Library, Report Card, Settings) remain unchanged.
- The logout button at the bottom remains unchanged.

### US-02: Welcoming placeholder with Laoshi branding

**As a** user, **I want** the right-side placeholder screen to show the Laoshi logo prominently with a clear call to action **so that** I know what to do when I first land on the Home page.

**Acceptance Criteria:**
- The BookOpen icon is replaced with the Laoshi logo image, displayed in a circular container with a border (similar to the mockup reference).
- The logo is centered above the title text.
- The "Create New Deck" button is removed from the placeholder.
- The tip text below the button is removed.

### US-03: Context-aware title text

**As a** user, **I want** the placeholder title to tell me whether I need to add a deck or select one **so that** I get the right guidance based on my current state.

**Acceptance Criteria:**
- When the user has **zero decks**: title reads "Add a deck to begin" (with pointing-left emoji prefix).
- When the user has **one or more decks**: title reads "Select a deck to begin" (with pointing-left emoji prefix).
- Subtitle below the title reads: "Laoshi is waiting for you in the classroom."
