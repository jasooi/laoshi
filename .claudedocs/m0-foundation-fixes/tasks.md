# Milestone 0: Foundation Fixes -- Task Breakdown

## Task Overview

**Total tasks**: 27 subtasks across 6 phases
**Estimated complexity**: Medium -- mostly wiring changes and infrastructure setup, one schema migration, no complex business logic.
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be done in order unless noted otherwise.

---

## Prerequisites

Before starting any tasks:

1. Ensure the backend virtual environment is active and `backend/requirements.txt` dependencies are installed.
2. Ensure `npm install` has been run in the repo root (where `package.json` lives).
3. Ensure PostgreSQL is running and the `DATABASE_URI` in `.env` is valid.
4. Ensure the existing app runs (`python backend/app.py` starts Flask on port 5000, `npm run dev` starts Vite on port 5173).

---

## Phase 1: Backend Model & API Prefix

This phase modifies the backend only. No frontend changes.

---

### T-001: Add `/api` prefix to Flask-RESTful Api

**Description**: In `backend/app.py`, modify the `register_resources` function to pass `prefix='/api'` to the `Api` constructor. Also modify `create_app()` to accept an optional `config_class` parameter (needed later for test infrastructure).

**Files affected**:
- `backend/app.py`

**Changes**:

1. In `register_resources(app)`, change `api = Api(app)` to `api = Api(app, prefix='/api')`. No other lines in this function change -- the resource paths like `/words`, `/token`, etc. stay as-is; the prefix is prepended automatically.

2. In `create_app()`, add an optional `config_class` parameter:
   ```python
   def create_app(config_class=None):
       app = Flask(__name__)
       if config_class is None:
           config_class = Config
       app.config.from_object(config_class)
       register_extensions(app)
       register_resources(app)
       return app
   ```

**Acceptance criteria**:
- [x] `GET http://localhost:5000/api/` returns the HomeResource response (string: "You have successfully called this API. Congrats!")
- [x] `GET http://localhost:5000/words` returns 404 (old path no longer works)
- [x] `GET http://localhost:5000/api/words` returns 401 (JWT required, no token provided) -- this confirms the route exists
- [x] `POST http://localhost:5000/api/token` with valid credentials returns `{ "access_token": "..." }`
- [x] `create_app()` still works with no arguments (default to `Config`)
- [x] `create_app(config_class=SomeConfig)` uses the provided config

**Dependencies**: None

**Testing**: Manual verification with `curl` or a REST client. Automated tests come in Phase 5.

---

### T-002: Add `source_name` column to Word model

**Description**: Add a nullable `source_name` column to the `Word` model and update `format_data()` to include it in the response.

**Files affected**:
- `backend/models.py`

**Changes**:

1. Add to the `Word` class, after the `confidence_score` column:
   ```python
   source_name = db.Column(db.String(200), nullable=True, default=None)
   ```

