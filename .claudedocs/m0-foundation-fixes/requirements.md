# Milestone 0: Foundation Fixes -- Requirements Document

## Feature Overview

Milestone 0 resolves the structural mismatches and missing infrastructure that currently prevent the Laoshi Coach frontend and backend from communicating. The frontend makes API calls to paths that do not exist on the backend, sends no authentication headers, uses TypeScript interfaces whose field names do not match the backend response shapes, and has no test infrastructure. Until these issues are fixed, every other milestone is blocked.

This milestone makes the existing features functional end-to-end: vocabulary listing, CSV word import, word deletion, and home page statistics should all work against the real backend instead of silently failing or returning empty data. It also adds the `source_name` column to the Word model so imported words can be tagged with their origin file name.

---

## User Stories

### US-01: Vocabulary list loads from the real backend
**As a** logged-in learner, **I want** the Vocabulary page to display my words from the database **so that** I can see the vocabulary I have imported.

**Acceptance Criteria:**
- When I navigate to `/vocabulary`, the page fetches my words from the backend and renders them in the table.
- Each word row displays the Chinese characters, pinyin, English meaning, and source name.
- If I have no words, the empty state message is shown.
- If my session has expired or I am not logged in, the request fails gracefully (no unhandled crash).

### US-02: CSV vocabulary import works end-to-end
**As a** logged-in learner, **I want** to upload a CSV file of vocabulary words **so that** they are saved to the database and immediately visible in the Vocabulary table.

**Acceptance Criteria:**
- I click "Import from file", select a `.csv` file, enter a source name, and click "Attach File".
- The CSV is parsed on the frontend. Each row is mapped to `{ word, pinyin, meaning, source_name }`.
- The parsed data is sent as a JSON array via `POST /api/words`.
- On success, the modal closes, and the Vocabulary table refreshes to show the newly imported words.
- If the CSV is malformed or missing required columns, the user sees an error message.

### US-03: Home page statistics load from the real backend
**As a** logged-in learner, **I want** the Home page to show my total word count **so that** I know how many words I have imported.

**Acceptance Criteria:**
- The Home page fetches vocabulary data from the backend and displays the correct total word count.
- If the API call fails (e.g. not authenticated), the page renders without crashing and shows zero values.

### US-04: Authentication state persists across pages
**As a** logged-in learner, **I want** my login session to persist as I navigate between pages **so that** I do not have to re-authenticate on every page load.

**Acceptance Criteria:**
- After logging in via the `/token` endpoint, the JWT access token is stored in the browser.
- All subsequent API calls include the JWT token in the `Authorization: Bearer <token>` header.
- The token persists across page navigations within the same browser session.
- A logout action clears the stored token.

### US-05: Word data fields display correctly
**As a** logged-in learner, **I want** word data to display correctly on all pages **so that** I see the meaning, confidence score, status, and source name of each word.

**Acceptance Criteria:**
- The Vocabulary page table correctly maps the backend `meaning` field to the "Meaning" column and `source_name` to the "Source Name" column.
- The Practice page word card correctly displays the English meaning and the confidence status (e.g. "Learning", "Reviewing").
- No fields show `undefined` or are blank due to field name mismatches.

---

## Functional Requirements

### API Path Alignment

**FR-001**: All backend API routes MUST be prefixed with `/api` so that the Vite dev proxy (`/api` -> `http://localhost:5000`) correctly forwards frontend requests to the backend without requiring a URL rewrite rule.

**FR-002**: The following backend route mappings MUST be updated:

| Current Backend Route | New Backend Route |
|---|---|
| `/words` | `/api/words` |
| `/words/<int:id>` | `/api/words/<int:id>` |
| `/users` | `/api/users` |
| `/users/<int:id>` | `/api/users/<int:id>` |
| `/sessions` | `/api/sessions` |
| `/sessions/<int:id>` | `/api/sessions/<int:id>` |
| `/sessions/<int:session_id>/words` | `/api/sessions/<int:session_id>/words` |
| `/sessions/<int:session_id>/words/<int:word_id>` | `/api/sessions/<int:session_id>/words/<int:word_id>` |
| `/token` | `/api/token` |
| `/me` | `/api/me` |
| `/` | `/api/` |

