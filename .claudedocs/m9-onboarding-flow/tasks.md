# Milestone 9: Onboarding Flow -- Task Breakdown

## Task Overview

**Total tasks**: 14 tasks (T-9.1 to T-9.14) across 5 phases
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be parallelised where noted.

---

## Prerequisites

Before starting any tasks:

1. Ensure M8 UI changes are complete and the dev server starts without errors.
2. Read the design document: `.claudedocs/m9-onboarding-flow/design.md`.
3. Read the requirements document: `.claudedocs/m9-onboarding-flow/requirements.md`.

---

## Phase 1: Backend Model & API

---

### T-9.1: Add `onboarding_complete` column to UserProfile model

**Description**: Add the new boolean column to the UserProfile model and update serialization methods.

**Files affected**:
- `backend/models.py`

**Changes**:

1. In `UserProfile` class (after `last_practice_date` on line 443), add:
```python
onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)
```

2. In `UserProfile.format_settings()` (line 449), add to the return dict:
```python
'onboarding_complete': self.onboarding_complete,
```

3. In `User.format_data()` (line 354), add to the self-viewer return dict:
```python
'onboarding_complete': (self.profile.onboarding_complete if self.profile else False),
```

**Acceptance criteria**:
- `User.format_data(self_viewer)` returns `onboarding_complete: false` when profile is None (new user).
- `User.format_data(self_viewer)` returns the actual `onboarding_complete` value when profile exists.
- `UserProfile.format_settings()` includes `onboarding_complete`.

**Dependencies**: None.

---

### T-9.2: Accept `onboarding_complete` in PUT /api/settings

**Description**: Allow the settings endpoint to update the onboarding flag.

**Files affected**:
- `backend/settings_resources.py`

**Changes**:

1. In `UserSettingsResource.put()` (after the `words_per_session` handling around line 54), add:
```python
if 'onboarding_complete' in data:
    if not isinstance(data['onboarding_complete'], bool):
        return {"error": "onboarding_complete must be a boolean"}, 400
    profile.onboarding_complete = data['onboarding_complete']
```

2. In `UserSettingsResource.get()` (line 16-22), add `'onboarding_complete': False` to the no-profile fallback response.

**Acceptance criteria**:
- `PUT /api/settings { "onboarding_complete": true }` sets the flag on the profile.
- `PUT /api/settings { "onboarding_complete": "yes" }` returns 400 validation error.
- `GET /api/settings` returns `onboarding_complete` for both existing and missing profiles.

**Dependencies**: T-9.1.

---

### T-9.3: Create Alembic migration

**Description**: Add the `onboarding_complete` column and backfill existing users.

**Files affected**:
- `backend/migrations/versions/<hash>_add_onboarding_complete_to_user_profile.py` (new)

**Changes**:

Run `flask db migrate -m "add_onboarding_complete_to_user_profile"` then manually edit the migration:

**upgrade():**
```python
op.add_column('user_profile',
    sa.Column('onboarding_complete', sa.Boolean(), nullable=False, server_default=sa.text('false'))
)
# Mark all existing profiles as onboarding-complete
op.execute("UPDATE user_profile SET onboarding_complete = true")
# Create profiles for existing users without one
op.execute("""
    INSERT INTO user_profile (user_id, onboarding_complete, deepseek_key_version, gemini_key_version, current_streak, created_ds, updated_ds)
    SELECT u.id, true, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    FROM "user" u
    LEFT JOIN user_profile up ON u.id = up.user_id
    WHERE up.id IS NULL
""")
```

**downgrade():**
```python
op.drop_column('user_profile', 'onboarding_complete')
```

**Acceptance criteria**:
- `flask db upgrade` runs without errors.
- All existing `user_profile` rows have `onboarding_complete = true`.
- All existing users have a `user_profile` row after migration.
- New `UserProfile` rows created by the app default to `onboarding_complete = false`.

**Dependencies**: T-9.1.

### T-9.4: Run migration

**Description**: Apply the migration to the database.

**Command**: `flask db upgrade`

**Acceptance criteria**:
- Migration applies successfully.
- `SELECT onboarding_complete FROM user_profile` returns `true` for all existing rows.

**Dependencies**: T-9.3.

---

## Phase 2: Frontend Types & Auth Context

Can be parallelised with Phase 1 migration step.

---

### T-9.5: Update TypeScript types

**Description**: Add `onboarding_complete` to frontend type definitions.

