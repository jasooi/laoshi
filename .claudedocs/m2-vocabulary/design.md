# Milestone 2: Vocabulary Management -- Design Document

## Design Overview

This document describes HOW the M2 refinement tasks (2.13–2.22) will be implemented. The work spans both backend (pagination infrastructure, search/sort, validation, DRY refactors) and frontend (component extraction, fixed layout, pagination UI).

**Key architectural change**: The `GET /api/words` endpoint currently returns a bare array of all words. This milestone transforms it into a paginated endpoint with server-side search and sort, changing the response to `{data, pagination}`. The frontend moves from client-side filtering/sorting of the full dataset to server-driven pagination.

The guiding principles are:
1. **KISS**: Minimal changes to achieve the goal. No over-engineering.
2. **DRY**: Extract repeated patterns, but only within M2 scope (vocabulary-related code).
3. **Reusability**: The pagination utility and component are designed for reuse in future milestones.

---

## Architecture & Approach

### Data Flow (After M2)

```
User types search / changes page / changes sort
  |
  | debounce 300ms (search only)
  v
Frontend: api.get('/api/words', { params: { page, per_page, search, sort_by } })
  |
  | Vite proxy /api/* -> localhost:5000
  v
Backend: WordListResource.get()
  |
  | 1. Parse query params (page, per_page, search, sort_by)
  | 2. Build base query: Word.get_query_for_user(user)
  | 3. If search: add .filter(or_(ilike on word, pinyin, meaning))
  | 4. Add .order_by(sort_by column)
  | 5. paginate_query(query, page, per_page)
  |    -> SELECT COUNT(*) for total
  |    -> SELECT ... OFFSET x LIMIT y for items
  v
Response: { "data": [...], "pagination": { page, per_page, total, total_pages, ... } }
  |
  v
Frontend: setWords(data), setPagination(pagination)
  |
  v
Render: sticky thead + scrollable tbody + Pagination controls
```

### Page Layout Structure

```
┌─────────────────────────────────────────┐
│  Vocabulary              [Import btn]   │  ← flex-shrink-0 (fixed)
├─────────────────────────────────────────┤
│  [Warning banner if present]            │  ← flex-shrink-0 (fixed)
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │ [🔍 Search words...]  [Sort ↕]  │    │  ← flex-shrink-0 (fixed)
│  ├─────────────────────────────────┤    │
│  │ #  中文  Pinyin  Meaning  ...   │    │  ← sticky top-0 (fixed)
│  ├─────────────────────────────────┤    │
│  │ 1  你好  nǐ hǎo  hello    ...  │    │
│  │ 2  谢谢  xiè xie  thanks  ...  │    │  ← flex-1 overflow-y-auto
│  │ 3  ...                          │    │     (scrollable)
│  │ ...                             │    │
│  ├─────────────────────────────────┤    │
│  │ Showing 1-10 of 42  [< 1 2 >]  │    │  ← flex-shrink-0 (fixed)
│  │                    Per page [10]│    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## Backend Design

### 1. Pagination Utility (`backend/utils.py`)

Add a `paginate_query` function that operates on any SQLAlchemy query object:

```python
def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """
    Apply pagination to a SQLAlchemy query.

    Returns (items, pagination_dict) where pagination_dict contains:
    page, per_page, total, total_pages, has_next, has_prev, next_page, prev_page.
    """
```

**Design decisions:**
- Operates on a query object (not a model class) so it works with any filtered/sorted query.
- Uses `query.count()` which issues `SELECT COUNT(*)` — efficient for PostgreSQL.
- Clamps invalid inputs (page < 1, per_page > max) rather than returning errors — follows KISS.
- Returns a tuple `(items, pagination_dict)` so the caller can format items however needed.

### 2. Word Model Enhancement (`backend/models.py`)

**New classmethod**: `Word.get_query_for_user(viewer)` returns a query object (not `.all()`):
```python
@classmethod
def get_query_for_user(cls, viewer):
    return cls.query.filter_by(user_id=viewer.id)
```

This enables composing with search, sort, and pagination. The existing `get_full_list()` is preserved for backward compatibility (used in any code path that needs all words).

**Status thresholds extraction**: Replace magic numbers in the `status` property with a class constant:
```python
STATUS_THRESHOLDS = [
    (0.9, "Mastered"),
    (0.7, "Reviewing"),
    (0.3, "Learning"),
    (0.0, "Needs Revision"),
]
```

### 3. Paginated GET /api/words (`backend/resources.py`)

`WordListResource.get()` is rewritten to:

1. Parse query params from `request.args`:
   - `page` (int, default 1)
   - `per_page` (int, default 20)
   - `search` (str, default "")
   - `sort_by` (str, default "pinyin")

2. Build the query:
   ```python
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
   ```

3. Paginate and return:
   ```python
   items, pagination = paginate_query(base_query, page, per_page)
   data = [w.format_data(vc_user) for w in items]
   return {"data": data, "pagination": pagination}, 200
   ```

**Breaking change**: Response changes from `[...]` to `{"data": [...], "pagination": {...}}`. Both `Vocabulary.tsx` and `Home.tsx` must be updated simultaneously.

### 4. Input Validation on POST /api/words

Add two checks before the existing bulk-create loop:
```python
if not isinstance(data, list):
    return {"error": "Expected a JSON array of words"}, 400