**FR-003**: The following frontend API paths MUST be updated to match the new backend routes. All calls MUST use the centralized Axios instance (see FR-009):

| Current Frontend Path | New Frontend Path | File |
|---|---|---|
| `/api/vocabulary` | `/api/words` | `Home.tsx`, `Vocabulary.tsx` |
| `/api/vocabulary/import` (POST FormData) | `/api/words` (POST JSON array) | `Vocabulary.tsx` |
| `/api/vocabulary/${wordId}` | `/api/words/${wordId}` | `Vocabulary.tsx` |
| `/api/progress/stats` | (deferred -- see FR-004) | `Home.tsx` |
| `/api/practice/next-word` | (deferred -- see FR-004) | `Practice.tsx` |
| `/api/practice/evaluate` | (deferred -- see FR-004) | `Practice.tsx` |

**FR-004**: Frontend calls to `/api/progress/stats`, `/api/practice/next-word`, and `/api/practice/evaluate` do NOT have corresponding backend endpoints yet. These calls MUST gracefully handle the 404/error response and fall back to default/mock values without crashing. The existing fallback behavior in `Practice.tsx` (mock word data) and `Home.tsx` (zero values) is acceptable and should be preserved.

### JWT Authorization

**FR-005**: A React auth context/provider MUST be created at `frontend/src/contexts/AuthContext.tsx` that:
- Stores the JWT access token in both React state and `localStorage`.
- Provides the current user state (token, user info, loading state, isAuthenticated flag).
- Exposes `login(username, password)` and `logout()` functions.
- On app initialization, checks `localStorage` for an existing token and restores the session.

**FR-006**: The `login()` function MUST call `POST /api/token` with `{ username, password }` and store the returned `access_token`.

**FR-007**: The `logout()` function MUST clear the stored token from both React state and `localStorage`.

**FR-008**: All frontend API calls to authenticated endpoints MUST include the header `Authorization: Bearer <token>`, where `<token>` is the JWT access token from the auth context.

**FR-009**: A centralized Axios instance MUST be created at `frontend/src/lib/api.ts` (or similar) that:
- Sets the base URL (empty string, since the Vite proxy handles routing).
- Automatically attaches the `Authorization: Bearer <token>` header via a request interceptor that reads the token from `localStorage`.
- Sets `Content-Type: application/json` as the default header.
- Is imported by all page components instead of using raw `fetch()`.

**FR-010**: The `AuthProvider` MUST wrap the `<App />` component in `main.tsx` so that auth state is available to all routes.

### CSV Import Fix

**FR-011**: The `papaparse` npm package MUST be installed for robust CSV parsing on the frontend.

**FR-012**: The `handleUpload` function in `Vocabulary.tsx` MUST be rewritten to:
1. Parse the selected CSV file using `Papa.parse` with `header: true`.
2. Validate that the parsed data contains the required columns (`word`, `pinyin`, `meaning`). Column name matching should be case-insensitive.
3. Map each row to the shape `{ word, pinyin, meaning, source_name }`, where `source_name` is the value entered in the "Name your source file" input.
4. Send the mapped array as a JSON `POST` to `/api/words` using the centralized Axios instance.
5. On success, close the modal, clear state, and call `fetchVocabulary()` to refresh the table.
6. On failure, display the error message from the backend response.

**FR-013**: If the CSV is empty or missing required columns, an error message MUST be shown to the user without making an API call.

### Backend `source_name` Column

**FR-014**: A `source_name` column MUST be added to the `Word` model in `backend/models.py`:
- Type: `db.String(200)`
- Nullable: `True` (existing words will have `NULL` for this field)
- Default: `None`

**FR-015**: `Word.format_data()` MUST be updated to include `source_name` in its return dictionary.

**FR-016**: `WordListResource.post` in `backend/resources.py` MUST be updated to read `source_name` from each item in the JSON payload and pass it to the `Word` constructor. If `source_name` is not provided, it defaults to `None`.

