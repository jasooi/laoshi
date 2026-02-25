# Milestone 1: Authentication & Onboarding -- Task Breakdown

## Task Overview

**Total tasks**: 22 tasks across 5 phases
**Estimated complexity**: Medium-High -- backend token infrastructure is new territory for this codebase; frontend work is mostly new components following established patterns.
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be done in order unless noted otherwise.

**Scope note**: Tasks 1.1-1.3 (backend auth endpoints) and 1.8 (onboarding flow) from the PROJECT_PLAN are already complete. This task breakdown covers the remaining work: secure token management, frontend auth pages, protected routes, and logout.

---

## Prerequisites

Before starting any tasks:

1. Ensure the backend virtual environment is active and `backend/requirements.txt` dependencies are installed.
2. Ensure `npm install` has been run in the repo root.
3. Ensure PostgreSQL is running and the `DATABASE_URI` in `.env` is valid.
4. Ensure both servers start: `python backend/app.py` (Flask on port 5000), `npm run dev` (Vite on port 5173).
5. Ensure existing backend tests pass: `cd backend && python -m pytest tests/ -v`.
6. Ensure existing frontend tests pass: `npm test -- --run`.

---

## Phase 1: Backend Token Infrastructure

This phase adds the refresh token infrastructure to the backend. No frontend changes.

---

### T-001: Configure JWT token expiry and cookie settings in config.py

**Description**: Add explicit token expiry settings and cookie configuration to the Flask `Config` class so that Flask-JWT-Extended issues short-lived access tokens and long-lived refresh tokens as HttpOnly cookies.

**Files affected**:
- `backend/config.py`

**Changes**:

1. Add `from datetime import timedelta` at the top of the file.

2. Add the following settings to the `Config` class:
   ```python
   # JWT Token Expiry
   JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
   JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

   # JWT Token Locations -- accept access tokens from headers, refresh from cookies
   JWT_TOKEN_LOCATION = ['headers', 'cookies']

   # JWT Cookie Settings
   JWT_REFRESH_COOKIE_PATH = '/api/token'
   JWT_COOKIE_SECURE = False               # Set True in production (requires HTTPS)
   JWT_COOKIE_SAMESITE = 'Strict'
   JWT_COOKIE_CSRF_PROTECT = False          # SameSite=Strict is sufficient for MVP
   ```

3. Ensure `TestConfig` inherits these settings and explicitly sets `JWT_COOKIE_SECURE = False`.

**Acceptance criteria**:
- `Config.JWT_ACCESS_TOKEN_EXPIRES` is `timedelta(minutes=15)`.
- `Config.JWT_REFRESH_TOKEN_EXPIRES` is `timedelta(days=7)`.
- `Config.JWT_TOKEN_LOCATION` is `['headers', 'cookies']`.
- `Config.JWT_COOKIE_SECURE` is `False` (development).
- `Config.JWT_COOKIE_SAMESITE` is `'Strict'`.
- `Config.JWT_COOKIE_CSRF_PROTECT` is `False`.
- `TestConfig` inherits all settings and `JWT_COOKIE_SECURE = False`.
- The Flask app starts without errors after these changes.

**Dependencies**: None

**Testing**: Start the Flask app, verify no startup errors. Automated tests in Phase 4.

---

### T-002: Create TokenBlocklist model and database migration

**Description**: Add a `TokenBlocklist` SQLAlchemy model to store revoked refresh token JTIs. Generate and apply the database migration.

**Files affected**:
- `backend/models.py`
- `backend/migrations/versions/` (new auto-generated migration file)

**Changes**:

1. Add the following model class to `backend/models.py` (after the `SessionWord` class):
   ```python
   class TokenBlocklist(db.Model):
       __tablename__ = 'token_blocklist'

       id = db.Column(db.Integer, primary_key=True)
       jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
       created_ds = db.Column(db.DateTime, nullable=False)

       def add(self):
           try:
               db.session.add(self)
               db.session.commit()
           except Exception:
               db.session.rollback()
               raise

       @classmethod
       def is_blocklisted(cls, jti: str) -> bool:
           return cls.query.filter_by(jti=jti).first() is not None
   ```

2. Generate migration: `cd backend && flask db migrate -m "add token_blocklist table"`
3. Verify the migration creates a `token_blocklist` table with `id`, `jti`, `created_ds` columns.
4. Apply migration: `flask db upgrade`