**Files affected**:
- `frontend/src/types/api.ts`

**Changes**:

1. In `User` interface (line 22), add:
```typescript
onboarding_complete?: boolean
```

2. In `UserSettings` interface (line 180), add:
```typescript
onboarding_complete?: boolean
```

**Acceptance criteria**:
- No TypeScript errors from the type changes.

**Dependencies**: None (types match the API contract from T-9.1/T-9.2).

---

### T-9.6: Update AuthContext

**Description**: Add `onboarding_complete` to the User interface and add an `updateUser` method for local state updates.

**Files affected**:
- `frontend/src/contexts/AuthContext.tsx`

**Changes**:

1. Add `onboarding_complete: boolean` to the local `User` interface (line 5).

2. Add `updateUser` to `AuthContextType` interface:
```typescript
updateUser: (updates: Partial<User>) => void
```

3. Implement `updateUser` inside `AuthProvider`:
```typescript
const updateUser = useCallback((updates: Partial<User>) => {
  setUser(prev => prev ? { ...prev, ...updates } : null)
}, [])
```

4. Add `updateUser` to the context provider value object.

**Acceptance criteria**:
- `useAuth()` returns `updateUser` function.
- Calling `updateUser({ onboarding_complete: true })` updates `user.onboarding_complete` without re-fetching `/api/me`.
- Existing `login`, `logout`, and silent refresh flows continue to work.

**Dependencies**: T-9.5.

---

## Phase 3: Onboarding UI Components

---

### T-9.7: Create StepIndicator component

**Description**: Create the dot progress indicator shown below the wizard cards.

**Files created**:
- `frontend/src/pages/onboarding/StepIndicator.tsx` (new)

**Props**:
```typescript
interface StepIndicatorProps {
  currentStep: number
  totalSteps: number
}
```

**Styling**:
- Container: `flex justify-center gap-2 mt-6`
- Active dot: `w-6 h-2 rounded-full bg-sage transition-all duration-300`
- Inactive dot: `w-2 h-2 rounded-full bg-warm-gray transition-all duration-300`

**Acceptance criteria**:
- Renders correct number of dots.
- Active dot is wider and sage-colored.
- Dot width animates on step change.

**Dependencies**: None (can be built independently).

---

### T-9.8: Create card components (NameCard, MeetLaoshiCard, DecksCard, PracticeCard)

**Description**: Create all 4 presentational card components.

**Files created**:
- `frontend/src/pages/onboarding/NameCard.tsx` (new)
- `frontend/src/pages/onboarding/MeetLaoshiCard.tsx` (new)
- `frontend/src/pages/onboarding/DecksCard.tsx` (new)
- `frontend/src/pages/onboarding/PracticeCard.tsx` (new)

**NameCard props**:
```typescript
{ name: string, onNameChange: (name: string) => void }
```

**Card contents** (see requirements.md for exact copy):
- **NameCard**: Wave emoji, heading, subtitle, text input (auto-focus, centered, maxLength 80), helper text
- **MeetLaoshiCard**: laoshi-logo.png (w-24 h-24 rounded-2xl), heading, description
- **DecksCard**: Library icon in sage-tint circle, heading, description with inline icon
- **PracticeCard**: Visual element, heading, 3 text blocks with bold labels

**Styling** (all cards):
- Content centered: `text-center` (except PracticeCard bullet text which is `text-left`)
- Headings: `text-2xl font-bold text-warm-black mb-2`
- Body text: `text-warm-muted leading-relaxed`

**Acceptance criteria**:
- Each card renders its content correctly.
- NameCard input updates the parent's `name` state via `onNameChange`.
- MeetLaoshiCard displays the Laoshi logo image.
- DecksCard includes the inline Library SVG icon.
- All cards follow the warm design language (sage, warm-muted, etc.).

**Dependencies**: None (can be built independently).

---

### T-9.9: Create OnboardingWizard orchestrator

**Description**: Create the main wizard component that manages step navigation, animations, and API calls.

**Files created**:
- `frontend/src/pages/onboarding/OnboardingWizard.tsx` (new)

**State**:
- `currentStep: number` (0-3)
- `preferredName: string`
- `isSaving: boolean`
- `direction: number` (1 forward, -1 back)

**Layout**:
- Background: `min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4`
- Card: `bg-white rounded-3xl shadow-lg p-8 max-w-md w-full overflow-hidden`

