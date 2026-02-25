# Milestone 2: Vocabulary Management -- Requirements Document

## Feature Overview

Milestone 2 delivers the complete vocabulary management experience: CRUD operations, CSV import, search/filter/sort, and paginated browsing. It also introduces server-side pagination infrastructure that will be reused across future milestones.

**What already exists (tasks 2.1-2.12):**
- Backend CRUD endpoints: `GET /api/words`, `POST /api/words` (bulk), `GET/PUT/DELETE /api/words/<id>`, `DELETE /api/words` (all).
- Frontend Vocabulary page with CSV import modal (PapaParse), edit modal, delete with confirmation, client-side search and sort.
- All wired to authenticated backend via centralized Axios instance.

**What this milestone delivers (tasks 2.13-2.22):**
1. **Server-side pagination**: `GET /api/words` returns paginated results with metadata (total, pages, next/prev links).
2. **Server-side search & sort**: Search across word/pinyin/meaning fields and sort by pinyin or word — all handled by the backend.
3. **Input validation**: `POST /api/words` validates that data is an array and required keys exist.
4. **Code quality**: DRY refactors (ownership helper, status thresholds), component extraction from monolithic Vocabulary.tsx.
5. **Fixed-layout Vocabulary page**: Page title, search bar, import button, and table headers remain visible while only the table body scrolls.
6. **Pagination UI**: Users choose 10, 20, or 50 words per page with navigation controls.

This milestone maps to **PRD User Story #3** (CSV import), **PRD User Story #6** (Search, filter, sort), and **PRD User Story #7** (Edit/delete words).

---

## User Stories

### US-01: Browse vocabulary with pagination
**As a** learner with a large word list, **I want** to browse my vocabulary in pages of 10, 20, or 50 words **so that** the page loads quickly and I can navigate through my words efficiently.

**Acceptance Criteria:**
- The Vocabulary page defaults to showing 10 words per page.
- I can select 10, 20, or 50 from a per-page dropdown.
- Pagination controls show page numbers with Previous/Next buttons.
- The footer shows "Showing X–Y of Z words" with accurate counts.
- Navigating to another page fetches that page from the server.
- Changing the per-page option resets to page 1.

### US-02: Search vocabulary across all words
**As a** learner, **I want** to search my vocabulary by Chinese characters, pinyin, or meaning **so that** I can quickly find specific words regardless of which page they are on.

**Acceptance Criteria:**
- A search bar is visible at the top of the vocabulary table.
- Typing in the search bar filters results across ALL words (not just the current page).
- Search is case-insensitive and matches partial strings in word, pinyin, or meaning fields.
- Search results are paginated with updated totals.
- Searching resets to page 1.
- Search input is debounced (300ms) to avoid excessive API calls.
- Clearing the search box restores the full word list.

### US-03: Sort vocabulary
**As a** learner, **I want** to sort my vocabulary by pinyin or by Chinese word **so that** I can view my words in an order that helps me study.

**Acceptance Criteria:**
- A sort toggle button switches between "Sort by Pinyin" and "Sort by Word".
- Changing sort order fetches freshly sorted results from the server.
- Sorting resets to page 1.
- The current sort preference persists while navigating pages.

### US-04: Fixed page layout with scrollable table
**As a** learner, **I want** the page title, search bar, import button, and table headers to always be visible **so that** I can reference column headers and use controls without scrolling back to the top.