2. Update `format_data()` to include `source_name`:
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
           'source_name': self.source_name,
       }
   ```

**Acceptance criteria**:
- [x] The `Word` model has a `source_name` attribute.
- [x] `format_data()` returns a dict that includes the key `source_name`.
- [x] Existing `Word` instances (with no `source_name` set) return `source_name: None` in `format_data()`.

**Dependencies**: None (can be done in parallel with T-001)

**Testing**: Verified via T-003 migration and T-004 resource test.

---

### T-003: Generate and apply database migration for `source_name`

**Description**: Use Flask-Migrate to generate a migration for the new `source_name` column and apply it.

**Files affected**:
- `backend/migrations/versions/` (new migration file, auto-generated)

**Steps**:
1. From the `backend/` directory, run: `flask db migrate -m "add source_name to word"`
2. Verify the generated migration adds a `source_name` column of type `VARCHAR(200)`, nullable.
3. Apply: `flask db upgrade`

**Acceptance criteria**:
- [x] The `word` table in PostgreSQL has a `source_name` column.
- [x] Existing rows have `source_name = NULL`.
- [x] The migration is reversible (`flask db downgrade` removes the column).

**Dependencies**: T-002

**Testing**: Connect to the database and run `\d word` (psql) or equivalent to confirm the column exists.

---

### T-004: Update WordListResource.post and WordResource.put for `source_name`

**Description**: Update the backend resource handlers to accept and store `source_name`.

**Files affected**:
- `backend/resources.py`

**Changes**:

1. In `WordListResource.post`, update the Word constructor call inside the `for item in data` loop:
   ```python
   word_to_add = Word(
       word=item["word"],
       pinyin=item["pinyin"],
       meaning=item["meaning"],
       source_name=item.get("source_name"),
       user_id=vc_user.id
   )
   ```

2. In `WordResource.put`, update the `allowable_fields` list:
   ```python
   allowable_fields = ["word", "pinyin", "meaning", "confidence_score", "source_name"]
   ```

**Acceptance criteria**:
- [x] `POST /api/words` with a JSON body `[{"word": "...", "pinyin": "...", "meaning": "...", "source_name": "My CSV"}]` creates a word with `source_name = "My CSV"`.
- [x] `POST /api/words` with a JSON body `[{"word": "...", "pinyin": "...", "meaning": "..."}]` (no `source_name`) creates a word with `source_name = None`.
- [x] `PUT /api/words/<id>` with `{"source_name": "Updated"}` updates the word's `source_name`.

**Dependencies**: T-001, T-002, T-003

**Testing**: Manual verification with `curl` or REST client, passing a JWT token.

---

## Phase 2: Frontend Infrastructure (Axios, Auth, Types)

This phase creates the shared frontend infrastructure. No page component changes yet.

---

### T-005: Create centralized Axios instance

**Description**: Create a new file `frontend/src/lib/api.ts` that exports a pre-configured Axios instance with a request interceptor for JWT auth.

**Files affected**:
- `frontend/src/lib/api.ts` (new file)

**Content**:
```typescript
import axios from 'axios'

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
```

**Acceptance criteria**:
- [x] File exists at `frontend/src/lib/api.ts`.
- [x] Exports a default Axios instance.
- [x] When `localStorage` has `access_token`, the interceptor adds `Authorization: Bearer <token>` to requests.
- [x] When `localStorage` has no `access_token`, no `Authorization` header is added.
- [x] TypeScript compiles without errors.

**Dependencies**: None (Axios is already in `package.json`)

**Testing**: Verified indirectly when page components use it in Phase 3.

---

### T-006: Create AuthContext and AuthProvider

**Description**: Create the auth context at `frontend/src/contexts/AuthContext.tsx` with `login`, `logout`, token persistence, and user state.

**Files affected**:
- `frontend/src/contexts/AuthContext.tsx` (new file)

**Content**: See design doc, Section 5 for full implementation.

Key behaviors:
- On mount, check `localStorage` for `access_token`. If found, set token state and call `GET /api/me` to validate and fetch user info. If `/api/me` fails, clear the stale token.
- `login(username, password)`: POST to `/api/token`, store token, fetch user info via `/api/me`.
- `logout()`: Clear token from state and `localStorage`, clear user state.
- Export `useAuth()` hook.

**Acceptance criteria**:
- [x] `AuthProvider` is a valid React component that wraps children.
- [x] `useAuth()` returns `{ token, user, isAuthenticated, isLoading, login, logout }`.
- [x] After `login()`, `localStorage` contains `access_token`.
- [x] After `logout()`, `localStorage` does not contain `access_token`.
- [x] If `localStorage` has a stale/invalid token on mount, it is cleared.
- [x] TypeScript compiles without errors.

**Dependencies**: T-005

**Testing**: Verified indirectly via integration in T-007 and when page components use auth in Phase 3.

---

### T-007: Wrap App with AuthProvider in main.tsx

**Description**: Import `AuthProvider` in `frontend/src/main.tsx` and wrap `<App />`.

**Files affected**:
- `frontend/src/main.tsx`

**Changes**:
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

**Acceptance criteria**:
- [x] The app starts without errors (`npm run dev`).
- [x] React DevTools shows `AuthProvider` in the component tree wrapping `App`.
- [x] `useAuth()` is callable from any component within the app tree.

**Dependencies**: T-006

**Testing**: Start the dev server, open the browser, confirm no console errors.

---

### T-008: Create shared TypeScript types file

**Description**: Create `frontend/src/types/api.ts` with interfaces for all backend response shapes.

**Files affected**:
- `frontend/src/types/api.ts` (new file)

**Content**:
```typescript
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
  session_start_ds: string
  session_end_ds: string | null
  user_id: number
}

