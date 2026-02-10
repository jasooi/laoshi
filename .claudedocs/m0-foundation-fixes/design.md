# Milestone 0: Foundation Fixes -- Design Document

## Design Overview

This document describes HOW the six foundation-fix tasks (plus the expanded CSV import scope) will be implemented. The guiding principles are:

1. **Minimal surface area**: prefer single-point changes (e.g. one `Api` prefix parameter) over shotgun edits across many files.
2. **Consistency with existing patterns**: follow the Flask-RESTful resource pattern, the existing model `format_data()` convention, and the component-per-page frontend structure.
3. **Incremental testability**: each phase produces working code that can be verified before the next phase begins.

---

## Architecture & Approach

### High-Level Data Flow (After M0)

```
Browser (React + Vite dev server :5173)
  |
  |  All API calls use centralized Axios instance
  |  Authorization: Bearer <jwt> header attached automatically
  |
  v
Vite Proxy (/api/* -> http://localhost:5000/api/*)
  |
  v
Flask (:5000) with Api prefix='/api'
  |
  v
Flask-RESTful Resources -> SQLAlchemy Models -> PostgreSQL
```

The Vite proxy in `vite.config.ts` already forwards `/api` to `http://localhost:5000` without stripping the prefix. By changing the Flask-RESTful `Api` prefix to `/api`, backend routes become `/api/words`, `/api/token`, etc., and the proxy just passes through.

---

## Backend Design

### 1. API Prefix Change (Task 0.1)

**File**: `backend/app.py`

The current `register_resources` function creates an `Api` instance with no prefix:

```python
# CURRENT
def register_resources(app):
    api = Api(app)
    api.add_resource(WordListResource, '/words')
    ...
```

Flask-RESTful's `Api` class accepts a `prefix` parameter. The fix is a one-line change:

```python
# NEW
def register_resources(app):
    api = Api(app, prefix='/api')
    api.add_resource(WordListResource, '/words')
    ...
```

This prepends `/api` to every route registered via `api.add_resource`. The resource registration strings themselves do NOT change. The `HomeResource` at `/` will become `/api/` (the health-check endpoint).

No changes are needed to `resources.py`, `models.py`, or any other backend file for the prefix change.

**Verification**: `GET http://localhost:5000/api/` should return the existing `HomeResource` response. `GET http://localhost:5000/words` should return 404.

### 2. `source_name` Column Addition (Task 0.1 extended / OQ-003)

**File**: `backend/models.py`

Add a new nullable column to the `Word` model:

```python
class Word(db.Model):
    __tablename__ = 'word'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(150), nullable=False)
    pinyin = db.Column(db.String(150), nullable=False)
    meaning = db.Column(db.String(300), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False, default=0.5)
    source_name = db.Column(db.String(200), nullable=True, default=None)  # NEW
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    ...
```

Update `format_data()` to include the new field:

```python
def format_data(self, viewer=None):
    if viewer is None or viewer.id != self.user_id:
        return None
    return {
        'id': self.id,
        'word': self.word,
        'pinyin': self.pinyin,
        'meaning': self.meaning,
        'confidence_score': self.confidence_score,
        'status': self.status,
        'source_name': self.source_name,  # NEW
    }
```

**Migration**: Run `flask db migrate -m "add source_name to word"` then `flask db upgrade`. Since the column is nullable with a default of `None`, existing rows are unaffected.

**File**: `backend/resources.py`

In `WordListResource.post`, read `source_name` from each item:

```python
# CURRENT
word_to_add = Word(word=item["word"], pinyin=item["pinyin"], meaning=item["meaning"], user_id=vc_user.id)

# NEW
word_to_add = Word(
    word=item["word"],
    pinyin=item["pinyin"],
    meaning=item["meaning"],
    source_name=item.get("source_name"),  # NEW - optional field
    user_id=vc_user.id
)
```

In `WordResource.put`, add `source_name` to the allowable fields:

```python
# CURRENT
allowable_fields = ["word", "pinyin", "meaning", "confidence_score"]

# NEW
allowable_fields = ["word", "pinyin", "meaning", "confidence_score", "source_name"]
```

### 3. Backend Test Infrastructure (Task 0.5)