**Acceptance criteria**:
- `TokenBlocklist` model exists in `backend/models.py` with `id`, `jti`, `created_ds` columns.
- `jti` column has a unique constraint and an index.
- `TokenBlocklist.add()` method persists the entry to the database.
- `TokenBlocklist.is_blocklisted(jti)` returns `True` if the jti exists, `False` otherwise.
- The `token_blocklist` table exists in the PostgreSQL database after migration.
- Existing tables are unaffected.

**Dependencies**: None (can be done in parallel with T-001)

**Testing**: Manual verification: `\d token_blocklist` in psql. Automated tests in Phase 4.

---

### T-003: Register blocklist loader callback and update CORS

**Description**: Register Flask-JWT-Extended's `token_in_blocklist_loader` callback so that revoked tokens are rejected. Update CORS to support credentials (cookies).

**Files affected**:
- `backend/app.py`

**Changes**:

1. Add import: `from models import TokenBlocklist`

2. In `register_extensions(app)`, update CORS and add the blocklist loader:
   ```python
   def register_extensions(app):
       db.init_app(app)
       migrate = Migrate(app, db)
       jwt.init_app(app)
       CORS(app, supports_credentials=True)

       @jwt.token_in_blocklist_loader
       def check_if_token_revoked(jwt_header, jwt_payload):
           jti = jwt_payload['jti']
           return TokenBlocklist.is_blocklisted(jti)
   ```

**Acceptance criteria**:
- The `@jwt.token_in_blocklist_loader` callback is registered.
- If a token's `jti` is in the `TokenBlocklist`, requests using that token return 401.
- CORS is configured with `supports_credentials=True`.
- The Flask app starts without errors.
- Existing endpoints continue to work with valid access tokens.

**Dependencies**: T-002

**Testing**: Start Flask. Verify existing endpoints still work. Automated tests in Phase 4.

---

### T-004: Update TokenResource (login) to issue both tokens

**Description**: Modify the `POST /api/token` login endpoint to issue a refresh token as an HttpOnly cookie in addition to the access token in the response body.

**Files affected**:
- `backend/resources.py`

**Changes**:

1. Update imports at the top of `resources.py`:
   ```python
   from flask import request, make_response
   from flask_jwt_extended import (
       create_access_token, create_refresh_token,
       jwt_required, get_jwt_identity, get_jwt,
       set_refresh_cookies, unset_refresh_cookies
   )
   from models import Word, User, SessionWord, UserSession, TokenBlocklist
   ```

2. Rewrite `TokenResource.post()`:
   ```python
   class TokenResource(Resource):
       def post(self):
           data = request.get_json()
           username = data.get('username')
           password = data.get('password')

           user = User.get_by_username(username)

           if not user or not check_password(password, user.password):
               return {'message': 'Username or password is incorrect.'}, HTTPStatus.UNAUTHORIZED

           try:
               identity = str(user.id)
               access_token = create_access_token(identity=identity)
               refresh_token = create_refresh_token(identity=identity)
           except Exception as e:
               return {'message': 'Failure creating access token.'}, 500

           response = make_response(
               {'access_token': access_token},
               HTTPStatus.OK
           )
           set_refresh_cookies(response, refresh_token)
           return response
   ```

**Acceptance criteria**:
- `POST /api/token` with valid credentials returns `{ "access_token": "..." }` in the response body (same as before).
- The response also includes a `Set-Cookie` header with the refresh token (HttpOnly, SameSite=Strict).
- `POST /api/token` with invalid credentials still returns 401 with `{ "message": "Username or password is incorrect." }`.
- The access token is a short-lived token (15 min expiry).
- The refresh token is a long-lived token (7 day expiry).

**Dependencies**: T-001, T-003

**Testing**: Manual test with curl: `curl -v -X POST http://localhost:5000/api/token -H "Content-Type: application/json" -d '{"username":"...","password":"..."}'`. Check for `Set-Cookie` header in the response. Automated tests in Phase 4.

---

### T-005: Create TokenRefreshResource endpoint

**Description**: Create a new `POST /api/token/refresh` endpoint that accepts a refresh token via HttpOnly cookie, issues new access + refresh tokens, and blocklists the old refresh token.

**Files affected**:
- `backend/resources.py`
- `backend/app.py`

**Changes**:

1. Add `TokenRefreshResource` class to `resources.py`:
   ```python
   class TokenRefreshResource(Resource):
       @jwt_required(refresh=True)
       def post(self):
           identity = get_jwt_identity()
           old_jti = get_jwt()['jti']

           # Blocklist the old refresh token
           now = datetime.now()
           blocklist_entry = TokenBlocklist(jti=old_jti, created_ds=now)
           blocklist_entry.add()

           # Issue new tokens
           new_access_token = create_access_token(identity=identity)
           new_refresh_token = create_refresh_token(identity=identity)

           response = make_response(
               {'access_token': new_access_token},
               HTTPStatus.OK
           )
           set_refresh_cookies(response, new_refresh_token)
           return response
   ```

2. Register the route in `backend/app.py`:
   ```python
   from resources import (..., TokenRefreshResource)
   # In register_resources():
   api.add_resource(TokenRefreshResource, '/token/refresh')
   ```

**Acceptance criteria**:
- `POST /api/token/refresh` with a valid refresh cookie returns `{ "access_token": "..." }` and a new refresh cookie.
- The old refresh token's `jti` is added to the `TokenBlocklist` table.
- `POST /api/token/refresh` with no cookie returns 401.
- `POST /api/token/refresh` with a blocklisted refresh token returns 401.
- `POST /api/token/refresh` with an expired refresh token returns 401.

**Dependencies**: T-002, T-003, T-004

**Testing**: Manual test: login to get the refresh cookie, then call refresh. Verify the old jti is in the blocklist table. Automated tests in Phase 4.

---

### T-006: Create TokenRevokeResource endpoint

**Description**: Create a new `POST /api/token/revoke` endpoint that blocklists the refresh token and clears the refresh cookie. This is used for logout.

**Files affected**:
- `backend/resources.py`
- `backend/app.py`

**Changes**:

1. Add `TokenRevokeResource` class to `resources.py`:
   ```python
   class TokenRevokeResource(Resource):
       @jwt_required(refresh=True)
       def post(self):
           jti = get_jwt()['jti']
           now = datetime.now()

           blocklist_entry = TokenBlocklist(jti=jti, created_ds=now)
           blocklist_entry.add()

           response = make_response(
               {'message': 'Token revoked'},
               HTTPStatus.OK
           )
           unset_refresh_cookies(response)
           return response
   ```

2. Register the route in `backend/app.py`:
   ```python
   from resources import (..., TokenRevokeResource)
   # In register_resources():
   api.add_resource(TokenRevokeResource, '/token/revoke')
   ```

**Acceptance criteria**:
- `POST /api/token/revoke` with a valid refresh cookie returns `{ "message": "Token revoked" }` with 200.
- The response clears the refresh cookie (unsets it).
- The refresh token's `jti` is added to the `TokenBlocklist` table.
- Subsequent calls to `/api/token/refresh` with the revoked token return 401.
- `POST /api/token/revoke` with no cookie returns 401.

**Dependencies**: T-002, T-003

**Testing**: Manual test: login, then revoke, then try to refresh. Automated tests in Phase 4.

---

## Phase 2: Frontend Token Infrastructure

This phase updates the frontend auth infrastructure. No new UI components yet.

---

### T-007: Update Axios instance -- remove localStorage, add token setter and 401 interceptor

**Description**: Rewrite `frontend/src/lib/api.ts` to use an in-memory token with a setter function, and add a 401 response interceptor that automatically refreshes the token.

**Files affected**:
- `frontend/src/lib/api.ts`

**Changes**: Replace the entire file with the implementation from the design document (Section 9). Key elements:
1. Module-level `accessToken` variable with `setAccessToken()` and `getAccessToken()` exports.
2. Request interceptor reads from the module-level variable instead of localStorage.
3. 401 response interceptor that calls `POST /api/token/refresh` with `withCredentials: true`, retries the failed request on success, and calls `onRefreshFailure` callback on failure.
4. `failedQueue` array to handle concurrent 401s.
5. `setOnRefreshFailure()` export for AuthContext to register a logout callback.

**Acceptance criteria**:
- No references to `localStorage` remain in `api.ts`.
- `setAccessToken(token)` updates the module-level variable.
- The request interceptor uses the module-level variable for the `Authorization` header.
- On 401 (excluding `/api/token*` URLs), the interceptor attempts a refresh.
- If refresh succeeds, the original request is retried with the new token.
- If refresh fails, `onRefreshFailure` is called and the error is propagated.
- Concurrent 401s are queued (only one refresh request at a time).
- TypeScript compiles without errors.