**Animation**:
- framer-motion `AnimatePresence` with `mode="wait"` and `custom={direction}`
- Slide variants: 300px horizontal offset, 300ms, easeInOut

**API calls**:
- Card 1 "Next": `settingsApi.updateSettings({ preferred_name })` + `updateUser()`
- Card 4 "Let's get started!": `settingsApi.updateSettings({ onboarding_complete: true })` + `updateUser()` + `navigate('/home')`

**Navigation**:
- Back button (cards 2-4): `text-warm-muted hover:text-warm-black`
- Next button (cards 1-3): `bg-sage text-white rounded-full px-8 py-3`
- "Let's get started!" (card 4): same sage style
- Disabled during save: `disabled:opacity-50`

**Acceptance criteria**:
- Steps advance and go back correctly.
- Animation direction matches navigation direction.
- Card 1 "Next" saves name via API and updates AuthContext.
- Card 4 completes onboarding via API, updates AuthContext, and navigates to /home.
- API errors are handled gracefully (still navigates on card 4 failure).

**Dependencies**: T-9.6, T-9.7, T-9.8.

---

### T-9.10: Update Welcome.tsx

**Description**: Replace the static Welcome page with conditional rendering based on onboarding status.

**Files affected**:
- `frontend/src/pages/Welcome.tsx`

**Changes**:

Replace the entire component with:
```typescript
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import OnboardingWizard from './onboarding/OnboardingWizard'

const Welcome = () => {
  const { user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (user?.onboarding_complete) {
      navigate('/home', { replace: true })
    }
  }, [user, navigate])

  if (user?.onboarding_complete) return null

  return <OnboardingWizard />
}

export default Welcome
```

**Acceptance criteria**:
- New users see the OnboardingWizard at `/`.
- Returning users (onboarding_complete=true) are redirected to `/home`.
- No flash of wizard content before redirect for returning users.

**Dependencies**: T-9.6, T-9.9.

---

## Phase 4: Build Verification

---

### T-9.11: TypeScript build check

**Description**: Verify no type errors across the frontend.

**Command**: `npx tsc --noEmit` in `frontend/`

**Acceptance criteria**:
- Zero TypeScript errors.

**Dependencies**: T-9.10.

---

### T-9.12: Vite build check

**Description**: Verify the production build succeeds.

**Command**: `npx vite build` in `frontend/`

**Acceptance criteria**:
- Build completes without errors.

**Dependencies**: T-9.11.

---

## Phase 5: Manual E2E Testing

---

### T-9.13: Test new user onboarding flow

**Description**: Register a new user and verify the complete onboarding experience.

**Test steps**:
1. Register a new user via the registration form.
2. Verify auto-login redirects to `/` and the OnboardingWizard appears.
3. Card 1: enter a name, click "Next". Verify name is saved via `GET /api/settings`.
4. Card 2: verify Laoshi logo and description. Click "Next".
5. Card 3: verify deck explanation and Library icon. Click "Next".
6. Card 4: verify practice overview. Click "Let's get started!".
7. Verify navigation to `/home` with "Add a deck to begin" placeholder.
8. Verify `GET /api/me` returns `onboarding_complete: true`.
9. Navigate to `/` directly. Verify redirect to `/home`.

**Dependencies**: All previous tasks.

---

### T-9.14: Test existing user bypass

**Description**: Verify existing users never see the onboarding wizard.

**Test steps**:
1. Log in as an existing user (e.g. bengregory).
2. Verify landing on `/home` (not `/` or onboarding).
3. Navigate directly to `/`. Verify redirect to `/home`.
4. Verify `GET /api/me` returns `onboarding_complete: true`.

**Dependencies**: T-9.4 (migration applied).

---

## Dependency Graph

```
T-9.1 (model) ──┬──> T-9.2 (API) ──> T-9.3 (migration) ──> T-9.4 (run migration)
                │
T-9.5 (types) ──┴──> T-9.6 (AuthContext)
                                        │
T-9.7 (StepIndicator) ─────────────────┤
T-9.8 (cards) ─────────────────────────┤
                                        │
                                        ├──> T-9.9 (wizard) ──> T-9.10 (Welcome.tsx)
                                                                       │
                                                                       ├──> T-9.11 (tsc)
                                                                       ├──> T-9.12 (build)
                                                                       ├──> T-9.13 (E2E new user)
                                                                       └──> T-9.14 (E2E existing user)
```
