# Mobile Android + Multi-Language Support -- Requirements Document

## Feature Overview

This milestone delivers two interconnected initiatives that expand Laoshi Coach from a Mandarin-only web app to a multi-language, multi-platform learning tool:

1. **Multi-Language Backend + Web Frontend (Phase 1)**: Per-deck language tagging (`ZH` or `JP`), renaming `Word.pinyin` to `Word.reading` for language generality, language-aware AI prompts with model routing (DeepSeek for Chinese, Claude 3.5 Sonnet via LiteLLM for Japanese), configurable sample deck env vars, and a web frontend language selector in deck creation.

2. **Android Mobile App (Phase 2)**: A native Android app (Kotlin + Jetpack Compose) sharing the same backend API, providing all core functionality (auth, home, practice, library, progress, settings, onboarding) with mobile-native UX patterns.

**What already exists:**
- React web frontend at `frontend/` with full deck management, AI practice sessions, report card, settings, and onboarding.
- Flask backend at `backend/` with JWT auth, deck/word CRUD, AI practice runner (DeepSeek feedback + Gemini orchestrator), report card service, sample deck seeding.
- `Word` model with `pinyin` column (Chinese-specific naming).
- `Deck` model with no language field (implicitly Chinese-only).
- Hardcoded Mandarin Chinese references in all AI prompts and prompt builders.
- Single sample deck CSV (`swe_vocab_list.csv`) seeded for all new users.
- JWT auth via cookies for web (access token in header, refresh token in cookie).

**What this milestone delivers:**
- Decks tagged with `language` (`'ZH'` or `'JP'`), enabling per-deck language context.
- Generic `reading` column replacing `pinyin` on the `Word` model.
- Language-aware AI prompts using a `LANGUAGE_CONFIG` dictionary.
- Model routing: DeepSeek feedback for ZH, Claude 3.5 Sonnet (via LiteLLM) feedback for JP, Gemini Flash orchestrator for both.
- Per-language sample deck seeding via env vars (`ZH_SAMPLE_DECK_FILE`, `JP_SAMPLE_DECK_FILE`).
- Web frontend language selector when creating decks, dynamic column headers, reading field rename.
- Native Android app with all screens, matching the web app's visual design system.
- Backend mobile auth modifications (JWT in JSON body for mobile clients).

---

## User Stories

### Phase 1: Multi-Language Backend + Web Frontend

#### US-01: Create a deck with a specific language
**As a** learner, **I want** to select a language (Chinese or Japanese) when creating a new deck **so that** the app knows which language to use for AI feedback and display labels.

**Acceptance Criteria:**
- The "Create Deck" modal includes a language selector (ZH / JP radio buttons or toggle).
- Language defaults to `ZH` if not specified.
- The selected language is saved to the `Deck.language` column.
- Existing decks are automatically set to `ZH` via migration.
- The deck card in the library shows a small language badge (e.g., "ZH" or "JP").
- `POST /api/decks` accepts an optional `language` field (validated against `SUPPORTED_LANGUAGES`).
- Combining decks rejects if source decks have different languages.

#### US-02: Language-generic reading field
**As a** learner, **I want** the reading field (pinyin for Chinese, furigana for Japanese) to display with the correct label for my deck's language **so that** the UI is contextually appropriate.

**Acceptance Criteria:**
- The `Word` model uses a `reading` column (renamed from `pinyin`).
- The web table header shows "Pinyin" for ZH decks and "Furigana" for JP decks.
- The edit word modal labels the reading field dynamically based on deck language.
- The floating word pill in practice displays `word.reading` (not `word.pinyin`).
- The practice panel message area uses `reading` throughout.
- CSV upload accepts both `Pinyin` and `Reading` column headers for backward compatibility.
- API responses return `reading` instead of `pinyin`. API requests accept both `reading` and `pinyin` (backward compat).

#### US-03: Language-aware AI feedback
**As a** learner, **I want** the AI coach to evaluate my sentences using the appropriate language model and criteria **so that** I receive accurate feedback for whichever language I am practicing.