export interface SessionWord {
  id: string
  is_skipped: boolean
  session_notes: string | null
}
```

**Acceptance criteria**:
- [x] File exists at `frontend/src/types/api.ts`.
- [x] All four interfaces are exported.
- [x] `Word` interface matches `Word.format_data()` output exactly (including `source_name`).
- [x] TypeScript compiles without errors.

**Dependencies**: None (can be done in parallel with T-005, T-006)

**Testing**: TypeScript compilation check.

---

### T-009: Install PapaParse

**Description**: Install `papaparse` and its TypeScript types as project dependencies.

**Files affected**:
- `package.json` (dependencies updated by npm)
- `package-lock.json` (updated by npm)

**Steps**:
```
npm install papaparse
npm install -D @types/papaparse
```

**Acceptance criteria**:
- [x] `papaparse` appears in `dependencies` in `package.json`.
- [x] `@types/papaparse` appears in `devDependencies` in `package.json`.
- [x] `import Papa from 'papaparse'` compiles without TypeScript errors.

**Dependencies**: None

**Testing**: TypeScript compilation check.

---

## Phase 3: Frontend Page Component Updates

This phase updates each page component to use the new infrastructure.

---

### T-010: Update Vocabulary.tsx -- remove local interface, use shared Word type

**Description**: Remove the local `VocabularyWord` interface from `Vocabulary.tsx` and import `Word` from the shared types. Update all type references.

**Files affected**:
- `frontend/src/pages/Vocabulary.tsx`

**Changes**:
1. Remove the `VocabularyWord` interface (lines 3-9 of current file).
2. Add `import { Word } from '../types/api'`.
3. Replace all `VocabularyWord` references with `Word`:
   - `useState<VocabularyWord[]>([])` -> `useState<Word[]>([])`
4. Update function parameter types:
   - `handleDelete(wordId: string)` -> `handleDelete(wordId: number)`
   - `handleEdit(wordId: string)` -> `handleEdit(wordId: number)`

**Acceptance criteria**:
- [x] No `VocabularyWord` interface exists in the file.
- [x] `Word` is imported from `../types/api`.
- [x] All state types use `Word`.
- [x] `handleDelete` and `handleEdit` accept `number` parameter.
- [x] TypeScript compiles without errors.

**Dependencies**: T-008

**Testing**: TypeScript compilation check.

---

### T-011: Update Vocabulary.tsx -- fix field name references in JSX

**Description**: Update all JSX references from old field names to new field names.

**Files affected**:
- `frontend/src/pages/Vocabulary.tsx`

**Changes**:
1. In the `filteredWords` filter function (currently line ~52):
   - `word.definition.toLowerCase()` -> `word.meaning.toLowerCase()`
2. In the table body (currently line ~243):
   - `{word.definition}` -> `{word.meaning}`
3. In the table body (currently line ~244):
   - `{word.sourceName}` -> `{word.source_name}`

**Acceptance criteria**:
- [x] No references to `definition` or `sourceName` remain in the file.
- [x] The search filter works on the `meaning` field.
- [x] The table displays `meaning` and `source_name` in the correct columns.
- [x] TypeScript compiles without errors.

**Dependencies**: T-010

**Testing**: TypeScript compilation; visual inspection in browser.

---

### T-012: Update Vocabulary.tsx -- migrate fetch calls to Axios

**Description**: Replace all `fetch()` calls with the centralized Axios instance. Update the API paths from `/api/vocabulary` to `/api/words`.

**Files affected**:
- `frontend/src/pages/Vocabulary.tsx`

**Changes**:

1. Add import: `import api from '../lib/api'`

2. Rewrite `fetchVocabulary()`:
   ```typescript
   const fetchVocabulary = async () => {
     setLoading(true)
     try {
       const response = await api.get('/api/words')
       setWords(response.data)
     } catch (error) {
       console.error('Error fetching vocabulary:', error)
       setWords([])
     } finally {
       setLoading(false)
     }
   }
   ```
   Note: Axios throws on non-2xx status, so the `if (response.ok)` pattern is replaced with try/catch. The backend returns an array directly on success; on 404 (no words), the catch block sets empty array.

3. Rewrite `handleDelete()`:
   ```typescript
   const handleDelete = async (wordId: number) => {
     if (!confirm('Are you sure you want to delete this word?')) return
     try {
       await api.delete(`/api/words/${wordId}`)
       setWords(words.filter(w => w.id !== wordId))
     } catch (error) {
       console.error('Error deleting word:', error)
       alert('Failed to delete word')
     }
   }
   ```

**Acceptance criteria**:
- [x] No `fetch()` calls remain in the file (except `handleUpload` which is done in T-013).
- [x] `fetchVocabulary` calls `api.get('/api/words')`.
- [x] `handleDelete` calls `api.delete('/api/words/${wordId}')`.
- [x] Auth header is automatically attached by the Axios interceptor.
- [x] Error handling uses try/catch (Axios pattern), not `response.ok` (fetch pattern).
- [x] TypeScript compiles without errors.

**Dependencies**: T-005, T-010

**Testing**: Start both servers. With a valid JWT in localStorage (manually set for now), navigate to `/vocabulary` and confirm words load. Test delete.

---

### T-013: Update Vocabulary.tsx -- rewrite handleUpload with PapaParse

**Description**: Replace the FormData-based upload with client-side CSV parsing via PapaParse, then send JSON to `POST /api/words`.

**Files affected**:
- `frontend/src/pages/Vocabulary.tsx`

**Changes**:

1. Add import: `import Papa from 'papaparse'`

2. Rewrite `handleUpload()` (see design doc, Section 8 for full implementation):
   - Parse CSV using `Papa.parse` with `header: true, skipEmptyLines: true`.
   - Validate required columns (`word`, `pinyin`, `meaning`) case-insensitively.
   - Validate at least one data row exists.
   - Map rows to `{ word, pinyin, meaning, source_name }`.
   - Call `api.post('/api/words', words)`.
   - On success: close modal, clear state, call `fetchVocabulary()`.
   - On failure: show error message from backend or generic error.

**Acceptance criteria**:
- [x] No `FormData` usage remains in the file.
- [x] CSV is parsed client-side using PapaParse.
- [x] Required columns are validated before API call.
- [x] Empty CSV shows an error message.
- [x] CSV with wrong column names shows an error listing missing columns.
- [x] Valid CSV with correct columns sends JSON POST to `/api/words`.
- [x] `source_name` from the input field is attached to every word.
- [x] On success, modal closes and table refreshes.
- [x] On failure, error message is shown.
- [x] TypeScript compiles without errors.

**Dependencies**: T-009, T-012

**Testing**: Create a test CSV file with headers `word,pinyin,meaning` and sample rows. Upload via the UI. Verify words appear in the table with the correct `source_name`.

---

### T-014: Update Home.tsx -- migrate fetch calls to Axios and fix API path

**Description**: Replace `fetch()` calls with the centralized Axios instance. Update the vocabulary API path.

**Files affected**:
- `frontend/src/pages/Home.tsx`

**Changes**:

1. Add import: `import api from '../lib/api'`

2. Rewrite the `fetchStats` function:
   ```typescript
   const fetchStats = async () => {
     try {
       const vocabResponse = await api.get('/api/words')
       const vocabData = vocabResponse.data
       setTotalWords(Array.isArray(vocabData) ? vocabData.length : 0)
       setWordsWaiting(Array.isArray(vocabData) ? vocabData.length : 0)
     } catch (error) {
       console.error('Error fetching vocabulary:', error)
     }

     try {
       const progressResponse = await api.get('/api/progress/stats')
       const progressData = progressResponse.data
       setWordsToday(progressData.wordsToday || 0)
       setMasteryProgress(progressData.masteryProgress || 0)
     } catch (error) {
       // /api/progress/stats does not exist yet -- silently use defaults (0)
       console.log('Progress stats not available yet')
     }

     setLoading(false)
   }
   ```
   Note: The two API calls are in separate try/catch blocks so a failure in one does not prevent the other from running.

**Acceptance criteria**:
- [x] No `fetch()` calls remain in the file.
- [x] Vocabulary data is fetched from `/api/words`.
- [x] `totalWords` and `wordsWaiting` reflect the actual word count from the backend.
- [x] The `/api/progress/stats` call fails silently (endpoint does not exist yet), leaving `wordsToday` and `masteryProgress` at 0.
- [x] Auth header is automatically attached.
- [x] The page renders without errors or crashes.
- [x] TypeScript compiles without errors.

**Dependencies**: T-005

**Testing**: Start both servers. Set a valid JWT in localStorage. Navigate to `/home`. Confirm total word count matches the database.

---

### T-015: Update Practice.tsx -- remove local interface, use shared Word type

**Description**: Remove the local `VocabularyWord` interface from `Practice.tsx` and import `Word` from shared types. Update all state types and mock data objects.

**Files affected**:
- `frontend/src/pages/Practice.tsx`

**Changes**:
1. Remove the `VocabularyWord` interface (lines 4-10 of current file).
2. Add `import { Word } from '../types/api'`.
3. Replace all `VocabularyWord` references with `Word`:
   - `useState<VocabularyWord | null>(null)` -> `useState<Word | null>(null)`
   - `setPracticedWords` and `setSkippedWords` state types: `useState<VocabularyWord[]>([])` -> `useState<Word[]>([])`
4. Update all mock word objects to use the `Word` shape:
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
   There are three mock word instances in the file (the fallback mock in the `if (!response.ok)` branch and two in catch blocks). All three must be updated.

**Acceptance criteria**:
- [x] No `VocabularyWord` interface exists in the file.
- [x] `Word` is imported from `../types/api`.
- [x] All state types use `Word`.
- [x] All mock word objects use `Word` field names (`meaning`, `status`, `confidence_score`, `source_name`).
- [x] TypeScript compiles without errors.

**Dependencies**: T-008

**Testing**: TypeScript compilation check.

---

### T-016: Update Practice.tsx -- fix field name references in JSX

**Description**: Update JSX references from old field names to new field names in Practice.tsx.

**Files affected**:
- `frontend/src/pages/Practice.tsx`

**Changes**:
1. Line ~277 (translation toggle): `{currentWord.definition}` -> `{currentWord.meaning}`
2. Line ~283 (confidence badge): `{currentWord.confidenceLevel}` -> `{currentWord.status}`

**Acceptance criteria**:
- [x] No references to `definition` or `confidenceLevel` remain in the file.
- [x] The translation toggle shows `currentWord.meaning`.
- [x] The confidence badge shows `currentWord.status`.
- [x] TypeScript compiles without errors.

**Dependencies**: T-015

**Testing**: Visual inspection in browser.

---

### T-017: Update Practice.tsx -- migrate fetch calls to Axios

**Description**: Replace all `fetch()` calls with the centralized Axios instance. Keep the existing API paths (`/api/practice/next-word`, `/api/practice/evaluate`) since these endpoints will be built in future milestones. The existing fallback/mock behavior is preserved.

**Files affected**:
- `frontend/src/pages/Practice.tsx`

**Changes**:

1. Add import: `import api from '../lib/api'`

2. Rewrite `fetchNextWord()`:
   ```typescript
   const fetchNextWord = async () => {
     setLoading(true)
     try {
       const response = await api.get('/api/practice/next-word')
       const data = response.data
       setCurrentWord(data)
       const promptMessage: Message = { ... }
       setMessages((prev) => [...prev, promptMessage])
     } catch (error) {
       // Fallback: endpoint does not exist yet, use mock data
       console.log('API not available, using mock data')
       const mockWord: Word = { ... }
       setCurrentWord(mockWord)
       const promptMessage: Message = { ... }
       setMessages((prev) => [...prev, promptMessage])
     } finally {
       setLoading(false)
     }
   }
   ```

3. Rewrite `handleSubmit()` similarly -- the `fetch('/api/practice/evaluate', ...)` call becomes `api.post('/api/practice/evaluate', { wordId: currentWord.id, sentence: inputText })`. The catch block provides a fallback response message.

**Acceptance criteria**:
- [x] No `fetch()` calls remain in the file.
- [x] All API calls use the centralized `api` instance.
- [x] Auth header is automatically attached.
- [x] The page renders with mock data when the backend endpoints are not available (expected for M0).
- [x] No errors or crashes in the console (just a `console.log` for the fallback).
- [x] TypeScript compiles without errors.

**Dependencies**: T-005, T-015

**Testing**: Start the dev server. Navigate to `/practice`. The page should render with the mock word card. No unhandled errors in the console.

---

## Phase 4: Frontend Test Infrastructure

---

### T-018: Install Vitest and React Testing Library

**Description**: Install the test framework packages as dev dependencies.

**Files affected**:
- `package.json` (updated by npm)
- `package-lock.json` (updated by npm)

**Steps**:
```
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