**Acceptance Criteria:**
- The page title ("Vocabulary"), import button, search bar, sort button, and table column headers (#, 中文, Pinyin, Meaning, Source Name, Actions) are always visible.
- Only the table body rows scroll vertically.
- The page itself does not scroll — the entire layout fits within the viewport.
- Pagination controls at the bottom are always visible.

### US-05: Edit a word
**As a** learner, **I want** to edit a word's Chinese characters, pinyin, meaning, or source name **so that** I can correct mistakes or update my vocabulary.

**Acceptance Criteria:**
- Clicking the edit icon on a word row opens a modal with the word's current values pre-filled.
- I can modify any field (word, pinyin, meaning, source_name).
- Word, pinyin, and meaning are required — the form shows an error if any are empty.
- Clicking "Save Changes" sends a PUT request and the table shows the updated word.
- Clicking "Cancel" or the X button closes the modal without changes.

### US-06: Delete a word
**As a** learner, **I want** to delete a word from my vocabulary **so that** I can remove words I no longer need.

**Acceptance Criteria:**
- Clicking the delete icon on a word row shows a confirmation prompt.
- Confirming the deletion removes the word from the server and updates the table.
- The word count decrements after deletion.
- If deletion fails, the word remains visible and an error is shown.

### US-07: Import vocabulary from CSV
**As a** learner, **I want** to upload a CSV file containing vocabulary **so that** I can bulk-add words to my collection.

**Acceptance Criteria:**
- Clicking "Import from file" opens an upload modal.
- The modal accepts .csv files via file picker or drag-and-drop.
- Required CSV columns: word, pinyin, meaning (case-insensitive headers).
- A source name must be provided before uploading.
- Rows with missing required fields are skipped with a warning count shown after import.
- After successful import, the vocabulary table refreshes to page 1.

---

## Functional Requirements

### Pagination -- Backend

**FR-001**: The `GET /api/words` endpoint MUST accept optional query parameters: `page` (integer, default 1), `per_page` (integer, default 20), `search` (string, optional), `sort_by` (string, `pinyin` or `word`, default `pinyin`).

**FR-002**: The response format for `GET /api/words` MUST change from a bare array to a structured object:
```json
{
  "data": [{ "id": 1, "word": "...", "pinyin": "...", ... }],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

**FR-003**: The `per_page` parameter MUST be clamped to a maximum of 100 and a minimum of 1. Invalid `page` values (< 1 or > total_pages) MUST be clamped to valid range.

**FR-004**: When `search` is provided, the backend MUST filter words where the search string appears (case-insensitive, partial match) in ANY of: `word`, `pinyin`, or `meaning` columns.

**FR-005**: When `sort_by` is `word`, results MUST be ordered by the `word` column. When `sort_by` is `pinyin` (or any other value), results MUST be ordered by the `pinyin` column.

**FR-006**: When there are no words (empty result), the response MUST still follow the paginated format: `{"data": [], "pagination": {"total": 0, "total_pages": 1, ...}}`.

**FR-007**: A reusable `paginate_query` utility function MUST be added to `backend/utils.py` that accepts a SQLAlchemy query object, page, per_page, and max_per_page, and returns `(items, pagination_dict)`.

**FR-008**: A `Word.get_query_for_user(viewer)` classmethod MUST be added that returns a SQLAlchemy query (not executed) filtered by `user_id=viewer.id`. This enables composing the query with search/sort/pagination.

### Input Validation -- Backend

**FR-009**: The `POST /api/words` endpoint MUST validate that the request body is a JSON array (not a dict or other type). If not, return 400 with `{"error": "Expected a JSON array of words"}`.

**FR-010**: The `POST /api/words` endpoint MUST validate that each item in the array contains the required keys `word`, `pinyin`, and `meaning` with non-empty values. If any item is missing a required key, return 400 with a descriptive error including the row number.

### Code Quality -- Backend

**FR-011**: The `Word.status` property's threshold values MUST be extracted to a class-level constant `STATUS_THRESHOLDS` on the `Word` model. The TODO comment on models.py line 25 MUST be removed.

### Pagination -- Frontend

**FR-013**: A reusable `Pagination` component MUST be created at `frontend/src/components/Pagination.tsx` that renders page navigation controls and a per-page dropdown.

**FR-014**: The `Pagination` component MUST accept props: `page`, `totalPages`, `total`, `perPage`, `hasNext`, `hasPrev`, `onPageChange`, `onPerPageChange`, and `perPageOptions` (default `[10, 20, 50]`).

**FR-015**: The Vocabulary page MUST default to 10 words per page with options to show 10, 20, or 50.

**FR-016**: Changing the page, per-page, search query, or sort order MUST trigger a new API call to `GET /api/words` with updated query parameters.

**FR-017**: Changing search query or per-page MUST reset the page to 1.

**FR-018**: Search input MUST be debounced (300ms delay) before triggering an API call.

**FR-019**: Row numbers in the table MUST reflect global position: `(page - 1) * perPage + index + 1`.

### Layout -- Frontend

**FR-020**: The Vocabulary page MUST use a fixed layout where the page title, import button, upload warning banner, search bar, sort button, and table column headers do NOT scroll.

**FR-021**: Only the table body rows MUST scroll vertically within the available space.

**FR-022**: The `<thead>` element MUST use `sticky top-0` positioning within a scrollable container to remain visible while scrolling through rows.

**FR-023**: The `Pagination` component MUST be placed in a fixed footer area below the scrollable table body.

### Component Extraction -- Frontend

**FR-024**: The upload modal (currently inline in Vocabulary.tsx) MUST be extracted to `frontend/src/pages/vocabulary/UploadModal.tsx`. It manages its own state (selectedFile, sourceName, isDragging, uploading, uploadError) and communicates via callback props.

**FR-025**: The edit word modal (currently inline in Vocabulary.tsx) MUST be extracted to `frontend/src/pages/vocabulary/EditWordModal.tsx`. It manages its own form state and communicates via callback props.

### Home Page Update

**FR-026**: `Home.tsx` MUST be updated to consume the new paginated response format from `GET /api/words`. Instead of fetching all words to count them, it MUST call `GET /api/words?per_page=1` and read `pagination.total` for the word count.

### TypeScript Types

**FR-027**: `PaginationMeta` and `PaginatedResponse<T>` interfaces MUST be added to `frontend/src/types/api.ts`.

### Delete Behavior

**FR-028**: Word deletion MUST NOT be optimistic. The frontend MUST await the `DELETE /api/words/<id>` response before removing the word from the UI. On failure, the word remains visible and an error is shown.

---

## Non-Functional Requirements

**NFR-001**: The paginated `GET /api/words` endpoint MUST respond within 200ms for a user with up to 1,000 words.

**NFR-002**: The `paginate_query` utility MUST use SQL `COUNT(*)` for total count and `OFFSET/LIMIT` for pagination, not Python-level slicing.

**NFR-003**: The search bar MUST be debounced to prevent more than ~3 API calls per second during typing.

**NFR-004**: The Vocabulary page MUST render correctly on viewports 1024px wide and above. Table columns MUST not overflow on standard desktop widths.

**NFR-005**: The `Pagination` component MUST be reusable — it MUST NOT contain vocabulary-specific logic. It accepts generic pagination metadata and emits page/perPage change events.

---

## UI/UX Requirements

**UIR-001**: The pagination controls MUST follow the existing Tailwind/purple design system: active page button uses `bg-purple-600 text-white`, inactive uses `border border-gray-200 text-gray-700 hover:bg-gray-50`, disabled prev/next uses `text-gray-300 cursor-not-allowed`.

**UIR-002**: The per-page dropdown MUST be a `<select>` element styled consistently with other form controls in the app.

**UIR-003**: The "Showing X–Y of Z words" text MUST appear in the pagination footer, using `text-sm text-gray-500`.

**UIR-004**: For large page counts (>7 pages), the page number buttons MUST use ellipsis (`...`) to avoid rendering dozens of buttons. Pattern: always show first page, last page, current page, and 1 page before/after current.

**UIR-005**: The scrollable table body area MUST have a subtle visual cue that more content exists (e.g., the `overflow-y-auto` scroll bar).

**UIR-006**: The sticky table header MUST have a white background and a bottom border to visually separate it from scrolling rows.

---

## API Requirements

**AR-001**: `GET /api/words` response format (BREAKING CHANGE from bare array):

**Request**: `GET /api/words?page=1&per_page=10&search=hello&sort_by=pinyin`

**Success response (200)**:
```json
{
  "data": [
    {
      "id": 1,
      "word": "你好",
      "pinyin": "nǐ hǎo",
      "meaning": "hello",
      "confidence_score": 0.5,
      "status": "Learning",
      "source_name": "HSK1"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false,
    "next_page": null,
    "prev_page": null
  }
}
```

**AR-002**: All other endpoints (`POST /api/words`, `PUT /api/words/<id>`, `DELETE /api/words/<id>`, `DELETE /api/words`) remain unchanged.

---

## Out of Scope

The following items are explicitly NOT part of Milestone 2:

1. **Pagination on other list endpoints** (`/api/users`, `/api/sessions`, `/api/sessions/<id>/words`). The `paginate_query` utility is reusable, but only `/api/words` is paginated in M2.
2. **Advanced filtering** (by confidence_score range, by status, by source_name). Only text search is implemented.
3. **Bulk edit/delete** operations beyond the existing "delete all" endpoint.
4. **Virtual scrolling** (react-window/react-virtuoso). Standard pagination is sufficient for MVP.
5. **Cross-cutting DRY refactors**: The repeated `User.get_by_id(int(get_jwt_identity()))` pattern (18+ instances), the "fetch by ID + check ownership" pattern (8+ instances across WordResource, SessionWordResource, UserSessionResource), and the `add()/update()/delete()` try/except/rollback duplication across 5 model classes. These are all cross-cutting concerns that require touching all resources/models. The proper solution is a decorator or mixin base class that handles user identity extraction and ownership verification in one shot — not a per-call-site helper. Deferred to a dedicated code-quality pass.
6. **Generic exception handling overhaul**. The bare `except Exception` pattern throughout resources.py is noted but deferred.
7. **Mobile-responsive table layout**. The table is designed for desktop viewports (1024px+).

---

## Decisions Log

**DL-001**: Server-side search chosen over client-side search. With pagination, the client only has one page of data. Client-side search would only work within the current page, giving poor UX. Server-side search with SQL `ILIKE` across word/pinyin/meaning fields is simple and correct.

**DL-002**: Search is debounced at 300ms on the frontend. This balances responsiveness with avoiding excessive API calls during typing.

**DL-003**: The pagination response format uses a `pagination` metadata object rather than HTTP Link headers. This is simpler for the React frontend to consume and doesn't require parsing headers.

**DL-004**: `per_page` max is 100. This prevents clients from accidentally fetching enormous result sets while still allowing power users to see large pages.

**DL-005**: Delete is non-optimistic. The previous implementation removed the word from React state before the backend confirmed deletion, which could leave the UI in an inconsistent state on failure. Refetching the current page after deletion is safer and simpler.

**DL-006**: Modal extraction: `UploadModal` and `EditWordModal` go into `pages/vocabulary/` (not `components/`) because they are page-specific, not reusable across the app. The `Pagination` component goes into `components/` because it will be reused by future list pages.

**DL-007**: The "fetch by ID + check ownership" pattern (5 lines repeated in WordResource.get/put/delete and similar resources) was considered for extraction as a helper function in M2. However, a module-level helper that returns `(resource, error)` still requires 3 lines per call site — it doesn't scale well across all resources. The proper DRY solution is a decorator (e.g., `@owned_resource(Word, "word")`) that also handles the `User.get_by_id(get_jwt_identity())` extraction, reducing both patterns to zero boilerplate. Since this is a cross-cutting refactor affecting all resource classes, it is deferred to a dedicated code-quality pass rather than half-done in M2.