**Acceptance Criteria:**
- Practicing a ZH deck uses DeepSeek for feedback evaluation (unchanged behavior).
- Practicing a JP deck uses Claude 3.5 Sonnet (via LiteLLM) for feedback evaluation.
- The orchestrator (Gemini Flash) adapts its prompts to the deck's language (e.g., "Japanese teacher" instead of "Mandarin Chinese teacher").
- Feedback criteria adapt: ZH focuses on "word order, particles, verb aspect, measure words"; JP focuses on "particle usage (wa/ga/wo/ni), verb conjugation, keigo levels, word order (SOV)".
- Feedback language adapts: ZH returns feedback in "simple Chinese"; JP returns feedback in "simple Japanese".
- If `ANTHROPIC_API_KEY` is not set, JP practice gracefully fails with a clear error message (not a crash).
- The teacher persona remains "Laoshi" for all languages.

#### US-04: Language-aware report card
**As a** learner, **I want** my report card to reflect the language of my practice sessions **so that** score descriptions and teacher feedback are contextually appropriate.

**Acceptance Criteria:**
- Report card score descriptions adapt to the primary language of recent sessions.
- The report card agent prompt references the correct language context.
- The report card functions correctly when a user has practiced both ZH and JP decks.

#### US-05: Per-language sample decks
**As a** new user, **I want** to receive sample decks for available languages **so that** I can start practicing immediately in both Chinese and Japanese.

**Acceptance Criteria:**
- On registration, the system seeds a ZH sample deck using `ZH_SAMPLE_DECK_FILE` (default: `swe_vocab_list.csv`).
- On registration, the system attempts to seed a JP sample deck using `JP_SAMPLE_DECK_FILE` (default: `jp_sample_vocab_list.csv`).
- If the JP CSV file does not exist, JP seeding is silently skipped (no error).
- Sample decks are created with the correct `language` field.
- The CSV parser accepts both `Pinyin` and `Reading` column headers.
- Each language has its own deck name, description, and Laoshi message constants.

### Phase 2: Android Mobile App

#### US-06: Mobile authentication
**As a** learner, **I want** to register, log in, and stay authenticated on my Android phone **so that** I can practice on the go.

**Acceptance Criteria:**
- Login screen with username and password fields, validation matching web (username 3-80 chars, password 8+ with uppercase/lowercase/digit).
- Register screen with username, email, and password fields.
- JWT access token stored in EncryptedSharedPreferences.
- OAuth2 client credentials mechanism: mobile app sends `client_id` + `client_secret` with login request; backend validates client identity and returns refresh token in response body for mobile clients only.
- Web frontend also uses client credentials: sends `client_id` (no secret -- public client) with login request; refresh token remains in HttpOnly cookie only.
- Backend validates `client_id` (and `client_secret` for confidential clients) before issuing tokens.
- Automatic token refresh on 401 via OkHttp Authenticator (coroutine-safe, no `runBlocking`).
- Auth endpoints have explicit rate limiting (stricter for mobile: 10 req/min login, 30 req/min refresh).
- Logout clears tokens and navigates to login screen.

#### US-07: Mobile home screen
**As a** learner, **I want** to see my decks and their practice status on my phone **so that** I can choose which deck to practice.

**Acceptance Criteria:**
- Deck list displays all user decks with growth icon, recency color, progress bar, word count, and Laoshi message preview.
- Tapping a deck navigates to a deck detail screen with progress ring, stats, and "Start Practice" button.
- Tablet layout: two-pane master-detail (deck list + detail side by side).
- Phone layout: single-pane with navigation between list and detail.
- Deck recency colors: sage (<48h), amber (48-120h), coral (>120h), neutral (never).
- Growth icons: sprout (<25%), leaf (25-74%), flower (75%+).

#### US-08: Mobile practice session
**As a** learner, **I want** to complete full practice sessions on my phone **so that** I can practice Mandarin or Japanese anywhere.

**Acceptance Criteria:**
- Full chat interface with floating word pill (tappable to expand), message list, text input, and send button.
- Feedback card displays grammar/usage/naturalness scores with color coding.
- Confidence rating (0-5) buttons appear inline after "Next Word".
- Session summary displays after completion with word results and action buttons.
- Practice state machine: AI_TYPING -> WAITING_FOR_USER -> FEEDBACK_GIVEN -> AWAITING_RATING -> TRANSITIONING -> (loop or SESSION_COMPLETE).
- Session state persisted via SavedStateHandle + DataStore (survives process death).
- Both ZH and JP decks work with appropriate model routing.

#### US-09: Mobile library
**As a** learner, **I want** to manage my vocabulary decks and words on my phone **so that** I can add, edit, and organize my study materials.

