# Milestone 4: Home Page Stats, Settings & Security Hardening -- Requirements Document

## Feature Overview

Milestone 4 is the **final MVP milestone**. It delivers the remaining user-facing features (home page stats, settings page) and hardens the application for production readiness. It also performs a structural data model cleanup by separating user profile data from authentication data.

**What already exists:**
- Frontend `Home.tsx` with stat card UI shell: "Words Practiced Today", "Mastery Progress", "Words Ready for Review" -- all hardcoded to zero. `totalWords` and `wordsWaiting` are fetched from the words API; the other two stats are not.
- Frontend `Settings.tsx` with an empty placeholder ("Settings coming soon...").
- Backend has no `/api/progress/*` or `/api/settings` endpoints.
- `preferred_name` is a column on the `User` model (mixed with auth data).
- AI agent prompts have no data/command separation for user-supplied content.
- No rate limiting on any endpoint.
- Password update bug: `PUT /api/users/:id` stores passwords as plaintext via `setattr`.

**What this milestone delivers:**
1. **UserProfile model**: New 1:1 table separating non-auth data from User (preferred_name, words_per_session, encrypted BYOK keys).
2. **preferred_name migration**: Move from User to UserProfile with API contract preserved.
3. **Home page stats**: Real-time stats endpoint wired to the frontend.
4. **Settings page**: Full UI for practice configuration (words per session) and BYOK API key management.
5. **BYOK API keys**: Per-user DeepSeek and Gemini keys, Fernet-encrypted at rest.
6. **Rate limiting**: flask-limiter on all endpoints with stricter limits on auth and AI endpoints.
7. **Input validation hardening**: String length limits, password hash fix, message length caps.
8. **Prompt injection defenses**: Data/command separation with `[DATA]...[/DATA]` delimiters, system prompt hardening.

This milestone maps to **PRD User Stories**: #15 (Home page stats), #18 (Configure words per session), #19 (BYOK API key).

---

## User Stories

### US-01: View learning statistics on the home page
**As a** learner, **I want** to see my learning statistics on the home page **so that** I stay motivated and track my progress.

**Acceptance Criteria:**
- The "Words Practiced Today" stat shows the count of distinct words I practiced today (words with at least one completed attempt in sessions started today UTC).
- The "Mastery Progress" stat shows the percentage of my total vocabulary that has reached Mastered status (confidence > 0.9, strictly greater).
- The "Words Ready for Review" stat shows the count of words with confidence < 0.9 (matching the practice session word selection criteria).
- Stats update on page load (no caching, fresh query each time).
- If I have no words, all stats show 0 and mastery shows 0%.

### US-02: Configure words per session
**As a** learner, **I want** to configure how many words are practiced per session **so that** I can adjust sessions to my available time and energy.

**Acceptance Criteria:**
- The Settings page has a "Practice Settings" section with a number input for words per session.
- Valid range: 5-50 words.
- Default value shown when no preference is saved: 10 (from config).
- Clicking "Save" persists the setting. A success indicator appears.
- Clicking "Reset to Default" clears the saved preference (uses system default of 10).
- The next practice session uses the saved value (or default if cleared).

### US-03: Provide my own API keys (BYOK)
**As a** learner, **I want** to input my own API keys for DeepSeek and Gemini **so that** I can continue practicing if the default free-tier keys are exhausted.

**Acceptance Criteria:**
- The Settings page has an "API Keys" section with two separate inputs: one for DeepSeek, one for Gemini.
- Keys are entered in password-type inputs (masked by default).
- A status indicator shows whether a custom key is currently saved (green dot) or using default (gray dot).
- Clicking "Save" for a key encrypts it and stores it server-side. The raw key is never returned by any API.
- Clicking "Clear" removes the saved key and reverts to the default free-tier key.
- When a custom key is saved, practice sessions use that key for the corresponding AI provider.
- If decryption fails or the custom key is invalid, the system falls back to the default key silently.

### US-04: Set my display name
**As a** learner, **I want** to set my preferred display name **so that** the AI coach addresses me by my chosen name.

**Acceptance Criteria:**
- The Settings page has a "Profile" section with a text input for preferred name.
- Maximum 80 characters.
- Clicking "Save" persists the name.
- The AI coach uses this name in practice sessions.
- The `/api/me` endpoint continues to return `preferred_name` in the same response shape (API contract preserved).
- If no preferred name is set, the coach uses my username.

