# Milestone 2: Vocabulary Management -- Task Breakdown

## Task Overview

**Total new tasks**: 9 tasks (2.13–2.15, 2.17–2.22) across 4 phases
**Existing tasks**: 2.1–2.12 are complete (2.10 was previously unmarked but is implemented)
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be parallelized where noted.

---

## Prerequisites

Before starting any tasks:

1. Ensure the backend virtual environment is active and `backend/requirements.txt` dependencies are installed.
2. Ensure `npm install` has been run in `frontend/`.
3. Ensure PostgreSQL is running and the `DATABASE_URI` in `.env` is valid.
4. Ensure both servers start: `python backend/app.py` (Flask on port 5000), `npm run dev` (Vite on port 5173).
5. Ensure existing backend tests pass: `cd backend && python -m pytest tests/ -v`.
6. Ensure existing frontend tests pass: `cd frontend && npm test -- --run`.

---

## Phase 1: Backend Infrastructure

These tasks add the pagination utility and model improvements. No frontend changes.

---

### T-2.13: Add `paginate_query` utility and `Word.get_query_for_user`

**Description**: Add a reusable pagination utility function to `utils.py` and a new classmethod to the Word model that returns an unexecuted query. Also extract the status threshold magic numbers to a class constant.

**Files affected**:
- `backend/utils.py` — add `paginate_query` function
- `backend/models.py` — add `get_query_for_user` classmethod, add `STATUS_THRESHOLDS` constant, update `status` property, remove TODO comment on line 25

**Changes to `backend/utils.py`**:

Add the following function:

```python
def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: A SQLAlchemy Query object (before .all() is called)
        page: Page number (1-indexed), defaults to 1
        per_page: Items per page, defaults to 20
        max_per_page: Maximum allowed per_page, defaults to 100

    Returns:
        tuple: (list_of_items, pagination_dict)
    """
    per_page = max(1, min(per_page, max_per_page))
    page = max(1, page)
    total = query.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "next_page": page + 1 if page < total_pages else None,
        "prev_page": page - 1 if page > 1 else None,
    }
```

**Changes to `backend/models.py`**:

1. Add class constant to `Word`:
   ```python
   STATUS_THRESHOLDS = [
       (0.9, "Mastered"),
       (0.7, "Reviewing"),
       (0.3, "Learning"),
       (0.0, "Needs Revision"),
   ]
   ```

2. Update `status` property to use `STATUS_THRESHOLDS`:
   ```python
   @property
   def status(self):
       score = self.confidence_score if self.confidence_score is not None else 0.5
       for threshold, label in self.STATUS_THRESHOLDS:
           if score > threshold:
               return label
       return "Needs Revision"
   ```

3. Remove the TODO comment on line 25.

4. Add new classmethod:
   ```python
   @classmethod
   def get_query_for_user(cls, viewer):
       """Returns a base query for a user's words (not yet executed)."""
       return cls.query.filter_by(user_id=viewer.id)
   ```

**Acceptance criteria**:
- `paginate_query` exists in `utils.py` and can be imported.
- `Word.get_query_for_user(user)` returns a Query object (not a list).
- `Word.get_full_list(viewer)` still works unchanged (backward compat).
- `Word.STATUS_THRESHOLDS` exists as a class constant.
- `Word.status` property behaves identically to before.
- TODO comment is removed.
- Existing backend tests pass.

---

## Phase 2: Backend API Changes

These tasks modify the API endpoints. Must be done after Phase 1.

---

### T-2.14: Add pagination, server-side search, and sort to `GET /api/words`

**Description**: Rewrite `WordListResource.get()` to accept pagination, search, and sort query parameters, and return the new paginated response format.

**Files affected**:
- `backend/resources.py` — rewrite `WordListResource.get()`

**Changes**:

1. Add imports at the top of `resources.py`:
   ```python
   from utils import paginate_query
   from extensions import db
   ```

2. Rewrite `WordListResource.get()`:
   ```python
   @jwt_required()
   def get(self):
       vc_user = User.get_by_id(int(get_jwt_identity()))

       page = request.args.get('page', 1, type=int)
       per_page = request.args.get('per_page', 20, type=int)
       search = request.args.get('search', '', type=str).strip()
       sort_by = request.args.get('sort_by', 'pinyin', type=str)

       base_query = Word.get_query_for_user(vc_user)

       if search:
           pattern = f"%{search}%"
           base_query = base_query.filter(
               db.or_(
                   Word.word.ilike(pattern),
                   Word.pinyin.ilike(pattern),
                   Word.meaning.ilike(pattern),
               )
           )

       if sort_by == 'word':
           base_query = base_query.order_by(Word.word)
       else:
           base_query = base_query.order_by(Word.pinyin)

       items, pagination = paginate_query(base_query, page=page, per_page=per_page)
       data = [w.format_data(vc_user) for w in items]

       return {"data": data, "pagination": pagination}, 200
   ```