**Dependencies**: T-005 (backend refresh endpoint must exist to test)

**Testing**: TypeScript compilation. Integration verified in Phase 3 when AuthContext is updated.

---

### T-008: Update AuthContext -- in-memory tokens and silent refresh

**Description**: Rewrite `frontend/src/contexts/AuthContext.tsx` to remove all localStorage usage, store the access token in React state only, perform silent refresh on mount, and call `POST /api/token/revoke` on logout.

**Files affected**:
- `frontend/src/contexts/AuthContext.tsx`

**Changes**: Replace the entire file with the implementation from the design document (Section 10). Key elements:
1. Remove all `localStorage.getItem('access_token')` and `localStorage.setItem(...)` calls.
2. `useEffect` on `[token]` calls `setAccessToken(token)` to sync React state with the Axios module.
3. `useEffect` on mount calls `silentRefresh()`: `POST /api/token/refresh` with `withCredentials: true` to restore the session.
4. `login()` calls `POST /api/token` with `withCredentials: true` and stores the access token in React state.
5. `logout()` calls `POST /api/token/revoke` with `withCredentials: true`, then clears state.
6. `handleLogout` callback registered with `setOnRefreshFailure()` for the Axios interceptor.

**Acceptance criteria**:
- No references to `localStorage` remain in `AuthContext.tsx`.
- `login()` stores the access token in React state only (not localStorage).
- `login()` calls `/api/token` with `withCredentials: true` so the refresh cookie is stored.
- `logout()` calls `POST /api/token/revoke` to invalidate the refresh token on the server.
- On mount, `silentRefresh()` attempts to restore the session via `/api/token/refresh`.
- If silent refresh succeeds, `isAuthenticated` becomes `true` and `user` is populated.
- If silent refresh fails, `isAuthenticated` remains `false` and `isLoading` becomes `false`.
- The `handleLogout` function is registered with the Axios interceptor as the refresh failure callback.
- **IMPORTANT**: AuthContext MUST NOT use `useNavigate()` or any navigation logic. Navigation is handled by components (ProtectedRoute, Sidebar) to avoid circular dependencies with React Router.
- TypeScript compiles without errors.

**Dependencies**: T-007

**Testing**: TypeScript compilation. Manual integration test: start both servers, verify login/refresh/logout flow.

---

### T-009: Remove localStorage access_token from any remaining files

**Description**: Search the entire frontend codebase for any remaining references to `localStorage.getItem('access_token')` or `localStorage.setItem('access_token', ...)` and remove them. This is a cleanup task to ensure no code path still relies on localStorage for auth.

**Files affected**:
- Search all files in `frontend/src/` for `localStorage` references related to `access_token`.
- Expected: after T-007 and T-008, there should be none. This task is a verification pass.

**Acceptance criteria**:
- Grep for `localStorage.*access_token` in `frontend/src/` returns zero results.
- Grep for `getItem.*access_token` in `frontend/src/` returns zero results.
- The app starts without errors.

**Dependencies**: T-007, T-008

**Testing**: Grep verification. Manual test: verify the app does not write to or read from `localStorage` for auth (check browser DevTools Application > Local Storage).

---

## Phase 3: Frontend Auth Pages and Protected Routes

This phase creates the user-facing auth components. Backend must be ready (Phase 1 complete).

---

### T-010: Create Login page component

**Description**: Create the Login page at `frontend/src/pages/Login.tsx` with username/password form, error handling, loading state, and link to Register.

**Files affected**:
- `frontend/src/pages/Login.tsx` (new file)

**Changes**: Create the file with the implementation from the design document (Section 11). Key elements:
1. Form with username and password fields.
2. On submit: call `login()` from `useAuth()`, redirect to `/home` (or `location.state.from`) on success.
3. Error display from `error.response.data.message`.
4. Loading state on the submit button.
5. Link to `/register`.
6. Styling matches the Welcome page: gradient background, white card, purple buttons.

**Acceptance criteria**:
- The file exists at `frontend/src/pages/Login.tsx`.
- The page renders a form with username and password fields and a "Log in" button.
- A link to `/register` is visible below the form.
- Submitting valid credentials calls `login()` and redirects to `/home`.
- Submitting invalid credentials shows the backend error message in red.
- The button shows "Logging in..." and is disabled during submission.
- All form fields have associated `<label>` elements with `htmlFor`.
- Error messages use `role="alert"` and `aria-live="polite"`.
- TypeScript compiles without errors.

