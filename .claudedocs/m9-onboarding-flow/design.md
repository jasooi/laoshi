# Milestone 9: Onboarding Flow -- Design Document

> **Source of truth for architecture**: `.claude/architecture.md`
> This document describes M9-specific technical design decisions and component architecture.

---

## 1. Architecture Overview

### 1.1 Core Change: Conditional Welcome Page

**Before (current):** The Welcome page at `/` is a static page with "Get started" and "Skip for now" buttons. All authenticated users can see it.

**After (M9):** The Welcome page conditionally renders:
- `user.onboarding_complete === false` (or `undefined`) → Render `<OnboardingWizard />`
- `user.onboarding_complete === true` → Redirect to `/home`

No new routes are added. The existing `/` route continues to render `Welcome.tsx` inside a `ProtectedRoute`.

### 1.2 Onboarding Completion Tracking

**New column:** `UserProfile.onboarding_complete` (Boolean, NOT NULL, default=False)

**How new users flow:**
1. Register → `POST /api/users` creates User (no UserProfile yet)
2. Auto-login → `GET /api/me` returns `onboarding_complete: false` (profile is None)
3. Navigate to `/` → Welcome.tsx renders OnboardingWizard
4. Card 1 "Next" → `PUT /api/settings { preferred_name }` lazy-creates UserProfile with `onboarding_complete=false`
5. Card 4 "Let's get started!" → `PUT /api/settings { onboarding_complete: true }` marks complete
6. Navigate to `/home`

**How existing users are handled:**
- Alembic migration adds `onboarding_complete` column with `server_default=false`
- Migration then runs `UPDATE user_profile SET onboarding_complete = true` for all existing rows
- Migration creates UserProfile rows (with `onboarding_complete=true`) for any existing users missing a profile
- Result: all existing users have `onboarding_complete=true`, so they never see onboarding

**Edge case — profile is None:**
- `User.format_data()` returns `onboarding_complete: false` when `self.profile is None`
- After migration, the only users with `profile is None` are brand-new registrants (post-deployment)
- This is correct: new users should see onboarding

### 1.3 Backend API Changes

All existing APIs remain unchanged. Modifications only:

| Endpoint | Change |
|----------|--------|
| `GET /api/me` | Response now includes `onboarding_complete` boolean |
| `GET /api/settings` | Response now includes `onboarding_complete` boolean |
| `PUT /api/settings` | Accepts optional `onboarding_complete` boolean field |

---

## 2. Component Architecture

### 2.1 Modified Components

| Component | File | Changes |
|-----------|------|---------|
| Welcome | `pages/Welcome.tsx` | Conditional render: OnboardingWizard vs redirect to /home |
| AuthContext | `contexts/AuthContext.tsx` | Add `onboarding_complete` to User interface, add `updateUser` method |

### 2.2 New Components

| Component | File | Purpose |
|-----------|------|---------|
| OnboardingWizard | `pages/onboarding/OnboardingWizard.tsx` | Wizard orchestrator: step state, API calls, navigation, animations |
| NameCard | `pages/onboarding/NameCard.tsx` | Card 1: name input |
| MeetLaoshiCard | `pages/onboarding/MeetLaoshiCard.tsx` | Card 2: Laoshi introduction |
| DecksCard | `pages/onboarding/DecksCard.tsx` | Card 3: deck explanation |
| PracticeCard | `pages/onboarding/PracticeCard.tsx` | Card 4: practice overview |
| StepIndicator | `pages/onboarding/StepIndicator.tsx` | Dot progress indicator |

### 2.3 Component Tree

```
ProtectedRoute
  └── Welcome
      └── OnboardingWizard (if !onboarding_complete)
          ├── AnimatePresence
          │   └── [NameCard | MeetLaoshiCard | DecksCard | PracticeCard]
          ├── Navigation buttons (Back / Next / Let's get started!)
          └── StepIndicator (4 dots)
```

---

## 3. Data Flow

### 3.1 AuthContext Extension

Current User interface:
```typescript
interface User {
  id: number
  username: string
  preferred_name: string | null
}
```