**BREAKING CHANGE**: Response format changes from `[...]` to `{"data": [...], "pagination": {...}}`. Frontend tasks T-2.19 and T-2.20 must be implemented simultaneously.

**Acceptance criteria**:
- `GET /api/words` returns `{"data": [...], "pagination": {...}}`.
- `GET /api/words?page=2&per_page=10` returns the second page of 10 words.
- `GET /api/words?search=hello` filters across word, pinyin, meaning (case-insensitive).
- `GET /api/words?sort_by=word` sorts by Chinese word; default sorts by pinyin.
- Empty result returns `{"data": [], "pagination": {"total": 0, "total_pages": 1, ...}}`.
- `per_page` clamped to max 100.
- `page` clamped to valid range.

**Dependencies**: T-2.13 (paginate_query, get_query_for_user).

---

### T-2.15: Add input validation to `POST /api/words`

**Description**: Add validation to the bulk word import endpoint to check that the request body is a JSON array and that each item has the required keys.

**Files affected**:
- `backend/resources.py` — modify `WordListResource.post()`

**Changes**:

Add validation after the `if not data` check and before the loop:

```python
if not isinstance(data, list):
    return {"error": "Expected a JSON array of words"}, 400

for i, item in enumerate(data):
    for key in ("word", "pinyin", "meaning"):
        if key not in item or not item[key]:
            return {"error": f"Row {i+1} is missing required field: {key}"}, 400
```

**Acceptance criteria**:
- `POST /api/words` with a JSON object (not array) returns 400 with `"Expected a JSON array of words"`.
- `POST /api/words` with `[{"word": "hi"}]` (missing pinyin, meaning) returns 400 with `"Row 1 is missing required field: pinyin"`.
- `POST /api/words` with `[{"word": "", "pinyin": "abc", "meaning": "test"}]` returns 400 with `"Row 1 is missing required field: word"`.
- Valid arrays still work as before.
- Existing tests pass.

**Dependencies**: None (can be done in parallel with T-2.14).

---

## Phase 3: Frontend Changes

These tasks update the frontend. Must be done after Phase 2 (or simultaneously with Phase 2 if coordinated, since the API response format changes).

**Important**: Tasks T-2.17, T-2.18, and T-2.09 (types) can be done in parallel. T-2.19 depends on all of them. T-2.20 can be done in parallel with T-2.19.

---

### T-2.17: Create reusable `Pagination` component

**Description**: Create a pagination controls component that renders page navigation and a per-page dropdown.

**Files affected**:
- `frontend/src/components/Pagination.tsx` (new file)

**Props interface**:
```typescript
interface PaginationProps {
  page: number
  totalPages: number
  total: number
  perPage: number
  hasNext: boolean
  hasPrev: boolean
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
  perPageOptions?: number[]  // default [10, 20, 50]
}
```

**Rendering**:
- Left: `"Showing {start}–{end} of {total} words"` in `text-sm text-gray-500`
- Center: Previous button, page number buttons with ellipsis, Next button
- Right: `"Per page:"` label with `<select>` dropdown

**Page button logic**:
- Always render: page 1, last page, current page
- Render: current-1, current+1 (if they exist)
- Render `...` for gaps of 2+ pages
- Active page: `bg-purple-600 text-white rounded-lg`
- Inactive page: `border border-gray-200 text-gray-700 hover:bg-gray-50 rounded-lg`
- Disabled prev/next: `text-gray-300 cursor-not-allowed`

**Acceptance criteria**:
- Component renders correctly for various page counts (1, 5, 10, 50+ pages).
- Previous is disabled on page 1; Next is disabled on last page.
- Clicking page numbers calls `onPageChange` with the page number.
- Per-page dropdown calls `onPerPageChange` with the selected value.
- "Showing X–Y of Z" text is mathematically correct.
- No vocabulary-specific logic in the component.
- TypeScript compiles without errors.

**Dependencies**: None (needs PaginationMeta type from T-2.09 at integration time, but can be developed independently with local type).

---

### T-2.09 (types): Add `PaginationMeta` and `PaginatedResponse` types

**Description**: Add TypeScript interfaces for the new paginated API response format.

**Files affected**:
- `frontend/src/types/api.ts` — add two new interfaces

**Changes**:

Add after the existing `SessionWord` interface:

```typescript
export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
  next_page: number | null
  prev_page: number | null
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationMeta
}
```