**Dependencies**: T-008 (AuthContext with in-memory login)

**Testing**: TypeScript compilation. Manual browser test. Automated component test in Phase 5.

---

### T-011: Create Register page component

**Description**: Create the Register page at `frontend/src/pages/Register.tsx` with username, email, password, confirm password form, client-side validation, error handling, and link to Login.

**Files affected**:
- `frontend/src/pages/Register.tsx` (new file)

**Changes**: Create the file with the implementation from the design document (Section 12). Key elements:
1. Form with username, email, password, confirm password fields.
2. Client-side validation: password match check before submission.
3. On submit: `POST /api/users`, then `login()`, then redirect to `/`.
4. Error display from backend (`error.response.data.error` or `.message`).
5. Loading state on the submit button.
6. Link to `/login`.
7. Styling matches the Login/Welcome pages.

**Acceptance criteria**:
- The file exists at `frontend/src/pages/Register.tsx`.
- The page renders a form with username, email, password, confirm password fields and a "Register" button.
- A link to `/login` is visible below the form.
- Mismatched passwords show "Passwords do not match" without making an API call.
- Submitting valid data creates the user, logs in, and redirects to `/`.
- Backend validation errors (duplicate email/username) are displayed in red.
- The button shows "Creating account..." and is disabled during submission.
- All form fields have associated `<label>` elements.
- TypeScript compiles without errors.

**Dependencies**: T-008 (AuthContext with in-memory login)

**Testing**: TypeScript compilation. Manual browser test. Automated component test in Phase 5.

---

### T-012: Create ProtectedRoute component

**Description**: Create the `ProtectedRoute` wrapper component that checks authentication state and either renders children, shows a loading indicator, or redirects to `/login`.

**Files affected**:
- `frontend/src/components/ProtectedRoute.tsx` (new file)

**Changes**: Create the file with the implementation from the design document (Section 13). Key elements:
1. Uses `useAuth()` to check `isLoading` and `isAuthenticated`.
2. If `isLoading`: render a centered loading indicator with the purple gradient background.
3. If not authenticated: render `<Navigate to="/login" state={{ from: location }} replace />`.
4. If authenticated: render `{children}`.

**Acceptance criteria**:
- The file exists at `frontend/src/components/ProtectedRoute.tsx`.
- When `isLoading` is `true`, a loading indicator is shown (no flash of login page or content).
- When `isAuthenticated` is `false` and `isLoading` is `false`, redirects to `/login`.
- The redirect preserves the attempted URL in `location.state.from`.
- When `isAuthenticated` is `true`, children are rendered.
- TypeScript compiles without errors.

**Dependencies**: T-008 (AuthContext must be updated)

**Testing**: TypeScript compilation. Automated component test in Phase 5.

---

### T-013: Update App.tsx with new routes and ProtectedRoute wrapping

**Description**: Add `/login` and `/register` routes, wrap all existing routes with `ProtectedRoute`, and import the new components.

**Files affected**:
- `frontend/src/App.tsx`

**Changes**: Replace the file contents with the implementation from the design document (Section 14):
1. Import `Login`, `Register`, `ProtectedRoute`.
2. Add `/login` and `/register` as public routes.
3. Wrap `/`, `/practice`, `/home`, `/progress`, `/vocabulary`, `/settings` with `<ProtectedRoute>`.

**Acceptance criteria**:
- `/login` renders the Login page without requiring authentication.
- `/register` renders the Register page without requiring authentication.
- `/`, `/home`, `/vocabulary`, `/practice`, `/progress`, `/settings` are all wrapped with `ProtectedRoute`.
- Navigating to a protected route while unauthenticated redirects to `/login`.
- Navigating to a protected route while authenticated renders the page normally.
- TypeScript compiles without errors.

**Dependencies**: T-010, T-011, T-012

**Testing**: Manual browser test: navigate to `/home` without being logged in, verify redirect to `/login`. Log in, verify `/home` renders. Automated test in Phase 5.

---

### T-014: Update Sidebar with logout button

**Description**: Add a logout button at the bottom of the Sidebar that calls `logout()` from AuthContext and navigates to `/login`.

**Files affected**:
- `frontend/src/components/Sidebar.tsx`