**Acceptance criteria**:
- [x] `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` appear in `devDependencies`.

**Dependencies**: None

**Testing**: Packages install without errors.

---

### T-019: Configure Vitest in vite.config.ts

**Description**: Add the `test` configuration block to the existing `vite.config.ts` and create the test setup file.

**Files affected**:
- `vite.config.ts` (at repo root)
- `frontend/src/test/setup.ts` (new file)

**Changes to `vite.config.ts`**:

Add `/// <reference types="vitest" />` at the top of the file and a `test` block:

```typescript
/// <reference types="vitest" />
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

**New file `frontend/src/test/setup.ts`**:
```typescript
import '@testing-library/jest-dom'
```

**Acceptance criteria**:
- [x] `vite.config.ts` has a `test` block with `environment: 'jsdom'`.
- [x] `frontend/src/test/setup.ts` exists and imports `@testing-library/jest-dom`.
- [x] Running `npx vitest --run` (with no test files yet) exits cleanly with "no tests found" or similar.

**Dependencies**: T-018

**Testing**: Run `npx vitest --run` to verify configuration loads.

---

### T-020: Add `test` script to package.json

**Description**: Add a `test` script so that `npm test` runs Vitest.

**Files affected**:
- `package.json`

**Changes**: Add to the `scripts` section:
```json
"test": "vitest"
```

**Acceptance criteria**:
- [x] `npm test` starts Vitest in watch mode.
- [x] `npm test -- --run` runs tests and exits.

**Dependencies**: T-019

**Testing**: Run `npm test -- --run`.

---

### T-021: Update tsconfig.json for test support

**Description**: Update the TypeScript configuration to include the frontend source directory correctly and add Vitest globals type support.

**Files affected**:
- `tsconfig.json` (at repo root)

**Changes**:
1. Update `include` to reference the actual frontend source path: `"frontend/src"` (instead of `"src"`).
2. Add `"types": ["vitest/globals"]` to `compilerOptions` to support Vitest globals (`describe`, `it`, `expect`) without explicit imports.

**Acceptance criteria**:
- [x] `tsconfig.json` `include` contains `"frontend/src"`.
- [x] `compilerOptions.types` contains `"vitest/globals"`.
- [x] `npm run dev` still works (Vite dev server starts without TypeScript errors).
- [x] TypeScript recognizes `describe`, `it`, `expect` in test files without imports.

**Dependencies**: T-018

**Testing**: Start dev server; verify no regressions.

---

### T-022: Write frontend smoke test

**Description**: Create a smoke test that renders the `<App />` component and verifies it does not crash.

**Files affected**:
- `frontend/src/test/App.test.tsx` (new file)

**Content**:
```typescript
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByText('Welcome to the classroom')).toBeInTheDocument()
  })
})
```

Note: `<App />` uses `<BrowserRouter>` internally, so no extra router wrapper is needed. The default route `/` renders `<Welcome />` which contains the text "Welcome to the classroom".

**Acceptance criteria**:
- [x] `npm test -- --run` passes with 1 test passing.
- [x] The test renders `<App />` and finds the expected text.
- [x] No console errors during the test run.

**Dependencies**: T-019, T-020, T-021

**Testing**: Run `npm test -- --run`.

---

## Phase 5: Backend Test Infrastructure

---

### T-023: Add pytest to backend requirements

**Description**: Add `pytest` to `backend/requirements.txt` and install it.

**Files affected**:
- `backend/requirements.txt`

**Changes**: Add at the end of the file:
```
# Testing
pytest>=7.0.0
```

**Steps**: Install via `pip install -r requirements.txt` (from the `backend/` directory).

**Acceptance criteria**:
- [x] `pytest` appears in `backend/requirements.txt`.
- [x] `python -m pytest --version` runs successfully in the backend virtual environment.

**Dependencies**: None

**Testing**: Version check command.

---

### T-024: Add TestConfig class to backend config

**Description**: Add a `TestConfig` class to `backend/config.py` that overrides the database URI to use SQLite in-memory.

**Files affected**:
- `backend/config.py`

**Changes**: Add after the `Config` class:
```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-secret-key'
```

**Acceptance criteria**:
- [x] `TestConfig` exists in `backend/config.py`.
- [x] `TestConfig.SQLALCHEMY_DATABASE_URI` is `'sqlite:///:memory:'`.
- [x] `TestConfig.TESTING` is `True`.
- [x] `TestConfig` inherits from `Config` (gets other defaults).

**Dependencies**: None

**Testing**: Importable without errors: `from config import TestConfig`

---

### T-025: Create backend test fixtures (conftest.py)

**Description**: Create the pytest fixtures for the Flask test app, database, and test client.

**Files affected**:
- `backend/tests/__init__.py` (new, empty file)
- `backend/tests/conftest.py` (new file)

**Content of `conftest.py`**:
```python
import pytest
import sys
import os

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