**Acceptance criteria**:
- Types exist and are exported.
- TypeScript compiles without errors.

**Dependencies**: None.

---

### T-2.18: Extract `UploadModal` and `EditWordModal` from Vocabulary.tsx

**Description**: Extract the two inline modals from the monolithic Vocabulary.tsx into separate components.

**Files affected**:
- `frontend/src/pages/vocabulary/UploadModal.tsx` (new file)
- `frontend/src/pages/vocabulary/EditWordModal.tsx` (new file)
- `frontend/src/pages/Vocabulary.tsx` (remove inline modal code, import new components)

**UploadModal props**:
```typescript
interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onUploadSuccess: () => void
  onUploadWarning: (message: string) => void
}
```

Internal state: `selectedFile`, `sourceName`, `isDragging`, `uploading`, `uploadError`, `fileInputRef`.

Moves the following out of Vocabulary.tsx:
- `handleFileSelect`, `handleDragOver`, `handleDragLeave`, `handleDrop`, `handleFileInputChange`, `handleUpload` functions
- Upload modal JSX (current lines 369–498)

**EditWordModal props**:
```typescript
interface EditWordModalProps {
  word: Word | null       // null = modal closed
  onClose: () => void
  onSaveSuccess: (updatedWord: Word) => void
}
```

Internal state: `editForm`, `editError`, `editSaving`.

Moves the following out of Vocabulary.tsx:
- `handleEditSubmit` function (adapted to use `word` prop instead of `editingWord` state)
- Edit form state initialization (populate from `word` prop via useEffect)
- Edit modal JSX (current lines 501–589)

**Acceptance criteria**:
- Both modals work identically to before (same UI, same behavior, same error handling).
- Vocabulary.tsx no longer contains modal JSX or modal-specific state/handlers.
- The `vocabulary/` folder is created under `pages/`.
- TypeScript compiles without errors.

**Dependencies**: None (can be done in parallel with T-2.17).

---

### T-2.19: Restructure Vocabulary page with fixed layout and server-side pagination

**Description**: Major restructure of Vocabulary.tsx to use a fixed layout (scrollable table body only), server-side pagination/search/sort, and the extracted components.

**Files affected**:
- `frontend/src/pages/Vocabulary.tsx` — major rewrite

**Key changes**:

1. **Layout**: Change root to `h-full flex flex-col overflow-hidden`. Card uses `flex-1 flex flex-col overflow-hidden`. Table container uses `flex-1 overflow-y-auto`. `<thead>` uses `sticky top-0 bg-white z-10`.

2. **State**: Replace 15 useState hooks with ~10 (modal state moved to extracted components). Add: `page`, `perPage`, `pagination`, `debouncedSearch`.

3. **Data fetching**: Replace `fetchVocabulary` with a version that passes `page`, `per_page`, `search`, `sort_by` as API query params. Parse the new `{data, pagination}` response.

4. **Search debounce**: Add a useEffect that debounces `searchQuery` into `debouncedSearch` at 300ms. Reset page to 1 on search change.

5. **Sort**: On sort toggle, reset page to 1 and refetch.

6. **Delete**: Non-optimistic — await the DELETE request, then call `fetchVocabulary()` to refetch current page.

7. **Edit callback**: On save success from EditWordModal, call `fetchVocabulary()` to refetch.

8. **Import callback**: On upload success from UploadModal, reset to page 1 and refetch.

9. **Row numbers**: Use `(page - 1) * perPage + index + 1` for global numbering.

10. **Remove**: `filteredWords` computed variable (no longer needed — server returns the right data).

11. **Pagination footer**: Render `<Pagination>` component with props from pagination state.

**Acceptance criteria**:
- Page title, search bar, import button, and table headers are always visible.
- Only the table body scrolls vertically.
- Pagination controls are always visible at the bottom.
- Default shows 10 words per page.
- Per-page dropdown offers 10, 20, 50.
- Navigating pages fetches correct data from server.
- Search is debounced (300ms), resets to page 1, searches across all words.
- Sort toggle resets to page 1 and reorders server-side.
- Delete refetches current page (non-optimistic).
- Edit save refetches current page.
- Import resets to page 1 and refetches.
- Row numbers are globally consistent.
- TypeScript compiles without errors.

**Dependencies**: T-2.14 (backend pagination), T-2.17 (Pagination component), T-2.18 (extracted modals), T-2.09 (types).

---

### T-2.20: Update Home.tsx to use pagination metadata

**Description**: Update the Home page to consume the new paginated response format from `GET /api/words`, using `pagination.total` for the word count instead of fetching all words.

**Files affected**:
- `frontend/src/pages/Home.tsx` — modify `fetchStats`