for i, item in enumerate(data):
    for key in ("word", "pinyin", "meaning"):
        if key not in item or not item[key]:
            return {"error": f"Row {i+1} is missing required field: {key}"}, 400
```

---

## Frontend Design

### 1. TypeScript Types (`frontend/src/types/api.ts`)

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

### 2. Pagination Component (`frontend/src/components/Pagination.tsx`)

Props interface:
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
  perPageOptions?: number[]
}
```

**Layout**: Three-section flex row:
- Left: "Showing X–Y of Z words"
- Center: `[<] [1] [...] [4] [5] [6] [...] [16] [>]`
- Right: `Per page: [dropdown]`

**Page button logic** (to avoid rendering 100 buttons):
- Always show: first page, last page, current page
- Show: 1 page before and after current
- Use "..." for gaps
- Example for page 5 of 16: `[1] [...] [4] [5] [6] [...] [16]`

**Styling**: Purple active state, gray inactive, disabled prev/next when at boundary.

### 3. UploadModal Extraction (`frontend/src/pages/vocabulary/UploadModal.tsx`)

Extracted from Vocabulary.tsx lines 369–498. Self-contained component.

Props:
```typescript
interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onUploadSuccess: () => void
  onUploadWarning: (message: string) => void
}
```

Internal state: `selectedFile`, `sourceName`, `isDragging`, `uploading`, `uploadError`, `fileInputRef`.

The component owns the entire upload flow: file selection, drag/drop, CSV parsing, API call, error handling. It calls `onUploadSuccess` after a successful import and `onUploadWarning` if rows were skipped.

### 4. EditWordModal Extraction (`frontend/src/pages/vocabulary/EditWordModal.tsx`)

Extracted from Vocabulary.tsx lines 501–589. Self-contained component.

Props:
```typescript
interface EditWordModalProps {
  word: Word | null       // null = modal closed
  onClose: () => void
  onSaveSuccess: (updatedWord: Word) => void
}
```

Internal state: `editForm`, `editError`, `editSaving`.

The component is rendered when `word !== null`. It makes the PUT request and calls `onSaveSuccess` with the updated word from the server response.

### 5. Vocabulary.tsx Restructure

**State** (reduced from 15 to ~10 hooks):
```typescript
const [words, setWords] = useState<Word[]>([])
const [loading, setLoading] = useState(true)
const [searchQuery, setSearchQuery] = useState('')
const [debouncedSearch, setDebouncedSearch] = useState('')
const [sortBy, setSortBy] = useState<'pinyin' | 'word'>('pinyin')
const [page, setPage] = useState(1)
const [perPage, setPerPage] = useState(10)
const [pagination, setPagination] = useState<PaginationMeta | null>(null)
const [showUploadModal, setShowUploadModal] = useState(false)
const [uploadWarning, setUploadWarning] = useState<string | null>(null)
const [editingWord, setEditingWord] = useState<Word | null>(null)
```

**Search debounce**:
```typescript
useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedSearch(searchQuery)
    setPage(1)
  }, 300)
  return () => clearTimeout(timer)
}, [searchQuery])
```

**Data fetching** (depends on `debouncedSearch`, `sortBy`, `page`, `perPage`):
```typescript
const fetchVocabulary = useCallback(async () => {
  setLoading(true)
  try {
    const response = await api.get<PaginatedResponse<Word>>('/api/words', {
      params: {
        page,
        per_page: perPage,
        search: debouncedSearch || undefined,
        sort_by: sortBy,
      }
    })
    setWords(response.data.data)
    setPagination(response.data.pagination)
  } catch (error) {
    console.error('Error fetching vocabulary:', error)
    setWords([])
    setPagination(null)
  } finally {
    setLoading(false)
  }
}, [page, perPage, debouncedSearch, sortBy])

useEffect(() => { fetchVocabulary() }, [fetchVocabulary])
```

**Delete handler** (non-optimistic):
```typescript
const handleDelete = async (wordId: number) => {
  if (!confirm('Are you sure you want to delete this word?')) return
  try {
    await api.delete(`/api/words/${wordId}`)
    fetchVocabulary() // refetch current page
  } catch (error) {
    alert('Failed to delete word')
  }
}
```