**Acceptance criteria**:
- [x] `backend/tests/__init__.py` exists (can be empty).
- [x] `backend/tests/conftest.py` exists with `app`, `db`, and `client` fixtures.
- [x] Running `python -m pytest tests/` from the `backend/` directory discovers the conftest without import errors.

**Dependencies**: T-001 (for `create_app(config_class=...)` parameter), T-023, T-024

**Testing**: Run `python -m pytest tests/ --collect-only` from `backend/` to verify fixture discovery.

---

### T-026: Write backend smoke test

**Description**: Create a smoke test that verifies the Flask app starts and the health-check endpoint works.

**Files affected**:
- `backend/tests/test_smoke.py` (new file)

**Content**:
```python
def test_health_check(client):
    """GET /api/ should return 200 with the health check message."""
    response = client.get('/api/')
    assert response.status_code == 200


def test_words_requires_auth(client):
    """GET /api/words without a JWT should return 401."""
    response = client.get('/api/words')
    assert response.status_code == 401
```

**Acceptance criteria**:
- [x] Running `python -m pytest tests/` from `backend/` passes with 2 tests.
- [x] `test_health_check` confirms `GET /api/` returns 200.
- [x] `test_words_requires_auth` confirms `GET /api/words` without a token returns 401.
- [x] Tests run against SQLite in-memory (no PostgreSQL required).

