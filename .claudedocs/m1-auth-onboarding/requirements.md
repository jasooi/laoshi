# Milestone 1: Authentication & Onboarding -- Requirements Document

## Feature Overview

Milestone 1 completes the authentication and onboarding user experience for Laoshi Coach and hardens the auth infrastructure with a proper token refresh flow.

**What already exists (tasks 1.1-1.3, 1.8):**
- Backend auth endpoints: `POST /api/users` (register), `POST /api/token` (login), `GET /api/me` (current user).
- `AuthContext` at `frontend/src/contexts/AuthContext.tsx` with `login()`, `logout()`, token state, user state.
- Centralized Axios instance at `frontend/src/lib/api.ts` with JWT interceptor reading from localStorage.
- Welcome page onboarding flow at `frontend/src/pages/Welcome.tsx`.

**What this milestone delivers:**
1. **Secure token management**: Replace localStorage-based JWT storage with an in-memory access token + HttpOnly refresh cookie architecture. Add token refresh and revocation endpoints on the backend.
2. **Frontend auth pages**: Login page, Register page, protected route wrapper, logout button.
3. **Routing logic**: Unauthenticated users redirected to `/login`; post-registration auto-login and redirect to onboarding.

This milestone maps to **PRD User Story #1** (Register & login) and **PRD User Story #2** (Guided onboarding).

---

## User Stories

### US-01: Log in with username and password
**As a** returning user, **I want** to log in with my username and password **so that** I can access my saved vocabulary and progress.

**Acceptance Criteria:**
- When I navigate to `/login`, I see a form with username and password fields and a "Log in" button.
- When I submit valid credentials, I am redirected to `/home`.
- When I submit invalid credentials, I see the error message from the backend (e.g. "Username or password is incorrect.") displayed below the form.
- The login form has a link to the Register page for users who do not yet have an account.
- While the login request is in progress, the submit button shows a loading state and is disabled to prevent double-submission.

### US-02: Register a new account
**As a** new user, **I want** to create an account with a username, email, and password **so that** my learning progress is saved.

**Acceptance Criteria:**
- When I navigate to `/register`, I see a form with username, email, password, and confirm password fields and a "Register" button.
- When I submit valid registration data, my account is created, I am automatically logged in, and I am redirected to `/` (the Welcome/onboarding page).
- When I submit data that fails backend validation (e.g. duplicate email, duplicate username), I see the specific error message from the backend displayed below the form.
- If the password and confirm password fields do not match, a client-side validation error is shown before the form is submitted.
- The register form has a link to the Login page for users who already have an account.
- While the registration request is in progress, the submit button shows a loading state and is disabled.

### US-03: Unauthenticated users are redirected to login
**As a** product owner, **I want** unauthenticated users who try to access protected pages to be redirected to `/login` **so that** the app's data and features are only accessible to logged-in users.

**Acceptance Criteria:**
- If I am not logged in and navigate to `/home`, `/vocabulary`, `/practice`, `/progress`, or `/settings`, I am redirected to `/login`.
- While the auth state is loading (e.g. on initial page load when performing a silent refresh), a loading indicator is shown instead of a flash of the login page.
- After logging in, I am taken to the page I originally requested (or `/home` if no specific page was requested).

### US-04: Guided onboarding after registration
**As a** new user, **I want** a smooth transition from registration to onboarding **so that** I can start learning quickly.

**Acceptance Criteria:**
- After registering, I am automatically logged in and redirected to the Welcome page (`/`).
- The Welcome page shows the onboarding flow (the existing "Welcome to the classroom" card with "Get started" leading to vocabulary import).
- If I am already authenticated and navigate to `/`, I see the onboarding flow.
- If I am not authenticated and navigate to `/`, I am redirected to `/login`.

### US-05: Log out from the sidebar
**As a** logged-in user, **I want** to log out from any page **so that** I can end my session securely.