**New files**:
- `backend/tests/__init__.py` (empty, makes `tests` a package)
- `backend/tests/conftest.py` (pytest fixtures)
- `backend/tests/test_smoke.py` (smoke test)

**File**: `backend/requirements.txt`

Add at the end:

```
# Testing
pytest>=7.0.0
```

**File**: `backend/config.py`

Add a `TestConfig` class that overrides the database URI to use SQLite in-memory:

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'
```

Note: The current `Config` class reads `SQLALCHEMY_DATABASE_URI` from the env var. `TestConfig` overrides this with a hardcoded SQLite URI so tests never touch the real database. However, there is a subtlety: the current `Config` uses `SECRET_KEY` for the JWT secret (via `os.getenv('JWT_SECRET_KEY')`), but Flask-JWT-Extended looks for `JWT_SECRET_KEY` first and falls back to `SECRET_KEY`. We set both in `TestConfig` to be safe.

**File**: `backend/tests/conftest.py`

```python
import pytest
import sys
import os

# Add backend directory to Python path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from extensions import db as _db
from config import TestConfig


@pytest.fixture(scope='session')
def app():
    """Create a Flask app configured for testing."""
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope='function')
def db(app):
    """Create fresh database tables for each test function."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """A Flask test client with a clean database."""
    return app.test_client()
```

This requires a small change to `create_app()` in `backend/app.py` to accept an optional config class:

```python
# CURRENT
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    ...

# NEW
def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)
    ...
```

**File**: `backend/tests/test_smoke.py`

```python
def test_health_check(client):
    """GET /api/ should return 200."""
    response = client.get('/api/')
    assert response.status_code == 200
```

---

## Frontend Design

### 4. Centralized Axios Instance (Task 0.2 / FR-009)

**New file**: `frontend/src/lib/api.ts`

```typescript
import axios from 'axios'

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach JWT token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
```

**Why `localStorage` directly instead of reading from auth context?** The Axios instance is a module-level singleton created outside of the React component tree. It cannot access React context. Reading directly from `localStorage` is the standard pattern for Axios interceptors. The `AuthContext` is the authoritative source for React components; `localStorage` is the authoritative source for the Axios interceptor. They are kept in sync by the `login()`/`logout()` functions which write to both.

### 5. Auth Context/Provider (Task 0.3)

**New file**: `frontend/src/contexts/AuthContext.tsx`

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import api from '../lib/api'

interface User {
  id: number
  username: string
  preferred_name: string | null
}

interface AuthContextType {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, check localStorage for an existing token
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    if (storedToken) {
      setToken(storedToken)
      // Fetch user info to validate the token is still good
      api.get('/api/me')
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token is invalid or expired -- clear it
          localStorage.removeItem('access_token')
          setToken(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const response = await api.post('/api/token', { username, password })
    const accessToken = response.data.access_token
    localStorage.setItem('access_token', accessToken)
    setToken(accessToken)

    // Fetch user info after login
    const userResponse = await api.get('/api/me')
    setUser(userResponse.data)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

**File modified**: `frontend/src/main.tsx`

Wrap `<App />` with `<AuthProvider>`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { AuthProvider } from './contexts/AuthContext.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
```

Note: The `AuthProvider` is placed inside `<React.StrictMode>` but outside `<Router>` (which is inside `<App>`). This is correct because auth state is app-global and does not depend on routing.

### 6. Shared TypeScript Types (Task 0.6)

**New file**: `frontend/src/types/api.ts`

```typescript
// Backend response shapes -- must match the format_data() output of each model.

export interface Word {
  id: number
  word: string
  pinyin: string
  meaning: string
  confidence_score: number
  status: string
  source_name: string | null
}

export interface User {
  id: number
  username?: string
  preferred_name?: string | null
}

export interface UserSession {
  id: number
  session_start_ds: string    // ISO datetime string
  session_end_ds: string | null
  user_id: number
}

export interface SessionWord {
  id: string                  // composite key as "wordId_sessionId"
  is_skipped: boolean
  session_notes: string | null
}
```

The `User` interface uses optional fields for `username` and `preferred_name` because `User.format_data()` returns different shapes depending on whether the viewer is the owner/admin (full data) or another user (just `id`).

### 7. Frontend API Path Migration (Task 0.1 frontend side)

All `fetch()` calls in the frontend are replaced with the centralized Axios instance. The path changes are:

**File**: `frontend/src/pages/Home.tsx`

```typescript
// CURRENT
const vocabResponse = await fetch('/api/vocabulary')
const progressResponse = await fetch('/api/progress/stats')

// NEW
import api from '../lib/api'
const vocabResponse = await api.get('/api/words')
// /api/progress/stats stays as-is but uses api instance; the catch block handles 404 gracefully
```

The `Home.tsx` logic changes:
- Replace `fetch('/api/vocabulary')` with `api.get('/api/words')`.
- The `response.ok` check becomes a try/catch (Axios throws on non-2xx).
- Data is accessed via `response.data` instead of `response.json()`.
- The `/api/progress/stats` call is left pointing to a non-existent endpoint. The catch block sets zero values (existing behavior preserved).

**File**: `frontend/src/pages/Vocabulary.tsx`

```typescript
// CURRENT
const response = await fetch('/api/vocabulary')
const response = await fetch('/api/vocabulary/import', { method: 'POST', body: formData })
const response = await fetch(`/api/vocabulary/${wordId}`, { method: 'DELETE' })

// NEW
import api from '../lib/api'
const response = await api.get('/api/words')
// Upload: see CSV import section below
await api.delete(`/api/words/${wordId}`)
```

**File**: `frontend/src/pages/Practice.tsx`

```typescript
// CURRENT
const response = await fetch('/api/practice/next-word')
const response = await fetch('/api/practice/evaluate', { method: 'POST', ... })

// NEW
import api from '../lib/api'
const response = await api.get('/api/practice/next-word')
const response = await api.post('/api/practice/evaluate', { wordId: currentWord.id, sentence: inputText })
```

The Practice page paths still point to non-existent endpoints (`/api/practice/next-word`, `/api/practice/evaluate`). The existing catch blocks handle these gracefully by falling back to mock data. This is intentional -- these endpoints are out of scope for M0.

### 8. CSV Import Frontend Fix (Task 0.1 extended / OQ-003)

**New dependency**: `papaparse` (and `@types/papaparse` for TypeScript)

Install:
```
npm install papaparse
npm install -D @types/papaparse
```

**File modified**: `frontend/src/pages/Vocabulary.tsx`

The `handleUpload` function is rewritten:

```typescript
import Papa from 'papaparse'
import api from '../lib/api'

const handleUpload = async () => {
  if (!selectedFile || !sourceName.trim()) {
    alert('Please select a file and enter a source name')
    return
  }

  setUploading(true)
  try {
    // Parse CSV on the frontend
    const parseResult = await new Promise<Papa.ParseResult<Record<string, string>>>((resolve, reject) => {
      Papa.parse<Record<string, string>>(selectedFile, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => resolve(results),
        error: (error) => reject(error),
      })
    })

    // Validate required columns (case-insensitive)
    const headers = parseResult.meta.fields?.map(f => f.toLowerCase()) || []
    const requiredColumns = ['word', 'pinyin', 'meaning']
    const missingColumns = requiredColumns.filter(col => !headers.includes(col))

    if (missingColumns.length > 0) {
      alert(`CSV is missing required columns: ${missingColumns.join(', ')}`)
      return
    }

    if (parseResult.data.length === 0) {
      alert('CSV file contains no data rows')
      return
    }

    // Map rows to backend shape
    // Use case-insensitive column lookup
    const fieldMap: Record<string, string> = {}
    parseResult.meta.fields?.forEach(f => {
      fieldMap[f.toLowerCase()] = f
    })

    const words = parseResult.data.map(row => ({
      word: row[fieldMap['word']],
      pinyin: row[fieldMap['pinyin']],
      meaning: row[fieldMap['meaning']],
      source_name: sourceName.trim(),
    }))

    // Send to backend
    const response = await api.post('/api/words', words)
    console.log('Import successful:', response.data)
    setShowUploadModal(false)
    setSelectedFile(null)
    setSourceName('')
    fetchVocabulary()
  } catch (error: any) {
    console.error('Error uploading file:', error)
    const message = error.response?.data?.error || 'Failed to upload file. Please try again.'
    alert(`Import failed: ${message}`)
  } finally {
    setUploading(false)
  }
}
```

**Key design decisions for CSV parsing:**

1. **Client-side parsing only**: the CSV file never leaves the browser. PapaParse reads it from the `File` object directly.
2. **Case-insensitive column matching**: if the CSV has headers like "Word", "PINYIN", or "Meaning", they still match. This is done by building a `fieldMap` from lowercase header names to original header names.
3. **Validation before API call**: if required columns are missing or no data rows exist, we show an error and skip the network request.
4. **source_name applied uniformly**: all words in a single upload get the same `source_name` (the value from the input field).

### 9. TypeScript Interface Updates (Task 0.6)

**File**: `frontend/src/pages/Vocabulary.tsx`

Remove the local `VocabularyWord` interface and import `Word` from the shared types:

```typescript
// REMOVE
interface VocabularyWord {
  id: string
  word: string
  pinyin: string
  definition: string
  sourceName: string
}

// ADD
import { Word } from '../types/api'
```

Update all state and function signatures:
- `useState<VocabularyWord[]>([])` becomes `useState<Word[]>([])`
- `handleDelete(wordId: string)` becomes `handleDelete(wordId: number)`
- `handleEdit(wordId: string)` becomes `handleEdit(wordId: number)`

Update JSX references:
- `word.definition` becomes `word.meaning` (in filter function line 52 and table cell line 243)
- `word.sourceName` becomes `word.source_name` (in table cell line 244)

**File**: `frontend/src/pages/Practice.tsx`

Remove the local `VocabularyWord` interface and import `Word`:

```typescript
// REMOVE
interface VocabularyWord {
  id: string
  word: string
  pinyin: string
  definition: string
  confidenceLevel: string
}

// ADD
import { Word } from '../types/api'
```

Update all state and references:
- `useState<VocabularyWord | null>(null)` becomes `useState<Word | null>(null)`
- `currentWord.definition` becomes `currentWord.meaning` (line 277)
- `currentWord.confidenceLevel` becomes `currentWord.status` (line 283)
- Mock word objects update their field names:
  ```typescript
  const mockWord: Word = {
    id: 1,
    word: '学习',
    pinyin: 'xue xi',
    meaning: 'to study, to learn',
    confidence_score: 0.5,
    status: 'Learning',
    source_name: null,
  }
  ```

---

## Frontend Test Infrastructure Design (Task 0.4)

### Package Installation

```
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

### Configuration

**File modified**: `vite.config.ts` (at repo root)

Add a `test` block to the existing Vite config:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'frontend/public',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./frontend/src/test/setup.ts'],
  },
})
```

Note: We use the `test` property within `vite.config.ts` rather than a separate `vitest.config.ts` to keep configuration in one place. The `globals: true` setting makes `describe`, `it`, `expect` available without importing. The `setupFiles` array points to a setup file that configures jest-dom matchers.

**New file**: `frontend/src/test/setup.ts`

```typescript
import '@testing-library/jest-dom'
```

**File modified**: `package.json`

Add a `test` script:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc && vite build",
  "preview": "vite preview",
  "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
  "test": "vitest"
}
```

**New file**: `frontend/src/test/App.test.tsx`

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../../App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    // The Welcome page is the default route, check for its heading
    expect(screen.getByText('Welcome to the classroom')).toBeInTheDocument()
  })
})
```

Note: The `<App />` component contains `<BrowserRouter>` internally, so no extra `<MemoryRouter>` wrapper is needed for the smoke test. The default route `/` renders the `<Welcome />` page which contains the text "Welcome to the classroom".

### TypeScript Configuration for Tests

**File modified**: `tsconfig.json`

The `include` array currently only has `"src"`. Since test files live in `frontend/src/test/`, they are already within the `src` directory of the Vite root... but wait. The `tsconfig.json` `include` says `"src"` which means `<root>/src/`. But the frontend source is actually at `frontend/src/`. We need to update the include to cover the actual source location:

```json
{
  "compilerOptions": { ... },
  "include": ["frontend/src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Also add Vitest types to `compilerOptions.types`:

```json
"compilerOptions": {
  ...
  "types": ["vitest/globals"]
}
```

---

## Backend Test Infrastructure Design (Task 0.5)

Covered in the Backend Design section above (item 3). Summary of new/modified files:

| File | Action |
|---|---|
| `backend/requirements.txt` | Add `pytest>=7.0.0` |
| `backend/config.py` | Add `TestConfig` class |
| `backend/app.py` | Modify `create_app()` to accept optional `config_class` parameter |
| `backend/tests/__init__.py` | New (empty) |
| `backend/tests/conftest.py` | New (pytest fixtures) |
| `backend/tests/test_smoke.py` | New (smoke test) |

Tests are run from the `backend/` directory with `python -m pytest tests/` or simply `pytest` if the working directory is `backend/`.

---

## Data Flow: Key User Interactions

### Flow 1: User opens Vocabulary page (GET /api/words)

```
1. Vocabulary.tsx mounts, calls fetchVocabulary()
2. fetchVocabulary() calls api.get('/api/words')
3. Axios interceptor reads access_token from localStorage
   -> If token exists, attaches Authorization: Bearer <token>
   -> If no token, no header attached (request will 401)
4. Request goes to Vite dev server proxy
5. Proxy forwards to http://localhost:5000/api/words
6. Flask-RESTful routes to WordListResource.get()
7. @jwt_required checks Authorization header
   -> If valid, extracts user_id from JWT
   -> If missing/invalid, returns 401
8. WordListResource.get() calls Word.get_full_list(vc_user)
9. Returns JSON array of word objects via format_data()
10. Axios response.data contains the array
11. Vocabulary.tsx sets words state, table renders
    -> word.meaning maps to "Meaning" column
    -> word.source_name maps to "Source Name" column
```

### Flow 2: User imports CSV file (POST /api/words)

```
1. User clicks "Import from file", selects CSV, enters source name
2. User clicks "Attach File" -> handleUpload() fires
3. Papa.parse reads the File object, returns parsed rows
4. Validation: checks for required columns (word, pinyin, meaning)
5. Maps rows to [{ word, pinyin, meaning, source_name }]
6. api.post('/api/words', wordsArray)
   -> Axios interceptor attaches Bearer token
   -> Content-Type: application/json (default)
7. Vite proxy -> Flask /api/words -> WordListResource.post()
8. @jwt_required validates token
9. Iterates JSON array, creates Word instances with source_name
10. Word.add_list() bulk inserts
11. Returns 201 with created_data
12. Frontend closes modal, calls fetchVocabulary() to refresh table
```

### Flow 3: App initialization with existing token

```
1. main.tsx renders <AuthProvider> wrapping <App>
2. AuthProvider useEffect checks localStorage for 'access_token'
3. If found, sets token state and calls api.get('/api/me')
4. If /api/me returns 200, sets user state from response
5. If /api/me returns 401 (expired token), clears token from state and localStorage
6. Sets isLoading = false
7. <App /> renders, routes resolved
```

---

## Error Handling

### Frontend Error Handling

| Scenario | Handling |
|---|---|
| No JWT token stored | Axios sends request without Authorization header. Backend returns 401. Catch block logs error; page renders with empty/default data. |
| Expired JWT token | Same as above. AuthProvider's initial /api/me call detects this and clears the stale token. |
| Network error (backend down) | Axios throws. Catch block logs error; page renders with empty/default data. |
| CSV missing required columns | PapaParse returns data, validation detects missing columns, `alert()` shown, no API call made. |
| CSV parse error (malformed file) | PapaParse `error` callback fires, promise rejects, catch block shows error alert. |
| Backend validation error (POST /api/words) | Backend returns 400 with `{ "error": "..." }`. Catch block reads `error.response.data.error` and shows it in alert. |
| DELETE word fails | Axios throws, catch block shows "Failed to delete word" alert. |

### Backend Error Handling

No changes to existing backend error handling. The existing pattern (try/except with rollback, returning `{ "error": "..." }` with appropriate HTTP status) is preserved.

---

## Security Considerations

1. **JWT stored in localStorage**: This is acceptable for the MVP. `localStorage` is vulnerable to XSS attacks. For production hardening in a future milestone, consider migrating to `httpOnly` cookies with CSRF protection.

2. **No token refresh**: If the JWT expires, the user must log in again. Token refresh is out of scope for M0.

3. **CORS**: The `flask-cors` package is already in `backend/requirements.txt`. If CORS is not yet initialized in `app.py`, it may need to be added. However, during development the Vite proxy handles same-origin concerns, so CORS is only relevant for production deployments.

4. **Input validation for CSV import**: The frontend validates CSV structure before sending. The backend already validates that `word`, `pinyin`, and `meaning` are present in each item (they are required fields on the Word model). A `KeyError` is raised if they are missing, which the existing try/except handles.

---

## Testing Strategy

### Backend Tests (pytest)

| Test | Type | What it verifies |
|---|---|---|
| `test_health_check` | Smoke | `GET /api/` returns 200 |
| `test_create_user_and_login` | Integration | `POST /api/users` creates user, `POST /api/token` returns JWT |
| `test_get_words_requires_auth` | Integration | `GET /api/words` without token returns 401 |
| `test_create_and_list_words` | Integration | `POST /api/words` with token creates words, `GET /api/words` returns them including `source_name` |

The smoke test is the minimum required for M0. The integration tests are recommended but not strictly required.

### Frontend Tests (Vitest + React Testing Library)

| Test | Type | What it verifies |
|---|---|---|
| `App renders without crashing` | Smoke | `<App />` mounts and renders the Welcome page text |

The smoke test is the minimum required for M0. Additional component-level tests can be added in future milestones.

---

## Technical Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Flask-RESTful `Api(prefix=...)` doesn't work as expected | Low | High | Verified in Flask-RESTful docs: `prefix` parameter is supported. Fallback: use a Blueprint with `url_prefix='/api'` and register the Api on the Blueprint. |
| `papaparse` typing issues with TypeScript | Low | Low | `@types/papaparse` exists and is well-maintained. The Promise wrapper pattern for `Papa.parse` is a well-known approach. |
| Existing tests fail after API prefix change | N/A | N/A | There are no existing tests. This is a greenfield test setup. |
| SQLite vs PostgreSQL behavior differences in tests | Medium | Medium | For M0 smoke tests, the queries are simple enough that SQLite and PostgreSQL behave identically. For more complex tests in future milestones, consider using a test PostgreSQL database via Docker. |
| `tsconfig.json` `include` path mismatch | Medium | Low | The `include` currently says `"src"` but frontend source is at `frontend/src/`. Fixing to `"frontend/src"` is part of the test infra setup. If this breaks the build, we investigate the Vite/TypeScript integration. |

---

## Alternatives Considered

### API Prefix: Vite proxy rewrite vs. Flask route prefix
**Alternative**: Add a `rewrite` rule to the Vite proxy that strips `/api` before forwarding:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:5000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```
**Why rejected**: This creates a divergence between dev and production. In production (no Vite proxy), the backend must serve at `/api/*` anyway. Adding the prefix on Flask is simpler and works in both environments.

### Auth header injection: Axios interceptor vs. custom fetch wrapper
**Alternative**: Create a `fetchWithAuth()` wrapper around the native `fetch` API.
**Why rejected**: Axios is already a dependency, provides interceptors natively, and has better ergonomics (automatic JSON parsing, error handling via exceptions). Migrating to Axios reduces code in each component.

### CSV parsing: Frontend (PapaParse) vs. Backend (Python csv module)
**Alternative**: Send the raw CSV file to the backend via `multipart/form-data` and parse it server-side.
**Why rejected**: The existing backend `POST /api/words` endpoint expects JSON. Adding a new file upload endpoint is more scope than needed. Client-side parsing with PapaParse is simpler, keeps the backend API clean, and allows immediate validation feedback to the user.

### Shared types: Single file vs. per-model files
**Alternative**: Create `frontend/src/types/word.ts`, `frontend/src/types/user.ts`, etc.
**Why rejected**: With only 4 interfaces, a single `api.ts` file is simpler and easier to find. If the number of types grows significantly, refactoring to per-model files is straightforward.