**Changes**: Update the file with the changes from the design document (Section 15):
1. Import `useNavigate` from `react-router-dom` and `useAuth` from `../contexts/AuthContext`.
2. Add `handleLogout` function that calls `await logout()` then `navigate('/login')`.
3. Restructure the aside element: wrap nav items in a `<div>`, add the logout button below with `mt-auto`.
4. The logout button uses a "door with arrow" SVG icon and has `hover:text-red-500 hover:bg-red-50` styling.

**Acceptance criteria**:
- A logout button is visible at the bottom of the Sidebar.
- The button is visually separated from the navigation items (pushed to bottom via `mt-auto`).
- The button uses a logout icon consistent with the existing sidebar icon style.
- On hover, the button turns red-tinted (`hover:text-red-500 hover:bg-red-50`).
- Clicking the button calls `logout()` and navigates to `/login`.
- After logout, the user cannot access protected routes.
- TypeScript compiles without errors.

**Dependencies**: T-008 (AuthContext with revoke-based logout)

**Testing**: Manual browser test. Automated component test in Phase 5.

---

## Phase 4: Backend Tests

This phase adds tests for the new token infrastructure.

---

### T-015: Write TokenBlocklist model unit tests

**Description**: Write pytest tests for the `TokenBlocklist` model's `add()` and `is_blocklisted()` methods.

**Files affected**:
- `backend/tests/test_token_blocklist.py` (new file)

**Content**:
```python
from models import TokenBlocklist
from datetime import datetime

def test_add_to_blocklist(db):
    """TokenBlocklist.add() should persist a jti to the database."""
    entry = TokenBlocklist(jti='test-jti-123', created_ds=datetime.now())
    entry.add()
    assert TokenBlocklist.is_blocklisted('test-jti-123') is True

def test_is_blocklisted_returns_false_for_unknown_jti(db):
    """is_blocklisted should return False for a jti not in the table."""
    assert TokenBlocklist.is_blocklisted('nonexistent-jti') is False
```

**Acceptance criteria**:
- Both tests pass: `python -m pytest tests/test_token_blocklist.py -v`
- Tests run against SQLite in-memory (no PostgreSQL needed).

**Dependencies**: T-002

**Testing**: `cd backend && python -m pytest tests/test_token_blocklist.py -v`

---

### T-016: Write token endpoint integration tests

**Description**: Write pytest integration tests for the login, refresh, and revoke endpoints.

**Files affected**:
- `backend/tests/test_auth_tokens.py` (new file)

**Content (key tests)**:
```python
import json

def _register_and_login(client):
    """Helper: register a test user and log in, return access token and response (with cookies)."""
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    response = client.post('/api/token', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    return response

def test_login_returns_access_token_and_sets_refresh_cookie(client):
    """POST /api/token should return access_token in body and set refresh cookie."""
    response = _register_and_login(client)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    # Check that a Set-Cookie header was set for the refresh token
    cookies = response.headers.getlist('Set-Cookie')
    refresh_cookie_set = any('refresh_token' in c for c in cookies)
    assert refresh_cookie_set

def test_refresh_returns_new_access_token(client):
    """POST /api/token/refresh with valid refresh cookie returns new access token."""
    _register_and_login(client)
    # The test client automatically stores cookies
    refresh_response = client.post('/api/token/refresh')
    assert refresh_response.status_code == 200
    data = json.loads(refresh_response.data)
    assert 'access_token' in data

def test_refresh_blocklists_old_token(client, db):
    """After refresh, the old refresh token's jti should be in the blocklist."""
    from models import TokenBlocklist
    _register_and_login(client)
    # First refresh
    client.post('/api/token/refresh')
    # The blocklist should now have at least one entry
    assert db.session.query(TokenBlocklist).count() >= 1

def test_revoke_blocklists_and_clears_cookie(client, db):
    """POST /api/token/revoke should blocklist the token and clear the cookie."""
    from models import TokenBlocklist
    _register_and_login(client)
    initial_count = db.session.query(TokenBlocklist).count()
    revoke_response = client.post('/api/token/revoke')
    assert revoke_response.status_code == 200
    data = json.loads(revoke_response.data)
    assert data['message'] == 'Token revoked'
    assert db.session.query(TokenBlocklist).count() > initial_count

def test_refresh_with_revoked_token_fails(client):
    """After revoking, refresh should fail with 401."""
    _register_and_login(client)
    client.post('/api/token/revoke')
    refresh_response = client.post('/api/token/refresh')
    assert refresh_response.status_code == 401

def test_protected_endpoint_with_expired_or_missing_token(client):
    """GET /api/me without a valid access token should return 401."""
    response = client.get('/api/me')
    assert response.status_code == 401
```