**Acceptance Criteria:**
- A logout button is visible at the bottom of the Sidebar on all pages that use the Layout component.
- Clicking the logout button clears my authentication state (access token from memory, refresh token cookie revoked on the server) and redirects me to `/login`.
- After logging out, attempting to navigate to any protected page redirects me to `/login`.

### US-06: Session persists across page refreshes
**As a** logged-in user, **I want** my session to survive page refreshes **so that** I do not have to log in every time I reload the page.

**Acceptance Criteria:**
- After logging in and refreshing the browser, I remain authenticated without seeing a login screen.
- The app silently refreshes my access token using the HttpOnly refresh cookie on page load.
- If my refresh token has expired (after 7 days of inactivity), I am redirected to `/login`.

---

## Functional Requirements

### Token Management -- Backend

**FR-001**: Token expiry MUST be configured explicitly in `backend/config.py`:
- Access token lifetime: 15 minutes (`JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)`).
- Refresh token lifetime: 7 days (`JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)`).

**FR-002**: The `POST /api/token` endpoint (login) in `backend/resources.py` MUST be updated to issue both an access token and a refresh token:
- The access token MUST be returned in the JSON response body: `{ "access_token": "..." }`.
- The refresh token MUST be set as an HttpOnly, Secure, SameSite=Strict cookie on the response. Use Flask-JWT-Extended's `set_refresh_cookies()` helper or manually set the cookie with the flags: `httponly=True`, `samesite='Strict'`, `secure=True` (with `secure=False` override in development/test config).
- The cookie name should be `refresh_token_cookie` (Flask-JWT-Extended default) or a custom name configured in `config.py`.

**FR-003**: Flask-JWT-Extended cookie configuration MUST be set in `backend/config.py`:
- `JWT_TOKEN_LOCATION = ['headers', 'cookies']` -- accept access tokens from headers and refresh tokens from cookies.
- `JWT_REFRESH_COOKIE_PATH = '/api/token'` -- scope the refresh cookie to the token endpoints only.
- `JWT_COOKIE_SECURE = False` for development (override to `True` in production).
- `JWT_COOKIE_SAMESITE = 'Strict'`.
- `JWT_COOKIE_CSRF_PROTECT = False` -- since we use SameSite=Strict, CSRF protection via double-submit cookie is not required for the MVP. This can be enabled in a future hardening pass.

**FR-004**: A `TokenBlocklist` model MUST be created in `backend/models.py` to store revoked refresh tokens:
- Columns: `id` (Integer, primary key), `jti` (String(36), unique, not null, indexed), `created_ds` (DateTime, not null).
- The `jti` (JWT ID) is a unique identifier embedded in each token by Flask-JWT-Extended.
- A database migration MUST be generated and applied for this new table.

**FR-005**: A `@jwt.token_in_blocklist_loader` callback MUST be registered (in `backend/extensions.py` or `backend/app.py`) that checks whether a given token's `jti` exists in the `TokenBlocklist` table. If it does, the token is considered revoked.

**FR-006**: A `POST /api/token/refresh` endpoint MUST be created in `backend/resources.py`:
- It MUST require a valid refresh token (via `@jwt_required(refresh=True)`).
- It MUST check that the refresh token is not blocklisted.
- It MUST issue a new access token and a new (rotated) refresh token.
- The new access token MUST be returned in the JSON response body.
- The new refresh token MUST be set as an HttpOnly cookie (replacing the old one).
- The old refresh token's `jti` MUST be added to the `TokenBlocklist` table.

**FR-007**: A `POST /api/token/revoke` endpoint MUST be created in `backend/resources.py` (used for logout):
- It MUST require a valid refresh token (via `@jwt_required(refresh=True)`).
- It MUST add the refresh token's `jti` to the `TokenBlocklist` table.
- It MUST clear the refresh token cookie from the response (use `unset_refresh_cookies()` or manually delete the cookie).
- It MUST return a success message: `{ "message": "Token revoked" }` with 200.

**FR-008**: The `TestConfig` in `backend/config.py` MUST be updated with the new JWT settings (token locations, cookie settings, etc.) so that tests can exercise the refresh flow.