**Dependencies**: T-025

**Testing**: Run `python -m pytest tests/ -v` from `backend/`.

---

## Phase 6: Integration Verification

---

### T-027: End-to-end manual verification

**Description**: Verify the complete data flow works end-to-end by manually testing all updated flows.

**Files affected**: None (this is a verification task, not a code task).

**Steps**:

1. **Start both servers**: `python backend/app.py` and `npm run dev`.

2. **Create a test user** (via curl or REST client):
   ```
   POST http://localhost:5000/api/users
   Body: { "username": "testuser", "email": "test@example.com", "password": "password123", "preferred_name": "Test" }
   ```

3. **Log in** (via curl or REST client):
   ```
   POST http://localhost:5000/api/token
   Body: { "username": "testuser", "password": "password123" }
   ```
   Copy the `access_token`.

4. **Set token in browser**: Open browser DevTools console on the running Vite app (`http://localhost:5173`) and run:
   ```javascript
   localStorage.setItem('access_token', '<paste-token-here>')
   ```
   Refresh the page.

5. **Test Vocabulary page**:
   - Navigate to `/vocabulary`.
   - Confirm the page loads without errors (empty state shown if no words).
   - Click "Import from file".
   - Select a test CSV with columns `word,pinyin,meaning`.
   - Enter a source name.
   - Click "Attach File".
   - Confirm words appear in the table with correct meaning and source name.
   - Delete a word. Confirm it is removed from the table.