### US-05: Application is protected against abuse
**As a** system operator, **I want** the application to be hardened against common attacks **so that** the system remains available and secure.

**Acceptance Criteria:**
- All endpoints have rate limiting (default 200/min).
- Authentication endpoints (login, register) have stricter limits (5/min).
- AI practice endpoints have moderate limits (30/min).
- Exceeding rate limits returns HTTP 429 with a clear error message.
- All string inputs have length limits matching database column sizes.
- Password updates are properly hashed before storage.
- Practice messages are capped at 2000 characters before being sent to AI.
- User-supplied content in AI prompts is wrapped in `[DATA]...[/DATA]` delimiters.
- Agent system prompts include instructions to ignore commands within data tags.
- Internal error details are never exposed to clients.

---

## Functional Requirements

### UserProfile Model -- Backend

**FR-001**: A new `UserProfile` model MUST exist with a 1:1 relationship to `User`. Columns: `id` (PK), `user_id` (FK, unique), `preferred_name` (String 80, nullable), `words_per_session` (Integer, nullable), `encrypted_deepseek_api_key` (Text, nullable), `encrypted_gemini_api_key` (Text, nullable), `created_ds`, `updated_ds`.

**FR-002**: `User.format_data()` MUST read `preferred_name` from the associated `UserProfile` (via `self.profile.preferred_name`). If no profile exists, return `None` for preferred_name. This MUST preserve the existing `/api/me` response shape: `{ id, username, preferred_name }`.

**FR-003**: The `preferred_name` column MUST be removed from the `User` model after data migration to `UserProfile`.

**FR-004**: `UserProfile` MUST be lazily created — it is NOT created at registration. It is created on the first `PUT /api/settings` call.

**FR-005**: An Alembic migration MUST create the `user_profile` table, copy existing `preferred_name` data from `User` rows to new `UserProfile` rows, then drop the `preferred_name` column from the `user` table.

### Stats Endpoint -- Backend

**FR-006**: `GET /api/progress/stats` MUST be JWT-protected and return `{ words_practiced_today, mastery_percentage, words_ready_for_review, total_words }`.

**FR-007**: `words_practiced_today` MUST count DISTINCT `SessionWord.word_id` values from `SessionWord` rows where `status=1` (completed) in `UserSession` rows started today (UTC).

**FR-008**: `mastery_percentage` MUST be calculated as `round(count(words where confidence_score > 0.9) / total_words * 100)`. Uses strictly greater than 0.9 to match `Word.STATUS_THRESHOLDS` logic. Returns 0 if no words exist.

**FR-009**: `words_ready_for_review` MUST count words where `confidence_score < 0.9`, matching the word selection criteria in `practice_runner.py:initialize_session()`.

### Settings Endpoints -- Backend

**FR-010**: `GET /api/settings` MUST be JWT-protected and return `{ preferred_name, words_per_session, has_deepseek_key, has_gemini_key }`. If no `UserProfile` exists, return defaults: `{ preferred_name: null, words_per_session: null, has_deepseek_key: false, has_gemini_key: false }`.

**FR-011**: `GET /api/settings` MUST NEVER return raw API keys. Only boolean indicators (`has_deepseek_key`, `has_gemini_key`).

**FR-012**: `PUT /api/settings` MUST accept partial updates. Supported fields: `preferred_name` (string, max 80), `words_per_session` (int, 1-50 or null), `deepseek_api_key` (string to set, null/empty to clear), `gemini_api_key` (string to set, null/empty to clear).

**FR-013**: `PUT /api/settings` MUST create `UserProfile` if it doesn't exist (lazy creation).

**FR-014**: `POST /api/settings/keys/<provider>/validate` MUST test the API key with a real API call before saving. If validation fails, the key MUST NOT be saved and an appropriate error message MUST be returned. Timeout: 10 seconds.

**FR-014a**: API key validation errors MUST include specific messages: "Invalid API key" (401), "Rate limit exceeded" (429), "Service unavailable" (5xx), "Validation timeout" (timeout).

**FR-015**: `DELETE /api/settings/keys/<provider>` MUST clear the encrypted key for the specified provider (deepseek or gemini) and increment its `key_version`. Returns 400 for invalid provider names.