### Token Management -- Frontend

**FR-009**: The access token MUST NO LONGER be stored in `localStorage`. It MUST be stored only in React state (in-memory) within the `AuthContext`. This prevents XSS attacks from stealing the access token.

**FR-010**: The refresh token is managed entirely by the browser as an HttpOnly cookie. The frontend code MUST NOT read, write, or reference the refresh token directly. The browser automatically sends it with requests to `/api/token/*` endpoints.

**FR-011**: The `AuthContext` at `frontend/src/contexts/AuthContext.tsx` MUST be updated:
- Remove all `localStorage.getItem('access_token')` and `localStorage.setItem('access_token', ...)` calls.
- The `login()` function MUST store the access token from the `POST /api/token` response in React state only.
- The `logout()` function MUST call `POST /api/token/revoke` (to revoke the refresh cookie on the server and clear the cookie), then clear the access token from React state and clear user state.

**FR-012**: The centralized Axios instance at `frontend/src/lib/api.ts` MUST be updated:
- The request interceptor MUST NO LONGER read from `localStorage`. Instead, it MUST accept the access token via a setter function or a module-level variable that the `AuthContext` updates whenever the token changes.
- A 401 response interceptor MUST be added that:
  1. On receiving a 401 response, attempts to refresh the token by calling `POST /api/token/refresh` (with `withCredentials: true` so the browser sends the refresh cookie).
  2. If the refresh succeeds, updates the in-memory access token and retries the original failed request.
  3. If the refresh fails (e.g. refresh token expired or revoked), redirects to `/login` (or signals the AuthContext to log out).
  4. Queues concurrent 401 failures so that only one refresh request is made at a time (prevents thundering herd of refresh calls).

**FR-013**: On app initialization (in `AuthContext`), the silent refresh flow MUST replace the current localStorage-based token check:
- Instead of reading `access_token` from `localStorage`, the `AuthContext` MUST call `POST /api/token/refresh` on mount.
- If the refresh succeeds (a valid refresh cookie exists in the browser), the new access token is stored in React state and the user info is fetched via `GET /api/me`.
- If the refresh fails (no refresh cookie, or cookie expired), `isLoading` is set to `false` and `isAuthenticated` remains `false`. The user is not logged in.
- This enables session persistence across page refreshes without localStorage.

**FR-014**: All Axios requests to the `/api/token/refresh` and `/api/token/revoke` endpoints MUST include `withCredentials: true` so the browser sends the HttpOnly refresh cookie.

### Login Page

**FR-015**: A Login page component MUST be created at `frontend/src/pages/Login.tsx` and rendered at the route `/login`.

**FR-016**: The Login page MUST contain a form with:
- A username input field (type `text`, required).
- A password input field (type `password`, required).
- A "Log in" submit button.
- A link to `/register` with text such as "Don't have an account? Register".

**FR-017**: On form submission, the Login page MUST call the `login(username, password)` function from `useAuth()`. The `login()` function handles `POST /api/token` and `GET /api/me` internally.

**FR-018**: If `login()` succeeds, the user MUST be redirected to `/home` (or to the originally-requested URL if the user was redirected to `/login` from a protected route).

**FR-019**: If `login()` throws an error (Axios error from `POST /api/token`), the Login page MUST extract the error message from `error.response.data.message` (the backend returns `{ "message": "Username or password is incorrect." }` with 401) and display it in the form area.

**FR-020**: While the login request is in progress, the submit button MUST be disabled and display a loading indicator (e.g. "Logging in..." text or a spinner).

### Register Page

**FR-021**: A Register page component MUST be created at `frontend/src/pages/Register.tsx` and rendered at the route `/register`.

**FR-022**: The Register page MUST contain a form with:
- A username input field (type `text`, required).
- An email input field (type `email`, required).
- A password input field (type `password`, required).
- A confirm password input field (type `password`, required).
- A "Register" submit button.
- A link to `/login` with text such as "Already have an account? Log in".