Updated User interface:
```typescript
interface User {
  id: number
  username: string
  preferred_name: string | null
  onboarding_complete: boolean
}
```

New method on AuthContextType:
```typescript
updateUser: (updates: Partial<User>) => void
```

This allows OnboardingWizard to update the local user state without re-fetching `/api/me`:
- After card 1: `updateUser({ preferred_name: "Jasmine" })`
- After card 4: `updateUser({ onboarding_complete: true })`

### 3.2 API Call Sequence

```
Card 1 → "Next":
  PUT /api/settings { preferred_name: "Jasmine" }  // lazy-creates profile
  updateUser({ preferred_name: "Jasmine" })

Card 2 → "Next":  (no API call)
Card 3 → "Next":  (no API call)

Card 4 → "Let's get started!":
  PUT /api/settings { onboarding_complete: true }
  updateUser({ onboarding_complete: true })
  navigate('/home', { replace: true })
```

---

## 4. Component Details

### 4.1 OnboardingWizard

Main orchestrator (~100 lines). Manages step state, animation direction, and API calls.

**State:**
- `currentStep: number` (0-3)
- `preferredName: string` (from card 1 input)
- `isSaving: boolean` (loading state during API calls)
- `direction: number` (1 = forward, -1 = back — for animation direction)

**Layout:**
- Full viewport: `min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100`
- Card container: `bg-white rounded-3xl shadow-lg p-8 max-w-md w-full`
- Matches existing Welcome.tsx background gradient

**Animation:**
- framer-motion `AnimatePresence` with `mode="wait"` and `custom={direction}`
- Slide variants: enter from right (forward) or left (back), exit to left (forward) or right (back)
- 300px horizontal offset, 300ms duration, easeInOut

**Navigation buttons:**
- Back (cards 2-4): text button, `text-warm-muted hover:text-warm-black`
- Next (cards 1-3): `bg-sage text-white rounded-full px-8 py-3`
- "Let's get started!" (card 4): same style as Next
- Disabled state during API save: `disabled:opacity-50`, text changes to "Saving..."

### 4.2 NameCard

Simple presentational component (~30 lines).

- Waving hand emoji (text-5xl)
- Heading: "Nice to meet you!" (`text-2xl font-bold text-warm-black`)
- Subtitle: "What should we call you?" (`text-warm-muted`)
- Text input: centered, `rounded-xl`, `focus:ring-2 focus:ring-sage`, auto-focused, maxLength 80
- Helper text: "You can always change this later in Settings" (`text-xs text-warm-muted`)

Props: `{ name: string, onNameChange: (name: string) => void }`

### 4.3 MeetLaoshiCard

Simple presentational component (~20 lines).

- Laoshi logo image: `w-24 h-24 mx-auto rounded-2xl` (from `assets/laoshi-logo.png`)
- Heading: "Meet Laoshi"
- Description paragraph about AI tutoring and sentence practice feedback

### 4.4 DecksCard

Presentational component (~30 lines).

- Library icon in sage-tint circle: `w-16 h-16 rounded-2xl bg-sage-tint` with book SVG (reuse from Sidebar.tsx)
- Heading: "Organize with Decks"
- Description with inline Library icon reference

### 4.5 PracticeCard

Presentational component (~30 lines).

- Visual element (seal.png or icon)
- Heading: "Ready to Practice"
- 3 text blocks with bold labels:
  - **Start from Home** — decks on the left, click to practice
  - **Smart scheduling** — spaced repetition for difficult words
  - **Track progress** — feedback per deck, Report Card

### 4.6 StepIndicator

Tiny reusable component (~15 lines).

- Row of 4 dots, centered (`flex justify-center gap-2`)
- Active dot: `w-6 h-2 rounded-full bg-sage`
- Inactive dot: `w-2 h-2 rounded-full bg-warm-gray`
- Transition: `transition-all duration-300`

Props: `{ currentStep: number, totalSteps: number }`

---

## 5. Backend Model Changes

### 5.1 UserProfile (models.py)

Add column:
```python
onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)
```