**Changes**:

Replace:
```typescript
const vocabResponse = await api.get('/api/words')
const vocabData = vocabResponse.data
setTotalWords(Array.isArray(vocabData) ? vocabData.length : 0)
setWordsWaiting(Array.isArray(vocabData) ? vocabData.length : 0)
```

With:
```typescript
const vocabResponse = await api.get('/api/words', { params: { per_page: 1 } })
const total = vocabResponse.data.pagination?.total ?? 0
setTotalWords(total)
setWordsWaiting(total)
```

**Acceptance criteria**:
- Home page shows the correct total word count.
- Only 1 word is fetched from the backend (not all words).
- Works correctly when user has 0 words.
- TypeScript compiles without errors.

**Dependencies**: T-2.14 (backend pagination).

---

## Phase 4: Tests & Verification

These tasks write tests and verify everything works end-to-end. Must be done after Phases 1–3.

---

### T-2.21: Write backend tests

**Description**: Write unit tests for the pagination utility and integration tests for the paginated `GET /api/words` endpoint and the validated `POST /api/words` endpoint.

**Files affected**:
- `backend/tests/test_pagination.py` (new file)
- `backend/tests/test_words_pagination.py` (new file)

**Test cases for `test_pagination.py`**:
1. Basic pagination: 25 items, page 1, per_page 10 → returns 10 items, total=25, total_pages=3, has_next=True, has_prev=False.
2. Last page: 25 items, page 3, per_page 10 → returns 5 items, has_next=False, has_prev=True.
3. Empty query: 0 items → returns [], total=0, total_pages=1.
4. per_page exceeds max: clamped to max_per_page.
5. page > total_pages: clamped to last page.
6. page < 1: clamped to 1.
7. per_page < 1: clamped to 1.

**Test cases for `test_words_pagination.py`**:
1. `GET /api/words` returns paginated response format `{data, pagination}`.
2. `page` and `per_page` params return correct slice.
3. `search` param filters across word, pinyin, meaning (case-insensitive).
4. `sort_by=word` sorts by Chinese word; default sorts by pinyin.
5. Empty user returns `{data: [], pagination: {total: 0}}`.
6. `POST /api/words` with non-array body returns 400.
7. `POST /api/words` with missing required keys returns 400 with descriptive error.
8. `POST /api/words` with valid array still works as before.

**Acceptance criteria**:
- All test cases pass.
- Tests use the existing conftest.py fixtures with SQLite in-memory.
- `python -m pytest tests/ -v` passes with all tests green.

**Dependencies**: T-2.13, T-2.14, T-2.15.

---

### T-2.22: Write frontend tests and verify all tests pass

**Description**: Write component tests for the Pagination component and verify all existing tests pass with the new API response shape.

**Files affected**:
- `frontend/src/test/Pagination.test.tsx` (new file)
- Possibly update mocks in existing test files if they mock `GET /api/words`

**Test cases for `Pagination.test.tsx`**:
1. Renders page numbers and navigation buttons.
2. Previous button is disabled on page 1.
3. Next button is disabled on last page.
4. Clicking a page number calls `onPageChange` with correct value.
5. Per-page dropdown renders options and calls `onPerPageChange`.
6. "Showing X–Y of Z" text is mathematically correct.
7. Ellipsis renders for large page counts.

**Verification**:
- Run `cd frontend && npm test -- --run` — all tests (existing + new) pass.
- Run `cd backend && python -m pytest tests/ -v` — all tests pass.
- Update any existing test mocks that return a bare array from `/api/words` to the new `{data, pagination}` format.

**Acceptance criteria**:
- All Pagination component tests pass.
- All existing tests pass (no regressions).
- TypeScript compiles without errors.

**Dependencies**: T-2.17 (Pagination component), T-2.19 (Vocabulary restructure), T-2.20 (Home update).

---

## Execution Order Summary

```
Phase 1:
  T-2.13  paginate_query + Word model improvements

Phase 2 (parallel, after Phase 1):
  T-2.14  Paginate GET /api/words  (depends on T-2.13)
  T-2.15  Validate POST /api/words (independent)

Phase 3 (mixed parallelism, after Phase 2):
  T-2.09  TypeScript types         (independent)
  T-2.17  Pagination component     (independent)
  T-2.18  Extract modals           (independent)
  T-2.19  Restructure Vocabulary   (depends on T-2.14, T-2.09, T-2.17, T-2.18)
  T-2.20  Update Home.tsx          (depends on T-2.14, can parallel with T-2.19)

Phase 4 (after all above):
  T-2.21  Backend tests
  T-2.22  Frontend tests + full verification
```