**FR-017**: `WordResource.put` MUST add `source_name` to its `allowable_fields` list so that source name can be updated via PUT.

### Frontend TypeScript Interface Alignment

**FR-018**: A shared TypeScript type definition file MUST be created at `frontend/src/types/api.ts` that defines interfaces for all backend response shapes: `Word`, `User`, `UserSession`, `SessionWord`.

**FR-019**: The `Word` interface MUST match the backend `Word.format_data()` response shape exactly:
```typescript
interface Word {
  id: number
  word: string
  pinyin: string
  meaning: string
  confidence_score: number
  status: string
  source_name: string | null
}
```

**FR-020**: The local `VocabularyWord` interfaces in `Vocabulary.tsx` and `Practice.tsx` MUST be removed and replaced with the shared `Word` import from `frontend/src/types/api.ts`.

**FR-021**: All JSX references to the old field names MUST be updated:
- `word.definition` -> `word.meaning` (in `Vocabulary.tsx` filter function and table cell)
- `word.sourceName` -> `word.source_name` (in `Vocabulary.tsx` table cell)
- `currentWord.definition` -> `currentWord.meaning` (in `Practice.tsx` translation toggle)
- `currentWord.confidenceLevel` -> `currentWord.status` (in `Practice.tsx` confidence badge)
- Mock word objects in `Practice.tsx` must use `meaning`, `status`, `confidence_score`, `source_name` fields.

**FR-022**: The `handleDelete` parameter type in `Vocabulary.tsx` MUST change from `(wordId: string)` to `(wordId: number)` and the filter `w.id !== wordId` must use the same `number` type.

### Frontend Test Infrastructure

**FR-023**: Vitest MUST be installed and configured as the frontend test runner, with React Testing Library for component testing. The following packages MUST be added as dev dependencies:
- `vitest`
- `@testing-library/react`
- `@testing-library/jest-dom`
- `jsdom`

**FR-024**: A Vitest configuration MUST be added, either as a separate `vitest.config.ts` at the project root or as a `test` property within the existing `vite.config.ts`. The test environment MUST be set to `jsdom`.

**FR-025**: A `test` script MUST be added to `package.json` that runs `vitest`.

**FR-026**: At least one smoke test MUST be written that verifies the `<App />` component renders without crashing.

### Backend Test Infrastructure

**FR-027**: `pytest` MUST be added to `backend/requirements.txt` as a test dependency.

**FR-028**: A test configuration MUST be created that allows the Flask app to run against an in-memory SQLite database (not the production PostgreSQL database).

**FR-029**: A `conftest.py` file MUST be created in the `backend/tests/` directory that provides:
- A Flask test app fixture using the app factory with test configuration (SQLite in-memory).
- A test client fixture.
- A test database fixture that creates and tears down tables for each test.

**FR-030**: At least one smoke test MUST be written that verifies the Flask app starts and the `GET /api/` health-check endpoint responds with a 200 status code.

---

## Non-Functional Requirements

**NFR-001**: No existing frontend UI layout or styling is changed by this milestone. All changes are to data plumbing (API paths, auth headers, field names, CSV parsing) and test infrastructure.

**NFR-002**: The backend route prefix change MUST be a single-point change (e.g. Flask Blueprint prefix or `Api` prefix parameter) so that adding `/api` does not require editing every resource registration individually.

**NFR-003**: The auth token storage MUST use `localStorage` so that the token survives page refreshes within the same browser tab. (This is acceptable for an MVP; a more secure approach using `httpOnly` cookies can be adopted in a later milestone.)

**NFR-004**: All test infrastructure MUST be runnable without requiring a running PostgreSQL database or external services.

**NFR-005**: Frontend tests MUST run in under 30 seconds for the smoke test suite.

**NFR-006**: Backend tests MUST run in under 10 seconds for the smoke test suite.

---

## UI/UX Requirements

**UIR-001**: No visual changes are expected. The Vocabulary page table headers already say "Meaning" and "Source Name", so the data mapping fix aligns the data with the existing headers.