**FR-023**: Before submitting the form, the Register page MUST validate that the password and confirm password fields match. If they do not match, a client-side error message MUST be displayed (e.g. "Passwords do not match") and the form MUST NOT be submitted to the backend.

**FR-023a**: Password validation rules (client-side):
- Minimum length: 8 characters
- No maximum length enforced on client-side (backend may enforce)
- No complexity requirements (uppercase, numbers, symbols) for MVP

**FR-023b**: Username validation rules (client-side):
- Minimum length: 3 characters
- Maximum length: 20 characters
- Allowed characters: alphanumeric (a-z, A-Z, 0-9) and underscores only
- Must start with a letter

**FR-023c**: Email validation (client-side):
- Must match standard email format: `local@domain.tld`
- Use HTML5 `type="email"` input for basic validation
- Full validation performed by backend

**FR-024**: On form submission (after client-side validation passes), the Register page MUST call `POST /api/users` with `{ username, email, password }` using the centralized Axios instance.

**FR-025**: If registration succeeds (201), the Register page MUST immediately call `login(username, password)` from `useAuth()` to authenticate the new user, then redirect to `/` (the Welcome/onboarding page).

**FR-026**: If registration fails (400), the Register page MUST extract and display the error message from `error.response.data.error`. The backend returns specific messages:
- `"Email and Username are required"` (400)
- `"Email invalid or already registered"` (400)
- `"Username invalid or already registered"` (400)

**FR-027**: While the registration request is in progress, the submit button MUST be disabled and display a loading indicator.

### Protected Route Wrapper

**FR-028**: A `ProtectedRoute` component MUST be created at `frontend/src/components/ProtectedRoute.tsx` that wraps child components and enforces authentication.

**FR-029**: `ProtectedRoute` MUST use the `useAuth()` hook to check `isAuthenticated` and `isLoading`:
- If `isLoading` is `true`, render a loading indicator (e.g. a centered spinner). This prevents a flash of the login page while the AuthContext is performing a silent refresh on app initialization.
- If `isLoading` is `false` and `isAuthenticated` is `false`, redirect to `/login` using React Router's `<Navigate>` component. The current URL should be preserved (e.g. via `state={{ from: location }}`) so the user can be redirected back after login.
- If `isLoading` is `false` and `isAuthenticated` is `true`, render the children.

**FR-030**: The following routes in `App.tsx` MUST be wrapped with `ProtectedRoute`:
- `/` (Welcome/onboarding)
- `/home`
- `/vocabulary`
- `/practice`
- `/progress`
- `/settings`

**FR-031**: The Login (`/login`) and Register (`/register`) routes MUST NOT be wrapped with `ProtectedRoute`. They must be accessible to unauthenticated users.

### Welcome Page Update

**FR-032**: The Welcome page at `frontend/src/pages/Welcome.tsx` MUST remain visually unchanged. Its current behavior (showing onboarding with "Get started" leading to `/vocabulary` and "Skip for now" leading to `/home`) is preserved.

**FR-033**: The Welcome page is now only reachable by authenticated users (via FR-030). No authentication check logic is needed within `Welcome.tsx` itself.

### Logout Button

**FR-034**: The Sidebar component at `frontend/src/components/Sidebar.tsx` MUST be updated to include a logout button at the bottom of the sidebar, visually separated from the navigation items.

**FR-035**: The logout button MUST call the `logout()` function from `useAuth()` and then navigate to `/login` using React Router's `useNavigate()`.

**FR-036**: The logout button MUST display a recognizable logout icon (e.g. a "log out" or "arrow right from bracket" SVG icon) consistent with the existing sidebar icon style (line-style, 24x24 viewBox, `currentColor` stroke).

---

## Non-Functional Requirements

**NFR-001**: The Login and Register pages MUST load within 1 second on a standard broadband connection.

**NFR-002**: The Login and Register forms MUST be accessible: all input fields must have associated labels (via `<label htmlFor>` or `aria-label`), error messages must be announced to screen readers (via `aria-live="polite"` or similar), and the forms must be fully navigable via keyboard.

