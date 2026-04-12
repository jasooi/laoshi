# Milestone 9: Onboarding Flow -- Requirements Document

## Feature Overview

Milestone 9 adds a 4-card onboarding wizard for first-time users. When a user registers and logs in for the first time, they are guided through a sequence of introduction cards before reaching the main app.

**What already exists:**
- `Welcome.tsx` at route `/` shows a generic landing page with "Get started" and "Skip for now" buttons.
- `Register.tsx` auto-logs in the user after registration and navigates to `/`.
- `Login.tsx` navigates to `/home` (or saved path) after login.
- `AuthContext.tsx` manages authentication state with `{ id, username, preferred_name }` on the User object.
- `UserProfile` model has `preferred_name` field (nullable, lazy-created via PUT /api/settings).
- `PUT /api/settings` accepts `preferred_name` and `words_per_session`, auto-creating the profile if missing.
- `GET /api/me` returns `{ id, username, preferred_name }`.
- framer-motion is installed and used throughout the app for animations.
- Warm color palette (sage, coral, amber) configured in Tailwind.

**What this milestone delivers:**
1. **Onboarding tracking**: New `onboarding_complete` boolean on `UserProfile`, exposed via `GET /api/me` and `PUT /api/settings`.
2. **4-card wizard**: Replaces the Welcome page for first-time users with a step-by-step introduction flow.
3. **Name collection**: Card 1 collects the user's preferred name and saves it to their profile immediately.
4. **Returning user handling**: Users who have completed onboarding are redirected from `/` to `/home`. Existing users are auto-marked as onboarding-complete via migration.

**Backend changes**: One new column on UserProfile, updates to `format_data()` / `format_settings()` / `PUT /api/settings`, one Alembic migration.

---

## User Stories

### US-01: First-time onboarding experience
**As a** new user, **I want** to be guided through a brief introduction to the app when I first sign up **so that** I understand how Laoshi, decks, and practice work before diving in.

**Acceptance Criteria:**
- After registering and auto-logging in, the user sees a 4-card wizard at `/`.
- The wizard fills the full viewport (no sidebar, no header) with a centered card.
- Cards transition with horizontal slide animations.
- Dot indicators at the bottom show progress (4 dots, active dot is wider and sage-colored).
- Back button is available on cards 2-4. Card 1 has no back button.

### US-02: Name collection
**As a** new user, **I want** Laoshi to ask for my name during onboarding **so that** the app can address me personally.

**Acceptance Criteria:**
- Card 1 shows a greeting ("Nice to meet you!"), a subtitle ("What should we call you?"), and a text input.
- The text input is auto-focused and accepts up to 80 characters.
- Helper text reads "You can always change this later in Settings".
- Clicking "Next" saves the name via `PUT /api/settings { preferred_name }`.
- If the user leaves the name blank, the field sends `null` and the user can still proceed.
- The name appears in `AuthContext.user.preferred_name` immediately after saving (no page reload needed).

### US-03: Meet Laoshi introduction
**As a** new user, **I want** to be introduced to Laoshi **so that** I understand what kind of tutor I'm working with.

**Acceptance Criteria:**
- Card 2 shows the Laoshi logo image (from `assets/laoshi-logo.png`), a heading ("Meet Laoshi"), and a paragraph explaining that Laoshi is an AI tutor who coaches sentence creation practice and provides feedback.
- No user interaction required other than clicking "Next".

### US-04: Deck explanation
**As a** new user, **I want** to understand how decks work **so that** I know how to organize my vocabulary.

**Acceptance Criteria:**
- Card 3 shows a Library icon (matching the sidebar icon), a heading ("Organize with Decks"), and a paragraph explaining:
  - Group vocabulary into decks by topic
  - Add words via CSV upload or manual input
  - Find decks in the Library (with inline Library icon)
- No user interaction required other than clicking "Next".

### US-05: Practice overview and completion
**As a** new user, **I want** to understand how practice and progress tracking work **so that** I know what to expect.

**Acceptance Criteria:**
- Card 4 shows a heading ("Ready to Practice") and 3 brief descriptions:
  - **Start from Home**: decks appear on the left, click one to practice.
  - **Smart scheduling**: Laoshi uses spaced repetition to prioritize difficult words.
  - **Track progress**: check feedback per deck and overall growth in Report Card.
- A "Let's get started!" button replaces the "Next" button.
- Clicking "Let's get started!" saves `onboarding_complete: true` via `PUT /api/settings` and navigates to `/home`.

### US-06: Returning users skip onboarding
**As a** returning user, **I want** to go straight to the home page when I log in **so that** I'm not shown the onboarding again.

**Acceptance Criteria:**
- Users with `onboarding_complete === true` who navigate to `/` are immediately redirected to `/home`.
- All existing users in the database are marked as `onboarding_complete = true` by the Alembic migration.
- The login flow continues to navigate to `/home` by default (no change to Login.tsx).

### US-07: Mid-onboarding abandonment
**As a** user who closes the browser during onboarding, **I want** to see the onboarding again on my next login **so that** I complete the full introduction.

**Acceptance Criteria:**
- If the user completes card 1 (name saved) but closes before card 4, `onboarding_complete` remains `false`.
- On next login, `GET /api/me` returns `onboarding_complete: false`.
- The Welcome page at `/` renders the onboarding wizard again (starting from card 1).
- The name input will be empty again (since AuthContext is fresh), but the saved `preferred_name` persists in the database.