**Acceptance criteria**:
- All tests pass: `python -m pytest tests/test_auth_tokens.py -v`
- Tests cover: login returns both tokens, refresh works, refresh blocklists old token, revoke works, revoked token cannot refresh, protected endpoints reject missing tokens.
- Tests run against SQLite in-memory.

**Dependencies**: T-004, T-005, T-006

**Testing**: `cd backend && python -m pytest tests/test_auth_tokens.py -v`

---

### T-017: Verify all existing backend tests still pass

**Description**: Run the entire backend test suite to ensure no regressions from the token infrastructure changes.

**Files affected**: None (verification task).

**Acceptance criteria**:
- `cd backend && python -m pytest tests/ -v` passes all tests (existing + new).
- No import errors or configuration issues.

**Dependencies**: T-015, T-016

**Testing**: `cd backend && python -m pytest tests/ -v`

---

## Phase 5: Frontend Tests and Integration Verification

---

### T-018: Write Login page component test

**Description**: Write a Vitest/RTL test for the Login page verifying it renders correctly and shows errors on failure.

**Files affected**:
- `frontend/src/test/Login.test.tsx` (new file)

**Key test cases**:
1. Renders username, password fields and submit button.
2. Renders link to register page.
3. Shows error message when login fails (mock the AuthContext).

**Acceptance criteria**:
- All test cases pass: `npm test -- --run`
- Tests mock the AuthContext provider appropriately.

**Dependencies**: T-010

**Testing**: `npm test -- --run`

---

### T-019: Write Register page component test

**Description**: Write a Vitest/RTL test for the Register page verifying form rendering and client-side validation.

**Files affected**:
- `frontend/src/test/Register.test.tsx` (new file)

**Key test cases**:
1. Renders username, email, password, confirm password fields and submit button.
2. Renders link to login page.
3. Shows "Passwords do not match" error when passwords differ (no API call).

**Acceptance criteria**:
- All test cases pass: `npm test -- --run`

**Dependencies**: T-011

**Testing**: `npm test -- --run`

---

### T-020: Write ProtectedRoute component test

**Description**: Write a Vitest/RTL test for the ProtectedRoute component verifying its three states: loading, unauthenticated redirect, and authenticated render.

**Files affected**:
- `frontend/src/test/ProtectedRoute.test.tsx` (new file)

**Key test cases**:
1. Shows loading indicator when `isLoading` is `true`.
2. Redirects to `/login` when `isAuthenticated` is `false` and `isLoading` is `false`.
3. Renders children when `isAuthenticated` is `true`.

**Acceptance criteria**:
- All test cases pass: `npm test -- --run`
- Tests mock the `useAuth` hook to control `isLoading` and `isAuthenticated`.

**Dependencies**: T-012

**Testing**: `npm test -- --run`

---

### T-021: Verify all existing frontend tests still pass

**Description**: Run the entire frontend test suite to ensure no regressions. Update any existing tests that broke due to the new auth requirements (e.g. the App smoke test may need AuthContext mocking since routes are now protected).

**Files affected**:
- `frontend/src/test/App.test.tsx` (may need updates)

**Changes**: The existing App smoke test renders `<App />` and expects "Welcome to the classroom" text. After M1, the default route `/` is protected. The test may need to either:
- Mock the AuthContext to simulate an authenticated user, OR
- Navigate to `/login` and check for login page content instead.

**Acceptance criteria**:
- `npm test -- --run` passes all tests (existing + new).
- No test failures due to protected route changes.

**Dependencies**: T-018, T-019, T-020

**Testing**: `npm test -- --run`

---

### T-022: End-to-end manual verification

**Description**: Verify the complete auth and onboarding flow works end-to-end.

**Files affected**: None (verification task).

**Steps**:

1. **Start both servers**: `python backend/app.py` and `npm run dev`.

2. **Test unauthenticated redirect**:
   - Open `http://localhost:5173/home` in the browser.
   - Verify redirect to `/login`.
   - Verify no flash of the home page content.