Update `format_settings()` to include:
```python
'onboarding_complete': self.onboarding_complete,
```

### 5.2 User.format_data() (models.py)

Add to the self-viewer return dict:
```python
'onboarding_complete': (self.profile.onboarding_complete if self.profile else False),
```

### 5.3 PUT /api/settings (settings_resources.py)

Add handling after existing field updates:
```python
if 'onboarding_complete' in data:
    if not isinstance(data['onboarding_complete'], bool):
        return {"error": "onboarding_complete must be a boolean"}, 400
    profile.onboarding_complete = data['onboarding_complete']
```

Add `'onboarding_complete': False` to the GET no-profile fallback response.

### 5.4 Alembic Migration

```sql
-- Add column
ALTER TABLE user_profile ADD COLUMN onboarding_complete BOOLEAN NOT NULL DEFAULT false;

-- Mark all existing profiles as complete
UPDATE user_profile SET onboarding_complete = true;

-- Create profiles for users who don't have one (with onboarding_complete=true)
INSERT INTO user_profile (user_id, onboarding_complete, deepseek_key_version, gemini_key_version, current_streak, created_ds, updated_ds)
SELECT u.id, true, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM "user" u
LEFT JOIN user_profile up ON u.id = up.user_id
WHERE up.id IS NULL;
```

---

## 6. File Impact Summary

### Files Modified
| File | Scope of Change |
|------|----------------|
| `backend/models.py` | Add `onboarding_complete` column, update `format_data()` and `format_settings()` |
| `backend/settings_resources.py` | Accept `onboarding_complete` in PUT, add to GET fallback |
| `frontend/src/types/api.ts` | Add `onboarding_complete` to User and UserSettings interfaces |
| `frontend/src/contexts/AuthContext.tsx` | Add `onboarding_complete` to User, add `updateUser` method |
| `frontend/src/pages/Welcome.tsx` | Conditional render: wizard vs redirect |

### Files Created
| File | Purpose |
|------|---------|
| `frontend/src/pages/onboarding/OnboardingWizard.tsx` | Wizard orchestrator |
| `frontend/src/pages/onboarding/NameCard.tsx` | Card 1: name input |
| `frontend/src/pages/onboarding/MeetLaoshiCard.tsx` | Card 2: Laoshi intro |
| `frontend/src/pages/onboarding/DecksCard.tsx` | Card 3: deck explanation |
| `frontend/src/pages/onboarding/PracticeCard.tsx` | Card 4: practice overview |
| `frontend/src/pages/onboarding/StepIndicator.tsx` | Dot progress indicator |
| `backend/migrations/versions/<hash>_add_onboarding_complete.py` | Database migration |

### Files NOT Changed
| File | Reason |
|------|--------|
| `frontend/src/App.tsx` | Route `/` → `<Welcome />` stays the same |
| `frontend/src/pages/Login.tsx` | Login still navigates to `/home` |
| `frontend/src/pages/Register.tsx` | Register still navigates to `/` |
| `frontend/src/lib/api.ts` | `settingsApi.updateSettings(Partial<UserSettings>)` already works |
| `frontend/src/components/Sidebar.tsx` | No changes |

---

## 7. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Onboarding trigger | `onboarding_complete` boolean on UserProfile | Explicit and reliable. Checking `preferred_name is null` would be fragile. |
| Where to show onboarding | Replace Welcome page at `/` | Already the post-registration landing. Login goes to `/home` so returning users skip it. |
| Name save timing | Immediate on card 1 "Next" | If user abandons mid-flow, name is still captured. PUT /api/settings auto-creates profile. |
| After onboarding | Navigate to `/home` | User sees "Add a deck to begin" placeholder, natural next step. |
| Existing user handling | Migration backfills `onboarding_complete=true` | Creates missing profiles too, so `profile is None` means brand-new user post-deployment. |
| Card navigation | Forward/back with dot indicators | Simple, familiar pattern. No skip button — flow is short enough (4 cards). |
| Animation | framer-motion horizontal slides | Consistent with existing app patterns (ConfidenceRating, FloatingWordPill). |