**NFR-003**: The protected route redirect MUST NOT cause a visible flash of the protected page content before redirecting. The loading state MUST be shown until auth status is determined (silent refresh completes).

**NFR-004**: The silent refresh flow on page load MUST complete within 2 seconds under normal network conditions. If the refresh takes longer (e.g. backend is slow), the loading indicator remains visible.

**NFR-004a**: Silent refresh timeout: If the refresh request takes longer than 10 seconds, the app SHOULD treat it as a failure, set `isLoading` to `false`, and redirect to `/login`.

**NFR-005**: Password fields MUST use `autoComplete="current-password"` on login and `autoComplete="new-password"` on register.

**NFR-006**: The access token MUST NOT be stored in localStorage, sessionStorage, or any other persistent browser storage. It MUST exist only in JavaScript memory (React state). This mitigates XSS-based token theft.

**NFR-007**: The refresh token cookie MUST have the `HttpOnly` flag set (preventing JavaScript access), `SameSite=Strict` (preventing CSRF), and `Secure` flag in production (HTTPS only). In development, `Secure` may be `False` to allow HTTP.

**NFR-008**: The 401 interceptor MUST handle concurrent request failures gracefully by queuing retries while a single refresh request is in-flight. This prevents multiple simultaneous refresh calls.

---

## UI/UX Requirements

**UIR-001**: The Login and Register pages MUST use the same visual style as the existing Welcome page: centered card on a purple gradient background (`bg-gradient-to-br from-purple-100 via-pink-50 to-blue-100`), white card with rounded corners (`rounded-3xl shadow-lg`), clean centered layout.

**UIR-002**: The Login and Register pages MUST NOT include the Sidebar or Layout wrapper. They are standalone full-screen pages, like the Welcome page.

**UIR-003**: Form input fields MUST use a consistent style: border (`border border-gray-300`), rounded (`rounded-lg`), padding (`px-4 py-3`), full width (`w-full`), with focus state (`focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent`).

**UIR-004**: The submit buttons MUST match the Welcome page "Get started" button style: purple background (`bg-purple-600 hover:bg-purple-700`), white text, full width, rounded (`rounded-full`), with a disabled state that reduces opacity (`disabled:opacity-50 disabled:cursor-not-allowed`).

**UIR-005**: Error messages MUST be displayed in red text (`text-red-600`) below the form or below the specific field that caused the error.

**UIR-006**: The navigation links between Login and Register pages (e.g. "Don't have an account? Register") MUST use purple text (`text-purple-600 hover:text-purple-700`) and be centered below the submit button.

**UIR-007**: The logout button in the Sidebar MUST be positioned at the bottom of the sidebar using flexbox spacing (`mt-auto`), visually separated from the navigation items. It should use the same icon button style as other sidebar items but with a distinct color on hover (e.g. `text-gray-400 hover:text-red-500 hover:bg-red-50`) to indicate a destructive action.

**UIR-008**: The loading indicator shown by `ProtectedRoute` while auth state is loading MUST be a centered spinner or minimal loading screen consistent with the app's purple color scheme. It MUST NOT show the sidebar or page content.

---

## Data Requirements

**DR-001**: A `TokenBlocklist` table MUST be created in the database with the following schema:

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key, auto-increment |
| `jti` | String(36) | Unique, not null, indexed |
| `created_ds` | DateTime | Not null |

**DR-002**: A Flask-Migrate migration MUST be generated and applied for the `TokenBlocklist` table.

**DR-003**: The existing `User` model and table are unchanged. The backend response shapes used by this milestone are:
- `POST /api/users` response: `{ "created_data": { "id": number, "username": string, "preferred_name": string | null } }` (201)
- `POST /api/token` response: `{ "access_token": string }` (200) + refresh token as HttpOnly cookie
- `GET /api/me` response: `{ "id": number, "username": string, "preferred_name": string | null }` (200)

---

## API Requirements

**AR-001**: The existing `POST /api/token` endpoint MUST be updated to also set a refresh token as an HttpOnly cookie. The JSON response body shape (`{ "access_token": "..." }`) remains the same.