6. **Test Home page**:
   - Navigate to `/home`.
   - Confirm `Total: X words` shows the correct count.
   - Confirm the page does not crash (progress stats will show 0).

7. **Test Practice page**:
   - Navigate to `/practice`.
   - Confirm the page renders with mock data (since `/api/practice/next-word` does not exist yet).
   - Confirm no console errors related to field name mismatches.

8. **Test auth persistence**:
   - Navigate between pages. Confirm the token is not lost.
   - Clear localStorage (`localStorage.removeItem('access_token')`). Refresh.
   - Confirm API calls fail gracefully (empty data, no crashes).

9. **Run all tests**:
   - From repo root: `npm test -- --run` (frontend smoke test passes).
   - From `backend/`: `python -m pytest tests/ -v` (backend smoke tests pass).

**Acceptance criteria**:
- [x] Vocabulary page loads words from the real backend.
- [x] CSV import creates words with correct `source_name`.
- [x] Word deletion works.
- [x] Home page shows correct total word count.
- [x] Practice page renders without field-name errors.
- [x] Auth token persists across page navigations.
- [x] Auth token absence is handled gracefully.
- [x] All frontend tests pass (`npm test -- --run`).
- [x] All backend tests pass (`python -m pytest tests/`).

**Dependencies**: All previous tasks (T-001 through T-026).