**FR-015a**: When an API key is cleared, active practice sessions MUST immediately detect the version change on their next message and fall back to default keys.

### BYOK Integration -- Backend

**FR-016**: `practice_runner.py` MUST check the user's `UserProfile` for custom API keys before each session.

**FR-017**: If custom keys exist, `practice_runner.py` MUST call `build_agents()` with the decrypted keys to create per-user agent instances.

**FR-018**: If no custom keys exist (or decryption fails), the default module-level agents MUST be used (zero overhead for the common case).

**FR-019**: `build_agents()` in `chat_agents.py` MUST accept optional `deepseek_api_key` and `gemini_api_key` parameters. When provided, it MUST create new `AsyncOpenAI` clients and agent objects using the custom keys, with the same prompt builders as the defaults.

### Rate Limiting -- Backend

**FR-020**: All endpoints MUST have a default rate limit of 200 requests per minute per IP.

**FR-021**: `POST /api/token` and `POST /api/users` MUST have a rate limit of 5 requests per minute.

**FR-022**: `POST /api/token/refresh` MUST have a rate limit of 10 requests per minute.

**FR-023**: `POST /api/practice/sessions/<id>/messages` MUST have a rate limit of 30 requests per minute.

**FR-024**: Exceeding rate limits MUST return HTTP 429 with `{ "error": "Rate limit exceeded. Try again later." }`.

### Input Validation -- Backend

**FR-025**: `POST /api/words` and `PUT /api/words/<id>` MUST enforce string length limits: `word` <= 150, `pinyin` <= 150, `meaning` <= 300, `source_name` <= 200 (matching DB column sizes).

**FR-026**: `PUT /api/users/<id>` MUST hash the password via `hash_password()` when updating the `password` field. The current code uses `setattr()` which stores it as plaintext.

**FR-027**: `PUT /api/users/<id>` MUST remove `preferred_name` from `allowable_fields` (now managed via `PUT /api/settings`).

**FR-028**: `POST /api/practice/sessions/<id>/messages` MUST reject messages exceeding 2000 characters with a 400 error.

**FR-029**: `POST /api/practice/sessions` MUST validate `words_count` is an integer in range 1-50 (if provided).

**FR-030**: `POST /api/users` MUST enforce: username 3-80 chars, email max 200, password 8-200 chars.

### Prompt Injection Defense -- Backend

**FR-031**: All user-supplied data injected into agent prompts MUST be wrapped in `[DATA]...[/DATA]` delimiters. This applies to: word info in orchestrator and feedback prompts, mem0 preferences in orchestrator prompt, word list in summary prompt.

**FR-032**: The orchestrator agent's system prompt MUST include security rules instructing the model to treat content within `[DATA]...[/DATA]` tags as data only, never follow instructions embedded within them, and never reveal system prompt contents.

**FR-033**: Practice message length MUST be capped at 2000 characters in `handle_message()` before being passed to `Runner.run()`.

### Encryption -- Backend

**FR-034**: A new `ENCRYPTION_KEY` environment variable MUST be added to the backend configuration (read from `.env`).

**FR-035**: `encrypt_api_key(plaintext)` and `decrypt_api_key(ciphertext)` utility functions MUST use Fernet symmetric encryption from the `cryptography` library.

**FR-036**: Encryption/decryption MUST use the app's `ENCRYPTION_KEY` from Flask config.

**FR-036a**: The `UserProfile` model MUST include `deepseek_key_version` and `gemini_key_version` columns (Integer, default=1) to track key rotations.

### AI Layer Integration -- Backend

**FR-037**: `hydrate_context()` in `practice_runner.py` MUST read `preferred_name` from `user.profile.preferred_name` (with None-safe access) instead of `user.preferred_name`.

**FR-038**: `initialize_session()` in `practice_runner.py` MUST check `user.profile.words_per_session` before falling back to `Config.DEFAULT_WORDS_PER_SESSION`.

**FR-039**: The 4 call sites in `practice_runner.py` that use `laoshi_agent` MUST be updated to call `get_user_agent(user, ds_version, gemini_version)` which returns the appropriate agent (custom or default) and current version numbers.