**Acceptance Criteria:**
- Deck list with cards showing language badge, word count, mastery percentage.
- Create deck dialog with name, description, and language selector (ZH/JP).
- CSV import via Android file picker.
- Deck words screen: paginated list with search, sortable by word/reading/meaning.
- Edit and delete word functionality.
- Column header adapts: "Pinyin" for ZH, "Furigana" for JP.

#### US-10: Mobile progress (report card)
**As a** learner, **I want** to view my progress and report card on my phone **so that** I can track my learning on the go.

**Acceptance Criteria:**
- Top metrics cards: time practiced, sessions, words.
- 7-day stacked bar chart (Vico library).
- Score breakdown with descriptive text.
- Teacher feedback section.
- Pull-to-refresh triggers feedback regeneration.

#### US-11: Mobile settings
**As a** learner, **I want** to manage my settings on my phone **so that** I can customize my experience.

**Acceptance Criteria:**
- Preferred name (editable).
- Words per session (slider or stepper).
- Logout button.
- Delete account with confirmation dialog.
- No BYOK (API key management not available on mobile).

#### US-12: Mobile onboarding
**As a** new learner on mobile, **I want** a guided onboarding experience **so that** I understand how Laoshi works before starting.

**Acceptance Criteria:**
- 5-step wizard using `HorizontalPager`:
  1. NameCard: "What should Laoshi call you?" (name input).
  2. MeetLaoshiCard: Introduction to Laoshi persona.
  3. DecksCard: Explanation of deck concept.
  4. PracticeCard: Explanation of practice flow.
  5. ReadyCard: "Get Started" button, sets `onboarding_complete=true`.
- Onboarding only shows if `onboarding_complete` is false.
- After completion, navigates to home screen.

---

---

## Non-Functional Requirements

### NFR-01: Auth endpoint rate limiting
- `POST /api/token` (login): Max 10 requests/minute per IP.
- `POST /api/token/refresh`: Max 30 requests/minute per IP.
- `POST /api/users` (register): Max 5 requests/minute per IP.
- Rate limits enforced by Flask-Limiter (already in stack).

### NFR-02: API versioning
- All endpoints are accessible via `/api/v1/` prefix (alias for `/api/`).
- Mobile app uses `/api/v1/` paths exclusively.
- Web frontend continues using `/api/` (both work identically).
- Future breaking changes will use `/api/v2/` without affecting mobile clients on v1.

### NFR-03: Mobile client-side caching
- Android repositories implement in-memory caching with TTL for read-heavy endpoints.
- Deck list: 30-second cache TTL.
- Report card: 60-second cache TTL.
- Cache invalidated on user-initiated actions (pull-to-refresh, deck creation, practice completion).

---

## Out of Scope

- **iOS app**: Only Android is covered in this milestone.
- **BYOK on mobile**: API key management is intentionally omitted from the mobile app.
- **Language step in onboarding**: Users pick language per-deck, not during onboarding.
- **Additional languages beyond ZH and JP**: The `LANGUAGE_CONFIG` is extensible, but only Chinese and Japanese are implemented now.
- **Offline mode**: The mobile app requires an internet connection for all operations.
- **Push notifications**: Not included in this milestone.
- **Dark mode**: Only light theme is implemented (matching web).
- **Voice input**: Text input only for practice sessions.
- **Shared deck library / community decks**: The per-deck `language` tag is foundational, but the shared library feature is deferred.

---

## Open Questions

1. **JP sample deck content**: The `jp_sample_vocab_list.csv` file will be provided later. The system should gracefully skip JP seeding if the file is missing. What topic should the JP sample deck cover? (Assumed: general beginner Japanese vocabulary.)
2. **LiteLLM deployment**: Should LiteLLM run as a sidecar proxy (localhost:4000) or be invoked directly via the `litellm` Python package's `acompletion()`? (Assumed: direct `litellm.acompletion()` since LiteLLM is already a dependency via mem0.)
3. **Android minimum API level**: Assumed API 26 (Android 8.0). Confirm target.
4. **Backend URL for mobile**: How does the mobile app discover the backend URL? (Assumed: build-time constant in `BuildConfig`, configurable per build variant.)
5. **App signing and distribution**: How will the Android app be distributed initially? (Assumed: manual APK / internal testing track, not Google Play Store for this milestone.)