3. **Test registration flow**:
   - Navigate to `/register`.
   - Test password mismatch: enter different passwords, submit, verify error message.
   - Register with valid data: username, email, matching passwords.
   - Verify automatic login and redirect to `/` (Welcome page).
   - Verify the Welcome page onboarding flow is shown.
   - Click "Get started", verify redirect to `/vocabulary`.

4. **Test logout**:
   - On any page with the Sidebar, click the logout button.
   - Verify redirect to `/login`.
   - Verify cannot navigate to `/home` (redirects back to `/login`).

5. **Test login flow**:
   - On `/login`, enter the credentials from step 3.
   - Verify redirect to `/home`.
   - Navigate between pages: `/vocabulary`, `/practice`, `/progress`, `/settings`.
   - Verify all pages load correctly.

6. **Test session persistence (page refresh)**:
   - While logged in, refresh the browser (F5).
   - Verify the user remains authenticated (no redirect to `/login`).
   - Verify a brief loading indicator appears during silent refresh.

7. **Test session expiry**:
   - Log in, then clear the refresh cookie manually (DevTools > Application > Cookies > delete the refresh cookie).
   - Refresh the page.
   - Verify redirect to `/login`.

8. **Test login with bad credentials**:
   - On `/login`, enter a wrong password.
   - Verify the error message "Username or password is incorrect." is displayed.

9. **Test registration errors**:
   - On `/register`, try to register with an existing username.
   - Verify the error message "Username invalid or already registered" is displayed.

10. **Verify localStorage is clean**:
    - Open DevTools > Application > Local Storage.
    - Verify no `access_token` entry exists at any point during the flow.

11. **Run all tests**:
    - `cd backend && python -m pytest tests/ -v` (all backend tests pass).
    - `npm test -- --run` (all frontend tests pass).

**Acceptance criteria**:
- Unauthenticated users are redirected to `/login` on all protected routes.
- Registration creates account, auto-logs in, redirects to onboarding.
- Login authenticates and redirects to `/home`.
- Logout revokes token and redirects to `/login`.
- Page refresh preserves the session (silent refresh works).
- Expired/missing refresh cookie results in redirect to `/login`.
- Backend error messages are displayed on Login and Register pages.
- Password mismatch is caught client-side on Register page.
- No `access_token` in localStorage at any point.
- All backend tests pass.
- All frontend tests pass.

**Dependencies**: All previous tasks (T-001 through T-021).

**Testing**: This task IS the testing.

---

## Definition of Done

Milestone 1 is complete when ALL of the following are true:

1. **Token infrastructure (backend)**: Access tokens expire in 15 minutes. Refresh tokens expire in 7 days. Refresh tokens are set as HttpOnly/SameSite=Strict cookies. `TokenBlocklist` table exists and is checked by Flask-JWT-Extended.
2. **Token endpoints (backend)**: `POST /api/token` issues both tokens. `POST /api/token/refresh` rotates tokens and blocklists the old one. `POST /api/token/revoke` blocklists the token and clears the cookie.
3. **Token management (frontend)**: Access token stored in React state only (not localStorage). Refresh token managed as HttpOnly cookie by the browser. 401 interceptor in Axios automatically refreshes and retries. Silent refresh on app mount restores sessions.
4. **Login page**: `/login` route renders a form with username, password, error display, loading state, and link to register.
5. **Register page**: `/register` route renders a form with username, email, password, confirm password, client-side validation, error display, loading state, and link to login. Successful registration auto-logs in and redirects to onboarding.
6. **Protected routes**: `/`, `/home`, `/vocabulary`, `/practice`, `/progress`, `/settings` are wrapped with `ProtectedRoute`. Unauthenticated users are redirected to `/login`. Loading state is shown during auth check.
7. **Welcome page**: Unchanged visually. Only accessible to authenticated users. Serves as the onboarding entry point after registration.
8. **Logout**: Sidebar has a logout button at the bottom. Clicking it revokes the refresh token and redirects to `/login`.
9. **Session persistence**: Page refresh triggers silent refresh via the HttpOnly cookie. Users remain authenticated without localStorage.
10. **Backend tests**: `TokenBlocklist` model tests and token endpoint integration tests pass.
11. **Frontend tests**: Login, Register, and ProtectedRoute component tests pass. Existing tests updated and passing.
12. **No regressions**: The app starts without errors, all pages render for authenticated users, no TypeScript compilation errors, all test suites pass.