**Testing**: This task IS the testing.

---

## Definition of Done

Milestone 0 is complete when ALL of the following are true:

1. **Backend API prefix**: All Flask routes are served under `/api/*`. The old routes (without prefix) return 404.
2. **Backend `source_name`**: The `Word` model has a `source_name` column. `format_data()` includes it. `POST /api/words` accepts it. `PUT /api/words/<id>` can update it.
3. **Database migration**: A migration for `source_name` has been generated and applied.
4. **Centralized Axios instance**: All frontend API calls use `frontend/src/lib/api.ts` instead of raw `fetch()`. The Axios interceptor attaches the JWT `Authorization` header automatically.
5. **Auth context**: `AuthProvider` wraps the app. `useAuth()` provides `login`, `logout`, `token`, `user`, `isAuthenticated`, `isLoading`.
6. **Shared TypeScript types**: `frontend/src/types/api.ts` defines `Word`, `User`, `UserSession`, `SessionWord` interfaces matching backend response shapes.
7. **Vocabulary page**: Fetches words from `/api/words`, displays `meaning` and `source_name`, delete works, CSV upload parses client-side and sends JSON.
8. **Home page**: Fetches word count from `/api/words`, handles missing `/api/progress/stats` gracefully.
9. **Practice page**: Uses `Word` type with correct field names (`meaning`, `status`), falls back to mock data for non-existent endpoints.
10. **Frontend tests**: Vitest configured, smoke test passes (`npm test -- --run`).
11. **Backend tests**: pytest configured, smoke tests pass (`python -m pytest tests/`).
12. **No regressions**: The app starts without errors, all pages render, no TypeScript compilation errors.