**AR-002**: A new `POST /api/token/refresh` endpoint MUST be created:
- **Authentication**: Requires a valid, non-blocklisted refresh token via HttpOnly cookie.
- **Request body**: None required.
- **Success response** (200): `{ "access_token": "<new_access_token>" }` + new refresh token set as HttpOnly cookie.
- **Failure responses**:
  - 401: Missing or invalid refresh token.
  - 401: Refresh token has been revoked (blocklisted).

**AR-003**: A new `POST /api/token/revoke` endpoint MUST be created:
- **Authentication**: Requires a valid refresh token via HttpOnly cookie.
- **Request body**: None required.
- **Success response** (200): `{ "message": "Token revoked" }` + refresh token cookie cleared.
- **Failure responses**:
  - 401: Missing or invalid refresh token.

**AR-004**: All existing API endpoints (`/api/words`, `/api/me`, etc.) continue to accept access tokens via the `Authorization: Bearer <token>` header. No changes to their authentication mechanism.

---

## Out of Scope

The following items are explicitly NOT part of Milestone 1:

1. **Password reset / forgot password flow.** Users who forget their password have no recovery mechanism in the MVP.
2. **Email verification.** Registration does not require email confirmation.
3. **OAuth / social login.** Only username + password authentication is supported.
4. **User profile editing.** Users cannot change their username, email, or password from the frontend in this milestone.
5. **Remember me toggle.** Sessions always persist via the refresh cookie for 7 days.
6. **Rate limiting on login/register.** No client-side or server-side rate limiting for auth endpoints.
7. **CSRF double-submit cookie protection.** SameSite=Strict on the refresh cookie is sufficient for the MVP. Double-submit CSRF can be added in a future hardening pass.
8. **Token blocklist cleanup.** Expired entries in `TokenBlocklist` are not automatically pruned. A cleanup task can be added later. Note: The blocklist table may grow over time; a periodic cleanup job (e.g., daily) removing entries older than 30 days should be considered for production.
9. **Refresh token families / advanced token theft detection.** Simple rotation with blocklist is sufficient for MVP.
10. **Multiple tab session invalidation.** If a user logs out in one tab, other tabs will only detect the invalidated session on their next API call or refresh attempt. This is acceptable for MVP.

---

## Decisions Log

**DL-001**: The Welcome page (`/`) is protected and requires authentication. Unauthenticated users are redirected to `/login`. The login page serves as the effective landing page for unauthenticated users.

**DL-002**: After registration, users are automatically logged in and redirected to `/` (Welcome/onboarding), not to `/home`. This ensures new users go through the onboarding flow.

**DL-003**: The `ProtectedRoute` component is a wrapper component, consistent with React Router v6 patterns and the existing `Layout` component pattern.

**DL-004**: The registration API call lives directly in the Register page component (not in AuthContext) since it is a one-time action. After successful registration, AuthContext's `login()` is called to establish the session.

**DL-005**: Access token is kept in memory only (React state). Refresh token is an HttpOnly cookie. This is more secure than localStorage because:
- XSS attacks cannot steal the access token from memory as easily as from localStorage.
- The refresh token is completely inaccessible to JavaScript.
- SameSite=Strict prevents CSRF on the cookie-based refresh endpoint.

**DL-006**: The Axios interceptor needs a mechanism to receive the access token from React state since it is a module-level singleton outside the React tree. The chosen approach is a module-level `setAccessToken()` function that AuthContext calls whenever the token changes. This avoids coupling Axios to localStorage.

**DL-007**: `JWT_COOKIE_CSRF_PROTECT = False` for the MVP. Since the refresh cookie is SameSite=Strict, cross-origin requests cannot include it. Combined with the fact that the refresh endpoint does not accept any user-controlled body data, CSRF risk is minimal.

**DL-008**: Token rotation on refresh: each refresh call issues a new refresh token and blocklists the old one. This limits the window of exposure if a refresh token is somehow compromised.