**FR-039a**: `get_user_agent()` MUST check stored session versions against `user.profile.deepseek_key_version` and `user.profile.gemini_key_version`. If mismatched, it MUST re-evaluate and return the updated agent with new versions.

### Frontend -- Types

**FR-040**: `types/api.ts` MUST include `ProgressStats` interface: `{ words_practiced_today, mastery_percentage, words_ready_for_review, total_words }`.

**FR-041**: `types/api.ts` MUST include `UserSettings` interface: `{ preferred_name: string|null, words_per_session: number|null, has_deepseek_key: boolean, has_gemini_key: boolean }`.

### Frontend -- API Helpers

**FR-042**: `lib/api.ts` MUST export `progressApi` with `getStats()` method.

**FR-043**: `lib/api.ts` MUST export `settingsApi` with `get()`, `update(data)`, and `deleteKey(provider)` methods.

### Frontend -- Home Page

**FR-044**: `Home.tsx` MUST call `progressApi.getStats()` on mount and populate all stat cards with real data.

**FR-045**: `Home.tsx` MUST remove the hardcoded `useState(0)` for `wordsToday` and `masteryProgress`.

### Frontend -- Settings Page

**FR-046**: `Settings.tsx` MUST replace the placeholder with three sections: Profile (preferred_name), Practice Settings (words_per_session), and API Keys (BYOK for DeepSeek and Gemini).

**FR-047**: The API Keys section MUST display each key's status (custom vs default) with an [Edit Key] button that opens a modal.

**FR-048**: The API Keys section MUST show status indicators (green dot for custom key, gray dot for default).

**FR-048a**: The Edit Key modal MUST contain a password-type input, [Cancel] and [Save Key] buttons.

**FR-048b**: Clicking [Save Key] MUST show a loading spinner on the button, disable it, and keep the modal open during validation.

**FR-048c**: On validation success, the modal MUST close and the status indicator MUST update immediately.

**FR-048d**: On validation failure, the modal MUST stay open, show an inline error message, and re-enable the [Save Key] button.

**FR-049**: A page-level error banner MUST appear when the modal closes after a validation failure, displaying the error message.

---

## Non-Functional Requirements

**NFR-001**: Rate limiting MUST use `flask-limiter` with `get_remote_address` as the key function.

**NFR-002**: Rate limit storage SHOULD use Redis if `REDIS_URI` is available, falling back to in-memory storage.

**NFR-003**: Fernet encryption/decryption MUST handle decryption failures gracefully — log the error and fall back to default keys, never crash.

**NFR-004**: The `ENCRYPTION_KEY` MUST be a valid Fernet key (URL-safe base64-encoded 32 bytes). It MUST be generated once and stored in `.env`.

**NFR-005**: Internal error details (stack traces, SQL errors) MUST NOT be exposed in API responses. Use generic error messages and log details server-side.

**NFR-006**: The `UserProfile` lazy creation pattern MUST NOT cause N+1 queries. The `profile` relationship on `User` SHOULD use `lazy='joined'` to eager-load in a single query.

**NFR-007**: The Settings page MUST follow the existing Tailwind CSS design system (purple color scheme, card-based layout).

---

## API Requirements

### AR-001: Get Progress Stats

**Request**: `GET /api/progress/stats`

**Success response (200)**:
```json
{
  "words_practiced_today": 5,
  "mastery_percentage": 23,
  "words_ready_for_review": 42,
  "total_words": 55
}
```

**Empty user response (200)**:
```json
{
  "words_practiced_today": 0,
  "mastery_percentage": 0,
  "words_ready_for_review": 0,
  "total_words": 0
}
```

### AR-002: Get Settings

**Request**: `GET /api/settings`

**Success response (200)** -- profile exists:
```json
{
  "preferred_name": "Jasmine",
  "words_per_session": 15,
  "has_deepseek_key": true,
  "has_gemini_key": false
}
```

**Success response (200)** -- no profile:
```json
{
  "preferred_name": null,
  "words_per_session": null,
  "has_deepseek_key": false,
  "has_gemini_key": false
}
```

### AR-003: Update Settings

**Request**: `PUT /api/settings`
```json
{
  "preferred_name": "Jasmine",
  "words_per_session": 15
}
```

Note: API keys are managed via separate validation endpoint (AR-003a).