**UIR-002**: The Practice page word card currently references `currentWord.definition` for the translation toggle and `currentWord.confidenceLevel` for the confidence badge. After the interface fix, these MUST continue to render identically using the corrected field names (`currentWord.meaning`, `currentWord.status`).

**UIR-003**: The `handleDelete` function in `Vocabulary.tsx` currently expects `wordId` as a `string`. After the interface fix changes `id` to `number`, the delete URL must still resolve correctly (template literals coerce numbers to strings automatically, but the filter comparison `w.id !== wordId` must use consistent types).

**UIR-004**: The upload modal flow remains visually identical. The only behavioral change is that clicking "Attach File" now parses the CSV on the frontend and sends JSON to the backend instead of sending a FormData payload to a nonexistent endpoint.

---

## Data Requirements

**DR-001**: A `source_name` column (type `VARCHAR(200)`, nullable, default `NULL`) MUST be added to the `word` table. A Flask-Migrate migration MUST be generated and applied.

**DR-002**: Existing rows in the `word` table will have `source_name = NULL` after the migration. This is acceptable.

**DR-003**: The `Word.format_data()` return shape after this milestone will be:
```python
{
    'id': int,
    'word': str,
    'pinyin': str,
    'meaning': str,
    'confidence_score': float,
    'status': str,        # computed property
    'source_name': str | None
}
```

---

## API Requirements

**AR-001**: All existing API endpoints retain their current request/response contracts. Only the URL prefix changes (adding `/api`).

**AR-002**: The `POST /api/words` endpoint request body is extended to accept an optional `source_name` field per word object:
```json
[
  { "word": "...", "pinyin": "...", "meaning": "...", "source_name": "..." },
  ...
]
```
If `source_name` is omitted, it defaults to `None`.

**AR-003**: The `POST /api/token` endpoint already returns `{ "access_token": "<jwt>" }` on success and `{ "message": "..." }` with 401 on failure. No changes needed.

**AR-004**: All `@jwt_required` endpoints already return 401 with a JWT error message when no valid token is provided. The frontend auth layer must handle these 401 responses.

---

## Out of Scope

The following items are explicitly NOT part of Milestone 0:

1. **New backend endpoints** for practice evaluation (`/api/practice/evaluate`), next-word selection (`/api/practice/next-word`), or progress statistics (`/api/progress/stats`). These belong to later milestones.
2. **Login and registration UI pages**. The auth context provides the infrastructure for storing and using tokens, but building login/register form pages is deferred.
3. **Protected route redirects**. Automatically redirecting unauthenticated users to a login page is deferred until the login page exists.
4. **Token refresh / expiry handling**. Handling expired JWTs gracefully (e.g. prompting re-login) is deferred.
5. **End-to-end (Cypress/Playwright) tests**. Only unit/integration tests with Vitest and pytest are in scope.
6. **CI/CD pipeline setup**. Test infrastructure is local only for this milestone.
7. **Server-side CSV parsing**. CSV files are parsed entirely on the frontend using PapaParse.

---

## Decisions Log (Resolved Open Questions)

**OQ-001 -- RESOLVED**: Add `/api` prefix to all Flask routes (backend change). The Vite proxy forwards `/api/*` to `http://localhost:5000` without stripping the prefix, so Flask must serve routes at `/api/*`. No Vite proxy rewrite is needed.

**OQ-002 -- RESOLVED**: Migrate all frontend `fetch()` calls to a centralized Axios instance. Axios is already a `package.json` dependency. The centralized instance will use request interceptors to attach the JWT `Authorization` header automatically.

**OQ-003 -- RESOLVED (SCOPE EXPANDED)**: Fix the CSV upload flow in M0. The frontend will install `papaparse`, parse CSV files client-side, and send parsed data as JSON to `POST /api/words`. A `source_name` column will be added to the `Word` model on the backend to support tagging imported words with their origin file name.

**OQ-004 -- RESOLVED**: The shared types file at `frontend/src/types/api.ts` will define interfaces for ALL backend response shapes: `Word`, `User`, `UserSession`, `SessionWord`.

**OQ-005 -- RESOLVED**: The `source_name` field is kept on the frontend interface and backed by a new `source_name` column on the `Word` database model.