**Callbacks for modals**:
```typescript
// After successful import
const handleUploadSuccess = () => {
  setShowUploadModal(false)
  setPage(1)
  fetchVocabulary()
}

// After successful edit
const handleEditSave = (updatedWord: Word) => {
  setEditingWord(null)
  fetchVocabulary() // refetch to get server-confirmed data
}
```

**Layout** (JSX structure):
```tsx
<div className="h-full flex flex-col overflow-hidden">
  {/* Fixed header */}
  <div className="flex-shrink-0 px-8 pt-8">
    <div className="flex items-center justify-between mb-4">
      <h1>Vocabulary</h1>
      <button>Import from file</button>
    </div>
    {uploadWarning && <WarningBanner />}
  </div>

  {/* Card with table */}
  <div className="flex-1 flex flex-col overflow-hidden mx-8 mb-8 bg-white rounded-2xl shadow-sm border">
    {/* Search bar */}
    <div className="flex-shrink-0 p-4 border-b">
      <SearchInput /> <SortButton />
    </div>

    {/* Scrollable table */}
    <div className="flex-1 overflow-y-auto">
      <table className="w-full">
        <thead className="sticky top-0 bg-white border-b z-10">
          <tr><th>#</th><th>中文</th><th>Pinyin</th>...</tr>
        </thead>
        <tbody>
          {words.map((word, index) => (
            <tr>
              <td>{(page - 1) * perPage + index + 1}</td>
              ...
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {/* Pagination footer */}
    <div className="flex-shrink-0 border-t">
      <Pagination
        page={page} totalPages={pagination.total_pages}
        total={pagination.total} perPage={perPage}
        hasNext={pagination.has_next} hasPrev={pagination.has_prev}
        onPageChange={setPage} onPerPageChange={(pp) => { setPerPage(pp); setPage(1) }}
      />
    </div>
  </div>

  <UploadModal ... />
  <EditWordModal ... />
</div>
```

### 6. Home.tsx Update

Change from fetching all words to using pagination metadata:
```typescript
const vocabResponse = await api.get('/api/words', { params: { per_page: 1 } })
const total = vocabResponse.data.pagination?.total ?? 0
setTotalWords(total)
setWordsWaiting(total)
```

This avoids fetching all words just to count them — a significant performance improvement for users with large vocabularies.

---

## File Changes Summary

| File | Type | Description |
|------|------|-------------|
| `backend/utils.py` | Modify | Add `paginate_query` function |
| `backend/models.py` | Modify | Add `get_query_for_user`, extract `STATUS_THRESHOLDS` |
| `backend/resources.py` | Modify | Paginate GET /api/words, validate POST |
| `frontend/src/types/api.ts` | Modify | Add `PaginationMeta`, `PaginatedResponse` |
| `frontend/src/components/Pagination.tsx` | New | Reusable pagination component |
| `frontend/src/pages/vocabulary/UploadModal.tsx` | New | Extracted upload modal |
| `frontend/src/pages/vocabulary/EditWordModal.tsx` | New | Extracted edit modal |
| `frontend/src/pages/Vocabulary.tsx` | Modify | Restructure layout, add pagination, server-side search |
| `frontend/src/pages/Home.tsx` | Modify | Use pagination.total for word count |
| `backend/tests/test_pagination.py` | New | Unit tests for paginate_query |
| `backend/tests/test_words_pagination.py` | New | Integration tests for GET /api/words |
| `frontend/src/test/Pagination.test.tsx` | New | Component tests for Pagination |

---

## Testing Strategy

### Backend

| Test file | Scope | Key test cases |
|-----------|-------|----------------|
| `test_pagination.py` | Unit: `paginate_query` | Basic pagination (25 items, 10/page), last page, empty query, input clamping (per_page > max, page < 1, page > total_pages) |
| `test_words_pagination.py` | Integration: `GET /api/words` | Paginated response format, page/per_page params, search filtering across fields, sort_by word vs pinyin, empty user, POST validation (non-array, missing keys) |

All tests use the existing `conftest.py` fixtures with SQLite in-memory.

### Frontend

| Test file | Scope | Key test cases |
|-----------|-------|----------------|
| `Pagination.test.tsx` | Component: `Pagination` | Renders page numbers, prev/next disabled at boundaries, onClick callbacks fire, per-page dropdown changes, "Showing X–Y of Z" text, ellipsis for large ranges |

Existing tests (`App.test.tsx`, `Login.test.tsx`, etc.) must be verified to still pass. Any mocks of `GET /api/words` returning a bare array must be updated to the new `{data, pagination}` shape.