**Success response (200)**:
```json
{
  "preferred_name": "Jasmine",
  "words_per_session": 15,
  "has_deepseek_key": true,
  "has_gemini_key": false
}
```

**Validation error (400)**:
```json
{
  "error": "words_per_session must be between 1 and 50"
}
```

### AR-003a: Validate and Save API Key

**Request**: `POST /api/settings/keys/<provider>/validate`
```json
{
  "api_key": "sk-abc123..."
}
```

**Provider**: `deepseek` or `gemini`

**Success response (200)**:
```json
{
  "message": "DeepSeek API key saved",
  "has_deepseek_key": true
}
```

**Validation error (400)** - invalid key:
```json
{
  "error": "Invalid API key"
}
```

**Validation error (400)** - rate limited:
```json
{
  "error": "Rate limit exceeded"
}
```

**Validation error (400)** - timeout:
```json
{
  "error": "Validation timeout"
}
```

### AR-004: Delete API Key

**Request**: `DELETE /api/settings/keys/deepseek`

**Success response (200)**:
```json
{
  "message": "DeepSeek API key cleared",
  "has_deepseek_key": false,
  "deepseek_key_version": 2
}
```

**Invalid provider (400)**:
```json
{
  "error": "Invalid provider. Must be 'deepseek' or 'gemini'."
}
```

Note: Clearing a key increments its version, signaling active sessions to fall back to default keys.

### AR-005: Rate Limit Exceeded

Any endpoint when rate limit exceeded returns:

**Response (429)**:
```json
{
  "error": "Rate limit exceeded. Try again later."
}
```

---

## Out of Scope

The following items are explicitly NOT part of Milestone 4:

1. **API key validation/test endpoint**: No endpoint to verify if a BYOK key works before saving.
2. **Secrets vault integration**: Keys are Fernet-encrypted in the DB, not in a vault like HashiCorp Vault.
3. **Full regex-based prompt injection detection**: Only delimiter-based defense and system prompt hardening. No keyword scanning or encoding detection.
4. **Human-in-the-loop review**: No manual review of AI responses.
5. **Detailed progress dashboard** (PRD story #16): Only the 3 home page stat cards. The full dashboard is M6.
6. **CSRF protection**: Not needed — API is JWT-based (no cookies for auth on API routes).
7. **Account deletion**: Not part of MVP.
8. **Email verification**: Not part of MVP.

---

## Decisions Log

**DL-001**: Separate `UserProfile` table from `User`. Industry best practice: auth table for identity/credentials only, profile table for everything else. Sources: [culttt.com](https://culttt.com/2015/02/02/storing-user-settings-relational-database), [vertabelo.com](https://vertabelo.com/blog/user-profile-database-model/).

**DL-002**: Fernet symmetric encryption for BYOK keys. Simple, well-supported by the `cryptography` library. Single key for encrypt/decrypt. Good enough for a self-hosted learning app (not handling payment data).

**DL-003**: BYOK supports both DeepSeek and Gemini keys separately. Users may have access to one provider but not the other.

**DL-004**: Mastery stat uses `confidence_score > 0.9` (strictly greater). This matches `Word.STATUS_THRESHOLDS` at line 25-30 of `models.py` where the comparison is `score > threshold`.

**DL-005**: Lazy creation of `UserProfile`. Not created at registration because: (a) the registration frontend doesn't send `preferred_name`, (b) most defaults are handled by null-coalescing at read time, (c) avoids an extra DB write on every registration.

**DL-006**: `preferred_name` migration preserves `/api/me` API contract. `User.format_data()` reads from `self.profile.preferred_name` which returns the same JSON shape. Frontend `AuthContext.tsx` needs zero changes.

**DL-007**: Rate limits are per-IP using `get_remote_address`. Simple and effective for MVP. Per-user rate limiting could be added later if needed.

**DL-008**: Prompt injection defense uses OWASP-recommended `[DATA]...[/DATA]` delimiter pattern. Not foolproof, but significantly raises the bar and follows industry best practice. Source: [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

**DL-009**: `build_agents()` caches default agents. When no custom keys are provided, returns the existing module-level agents. Zero overhead for the 99% common case.

**DL-010**: Generic error messages for 500s. Internal error details (stack traces, SQL errors) are logged server-side but never returned to clients. Prevents information leakage.
