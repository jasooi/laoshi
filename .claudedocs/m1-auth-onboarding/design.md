# Milestone 1: Authentication & Onboarding -- Design Document

## Design Overview

This document describes HOW the remaining M1 tasks will be implemented. The work spans both backend (secure token infrastructure) and frontend (auth pages, protected routes, logout).

**Key architectural change**: The current auth flow stores the JWT access token in `localStorage` and reads it via an Axios interceptor. This milestone replaces that with a more secure pattern:
- **Access token**: short-lived (15 min), stored in React state (memory only), sent via `Authorization: Bearer` header.
- **Refresh token**: long-lived (7 days), stored as an HttpOnly/SameSite=Strict cookie, used only to obtain new access tokens.
- **Silent refresh**: on page load, the app calls `/api/token/refresh` to restore the session from the refresh cookie, eliminating the need for localStorage.

The guiding principles are:
1. **Security first**: tokens never touch localStorage; refresh tokens are inaccessible to JavaScript.
2. **Consistency with existing patterns**: follow Flask-RESTful resource pattern, existing model conventions, and Tailwind-based frontend styling.
3. **Minimal disruption**: existing API endpoints continue to accept `Authorization: Bearer` headers. Only the token issuance and frontend storage change.

---

## Architecture & Approach

### High-Level Auth Flow (After M1)

```
Browser (React + Vite dev server :5173)
  |
  | 1. Login: POST /api/token { username, password }
  |    <- Response: { access_token } + Set-Cookie: refresh_token (HttpOnly)
  |
  | 2. API calls: Authorization: Bearer <access_token> (from React state)
  |
  | 3. On 401: POST /api/token/refresh (browser sends refresh cookie automatically)
  |    <- Response: { access_token } + Set-Cookie: new_refresh_token (HttpOnly)
  |    -> Retry original request with new access token
  |
  | 4. Logout: POST /api/token/revoke (browser sends refresh cookie)
  |    <- Response: { message } + Clear-Cookie: refresh_token
  |
  v
Vite Proxy (/api/* -> http://localhost:5000/api/*)
  |
  v
Flask (:5000) with Flask-JWT-Extended
  |
  v
TokenBlocklist (SQLAlchemy) for revoked refresh tokens
```

### Token Lifecycle

```
Registration:
  POST /api/users -> 201 (account created)
  POST /api/token -> 200 (access_token in body, refresh_token in cookie)
  GET /api/me -> 200 (user info)
  -> Redirect to / (onboarding)

Login:
  POST /api/token -> 200 (access_token in body, refresh_token in cookie)
  GET /api/me -> 200 (user info)
  -> Redirect to /home

Page Refresh (silent refresh):
  POST /api/token/refresh (refresh cookie sent by browser)
  -> 200: new access_token in body, new refresh_token in cookie
  -> 401: session expired, redirect to /login

API Call (401 interceptor):
  Original request -> 401
  POST /api/token/refresh -> new access_token
  Retry original request -> success

Logout:
  POST /api/token/revoke (refresh cookie sent by browser)
  -> Clear access_token from React state
  -> Redirect to /login
```

---

## Backend Design

### 1. Token Expiry Configuration

**File**: `backend/config.py`

Add token expiry and cookie settings to the `Config` class:

```python
from datetime import timedelta

class Config():
    # ... existing settings ...

    # JWT Token Expiry
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # JWT Token Locations -- accept access tokens from headers, refresh from cookies
    JWT_TOKEN_LOCATION = ['headers', 'cookies']

    # JWT Cookie Settings
    JWT_REFRESH_COOKIE_PATH = '/api/token'  # Scope refresh cookie to token endpoints
    JWT_COOKIE_SECURE = False               # Set True in production (requires HTTPS)
    JWT_COOKIE_SAMESITE = 'Strict'
    JWT_COOKIE_CSRF_PROTECT = False         # SameSite=Strict is sufficient for MVP
```

Update `TestConfig` to include appropriate test overrides:

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-secret-key'
    JWT_COOKIE_SECURE = False  # Allow HTTP in tests
```

### 2. TokenBlocklist Model

**File**: `backend/models.py`

Add a new model after the existing `SessionWord` class:

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

The `jti` column is indexed for fast lookup since every authenticated request will check the blocklist (for refresh tokens on the `/api/token/*` endpoints).

**Migration**: Run `flask db migrate -m "add token_blocklist table"` then `flask db upgrade`.

### 3. Blocklist Loader Callback

**File**: `backend/app.py` (or `backend/extensions.py`)

Register the blocklist check callback. This should be done after `jwt.init_app(app)`. The cleanest place is in `register_extensions()` in `app.py`:

```python
from models import TokenBlocklist

def register_extensions(app):
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app)
    CORS(app, supports_credentials=True)  # Updated: supports_credentials for cookies

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return TokenBlocklist.is_blocklisted(jti)
```

Note: `CORS(app, supports_credentials=True)` is needed so that the Vite proxy correctly forwards cookies. In development, the Vite proxy handles this, but `supports_credentials=True` ensures it works if the frontend ever calls the backend directly.

### 4. Updated TokenResource (Login)

**File**: `backend/resources.py`

Update the existing `TokenResource.post()` to issue both tokens:

```python
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_refresh_cookies, unset_refresh_cookies
)
from flask import request, jsonify, make_response

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

Key change: `set_refresh_cookies(response, refresh_token)` sets the refresh token as an HttpOnly cookie on the response. The `make_response()` call is needed to access the response object for cookie manipulation.

### 5. TokenRefreshResource (New Endpoint)

**File**: `backend/resources.py`

```python
from datetime import datetime

class TokenRefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Issue a new access token + rotated refresh token."""
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

### 6. TokenRevokeResource (New Endpoint)

**File**: `backend/resources.py`

```python
from datetime import datetime

class TokenRevokeResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Revoke the refresh token (logout)."""
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

### 7. Route Registration

**File**: `backend/app.py`

Add the new resources to `register_resources()`:

```python
from resources import (..., TokenRefreshResource, TokenRevokeResource)

def register_resources(app):
    api = Api(app, prefix='/api')
    # ... existing routes ...
    api.add_resource(TokenResource, '/token')
    api.add_resource(TokenRefreshResource, '/token/refresh')
    api.add_resource(TokenRevokeResource, '/token/revoke')
    api.add_resource(MeResource, '/me')
```

### 8. Import Updates

**File**: `backend/resources.py`

Add the new imports at the top:

```python
from flask import request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_refresh_cookies, unset_refresh_cookies
)
from models import Word, User, SessionWord, UserSession, TokenBlocklist
```

---

## Frontend Design

### 9. Axios Instance Update -- Token Setter and 401 Interceptor

**File**: `frontend/src/lib/api.ts`

The Axios instance needs two changes: (a) a way to receive the access token from React state instead of localStorage, and (b) a 401 interceptor for automatic refresh.

```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Access token management (in-memory) ---

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

// Request interceptor: attach in-memory access token
api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// --- 401 Response interceptor: automatic token refresh ---

let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
  config: InternalAxiosRequestConfig
}> = []

const processQueue = (error: AxiosError | null, token: string | null) => {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error)
    } else {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      resolve(api(config))
    }
  })
  failedQueue = []
}

// Callback for when refresh fails (set by AuthContext)
let onRefreshFailure: (() => void) | null = null

export function setOnRefreshFailure(callback: () => void) {
  onRefreshFailure = callback
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Only attempt refresh on 401, and not on token endpoints themselves
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/api/token')
    ) {
      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: originalRequest })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshResponse = await axios.post(
          '/api/token/refresh',
          {},
          { withCredentials: true }
        )
        const newToken = refreshResponse.data.access_token
        setAccessToken(newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        processQueue(null, newToken)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as AxiosError, null)
        setAccessToken(null)
        if (onRefreshFailure) {
          onRefreshFailure()
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

**Design decisions:**
- The `accessToken` module-level variable bridges React state and the Axios singleton. `AuthContext` calls `setAccessToken()` whenever the token changes.
- The refresh call uses a raw `axios.post()` (not the `api` instance) with `withCredentials: true` to ensure the HttpOnly cookie is sent. It does NOT go through the interceptor to avoid infinite refresh loops.
- The `failedQueue` pattern ensures only one refresh request is made even if multiple API calls fail simultaneously.
- The `onRefreshFailure` callback lets AuthContext handle logout/redirect when the refresh fails.
- Requests to `/api/token*` are excluded from the 401 interceptor to prevent refresh loops.

### 10. AuthContext Update -- In-Memory Tokens and Silent Refresh

**File**: `frontend/src/contexts/AuthContext.tsx`

Complete rewrite of the auth context:

```typescript
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { setAccessToken, setOnRefreshFailure } from '../lib/api'
import axios from 'axios'

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
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Update the Axios module token whenever React state changes
  useEffect(() => {
    setAccessToken(token)
  }, [token])

  // Logout handler (also used as refresh failure callback)
  const handleLogout = useCallback(() => {
    setToken(null)
    setUser(null)
    setAccessToken(null)
  }, [])

  // Register the refresh failure callback with the Axios interceptor
  useEffect(() => {
    setOnRefreshFailure(handleLogout)
  }, [handleLogout])

  // Silent refresh on mount -- replaces the localStorage check
  useEffect(() => {
    const silentRefresh = async () => {
      try {
        const refreshResponse = await axios.post(
          '/api/token/refresh',
          {},
          { withCredentials: true }
        )
        const newAccessToken = refreshResponse.data.access_token
        setToken(newAccessToken)
        setAccessToken(newAccessToken)

        // Fetch user info
        const userResponse = await api.get('/api/me')
        setUser(userResponse.data)
      } catch {
        // No valid refresh cookie -- user is not logged in
        setToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    silentRefresh()
  }, [])

  const login = async (username: string, password: string) => {
    // POST /api/token with withCredentials so the refresh cookie is set
    const response = await api.post('/api/token', { username, password }, {
      withCredentials: true,
    })
    const accessToken = response.data.access_token
    setToken(accessToken)
    setAccessToken(accessToken)

    // Fetch user info
    const userResponse = await api.get('/api/me')
    setUser(userResponse.data)
  }

  const logout = async () => {
    try {
      await axios.post('/api/token/revoke', {}, { withCredentials: true })
    } catch {
      // Even if revoke fails, clear local state
    }
    handleLogout()
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

**Key changes from current implementation:**
1. No `localStorage` references at all.
2. `login()` uses `withCredentials: true` so the browser stores the refresh cookie.
3. `logout()` calls `POST /api/token/revoke` to invalidate the refresh token server-side.
4. On mount, `silentRefresh()` calls `POST /api/token/refresh` instead of checking localStorage. If no valid refresh cookie exists, the user is not authenticated.
5. The `useEffect` for `setAccessToken(token)` keeps the Axios module-level token in sync with React state.

**Note on `useNavigate`**: Navigation after logout is handled by the component calling `logout()` (e.g. the Sidebar logout button), not by AuthContext itself. AuthContext should not depend on React Router (it wraps the Router in the component tree). The `handleLogout` callback from the 401 interceptor simply clears state; the `ProtectedRoute` component handles the redirect to `/login`.

### 11. Login Page

**New file**: `frontend/src/pages/Login.tsx`

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const Login = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Get the page the user was trying to access before being redirected
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/home'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err: any) {
      const message = err.response?.data?.message || 'Login failed. Please try again.'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          Welcome back
        </h1>
        <p className="text-gray-600 mb-8 text-center">
          Log in to continue learning
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Error display */}
          {error && (
            <div className="text-red-600 text-sm text-center" role="alert" aria-live="polite">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 px-8 rounded-full transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Logging in...' : 'Log in'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-purple-600 hover:text-purple-700 font-medium">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Login
```

**Design notes:**
- The `from` variable captures the originally-requested URL from `location.state` (set by the `ProtectedRoute` redirect). After login, the user is sent back to that URL.
- Error display uses `role="alert"` and `aria-live="polite"` for screen reader accessibility.
- The form uses `e.preventDefault()` to prevent page reload on submit.
- Styling matches the Welcome page card layout exactly.

### 12. Register Page

**New file**: `frontend/src/pages/Register.tsx`

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../lib/api'

const Register = () => {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    // Client-side validation: password match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsSubmitting(true)

    try {
      // Step 1: Register
      await api.post('/api/users', { username, email, password })

      // Step 2: Auto-login
      await login(username, password)

      // Step 3: Redirect to onboarding
      navigate('/', { replace: true })
    } catch (err: any) {
      // Backend returns { "error": "..." } for registration errors
      // and { "message": "..." } for login errors
      const message =
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Registration failed. Please try again.'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          Create your account
        </h1>
        <p className="text-gray-600 mb-8 text-center">
          Start your Mandarin learning journey
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="text-red-600 text-sm text-center" role="alert" aria-live="polite">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Enter your email"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Create a password"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Confirm your password"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 px-8 rounded-full transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-purple-600 hover:text-purple-700 font-medium">
            Log in
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Register
```

**Design notes:**
- Registration uses the `api` Axios instance directly for `POST /api/users` (the registration endpoint is public, no JWT needed).
- After successful registration, `login()` from AuthContext is called to establish the session (access token + refresh cookie).
- The redirect goes to `/` (Welcome/onboarding) so new users go through the guided onboarding.
- The error handler checks both `error.response.data.error` (registration errors) and `error.response.data.message` (login errors) since both can occur in the two-step flow.

### 13. ProtectedRoute Component

**New file**: `frontend/src/components/ProtectedRoute.tsx`

```typescript
import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 via-pink-50 to-blue-100">
        <div className="text-purple-600 text-lg font-medium">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
```

**Design notes:**
- The loading state uses the same gradient background as the Login/Register/Welcome pages for visual consistency during the brief loading moment.
- `state={{ from: location }}` passes the attempted URL so the Login page can redirect back after successful authentication.
- `replace` prevents the `/login` redirect from being added to the browser history stack.

### 14. App.tsx Route Updates

**File**: `frontend/src/App.tsx`

```typescript
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Welcome from './pages/Welcome'
import Login from './pages/Login'
import Register from './pages/Register'
import Home from './pages/Home'
import Practice from './pages/Practice'
import Progress from './pages/Progress'
import Vocabulary from './pages/Vocabulary'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes -- no auth required */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected routes */}
        <Route path="/" element={<ProtectedRoute><Welcome /></ProtectedRoute>} />
        <Route path="/practice" element={<ProtectedRoute><Practice /></ProtectedRoute>} />
        <Route path="/home" element={<ProtectedRoute><Layout><Home /></Layout></ProtectedRoute>} />
        <Route path="/progress" element={<ProtectedRoute><Layout><Progress /></Layout></ProtectedRoute>} />
        <Route path="/vocabulary" element={<ProtectedRoute><Layout><Vocabulary /></Layout></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
      </Routes>
    </Router>
  )
}

export default App
```

**Changes from current `App.tsx`:**
1. Import `ProtectedRoute`, `Login`, `Register`.
2. Add `/login` and `/register` routes (public).
3. Wrap all existing routes with `<ProtectedRoute>`.
4. Route ordering: public routes first, then protected routes.
5. **Note**: The `/practice` route is intentionally NOT wrapped in `<Layout>` as it uses a different layout from the other pages.

### 15. Sidebar Logout Button

**File**: `frontend/src/components/Sidebar.tsx`

Add `useAuth` and `useNavigate` imports, add a logout button at the bottom:

```typescript
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

// ... existing interface and sidebarItems ...

const Sidebar = ({ currentPath }: SidebarProps) => {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  // ... existing sidebarItems array ...

  return (
    <aside className="w-20 bg-white border-r border-gray-200 flex flex-col items-center py-6">
      {/* Logo/Brand */}
      <div className="mb-4">
        <img src="/laoshi-logo.png" alt="Laoshi Logo" className="w-16 h-16 rounded-2xl object-cover" />
      </div>

      {/* Navigation Items */}
      <div className="space-y-4">
        {sidebarItems.map((item) => {
          const isActive = currentPath === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                isActive
                  ? 'bg-purple-100 text-purple-600'
                  : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
              }`}
              title={item.label}
            >
              {item.icon}
            </Link>
          )
        })}
      </div>

      {/* Logout Button -- pushed to bottom */}
      <button
        onClick={handleLogout}
        className="mt-auto w-12 h-12 rounded-xl flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
        title="Log out"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
          />
        </svg>
      </button>
    </aside>
  )
}
```

**Design notes:**
- The logout button uses `mt-auto` within the flex column to push it to the bottom of the sidebar.
- The existing `space-y-4` class on the aside is replaced with a `<div className="space-y-4">` wrapper around the nav items, and the aside uses plain flex with `py-6` (no `space-y-4`) so that `mt-auto` works correctly.
- The logout icon is a "door with arrow" SVG (commonly used for logout) matching the existing icon style: `w-6 h-6`, `fill="none"`, `stroke="currentColor"`.
- Hover state uses red tint (`hover:text-red-500 hover:bg-red-50`) to signal a destructive action, distinct from the purple active state of navigation items.

### 16. Vite Proxy Cookie Forwarding

**File**: `vite.config.ts`

Ensure the Vite proxy forwards cookies correctly. The current config may need `cookieDomainRewrite` or the proxy may need to be checked:

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    },
  },
},
```

The Vite proxy should forward cookies by default since it proxies the full request/response. No changes should be needed, but this should be verified during implementation. If cookies are not being set, add `secure: false` to the proxy config or check that `JWT_COOKIE_SECURE = False` in development config.

---

## Data Flow: Key User Interactions

### Flow 1: New User Registration + Onboarding

```
1. User navigates to /register (public route, no ProtectedRoute wrapper)
2. User fills in username, email, password, confirm password
3. User clicks "Register"
4. Frontend validates password match (client-side)
5. POST /api/users { username, email, password }
   -> Backend creates user, returns 201 { created_data: { id, username, preferred_name } }
6. Frontend calls login(username, password) from AuthContext
7. login() calls POST /api/token { username, password } with withCredentials: true
   -> Backend creates access_token + refresh_token
   -> Returns { access_token } in body + refresh_token as HttpOnly cookie
8. AuthContext stores access_token in React state, calls setAccessToken()
9. login() calls GET /api/me (access token now in Axios interceptor)
   -> Returns { id, username, preferred_name }
10. AuthContext stores user info
11. Register page redirects to / (Welcome page)
12. ProtectedRoute checks isAuthenticated = true, renders Welcome
13. Welcome page shows onboarding: "Get started" -> /vocabulary
```

### Flow 2: Returning User Login

```
1. User navigates to /login (public route)
2. User enters username and password
3. User clicks "Log in"
4. Login page calls login(username, password) from AuthContext
5. POST /api/token { username, password } with withCredentials: true
   -> Returns { access_token } + refresh cookie
6. AuthContext stores access_token in state
7. GET /api/me -> user info stored
8. Login page redirects to /home (or the originally-requested URL from location.state)
9. ProtectedRoute checks isAuthenticated = true, renders Home
```

### Flow 3: Page Refresh (Silent Refresh)

```
1. User refreshes the page (or opens a new tab to the app)
2. main.tsx renders AuthProvider > App
3. AuthProvider's useEffect fires silentRefresh()
4. POST /api/token/refresh with withCredentials: true
   (browser automatically sends the HttpOnly refresh cookie)
5a. If refresh succeeds (200):
   -> Backend blocklists old refresh token, issues new access + refresh tokens
   -> AuthContext stores new access_token in state
   -> GET /api/me -> user info stored
   -> isLoading = false, isAuthenticated = true
   -> ProtectedRoute renders children normally
5b. If refresh fails (401 -- no cookie, expired, or revoked):
   -> AuthContext clears state
   -> isLoading = false, isAuthenticated = false
   -> ProtectedRoute redirects to /login
```

### Flow 4: Access Token Expiry During Use

```
1. User is working, access token expires (after 15 minutes)
2. User triggers an API call (e.g. fetches vocabulary)
3. api.get('/api/words') -> 401 (expired access token)
4. Axios 401 interceptor catches the error
5. Interceptor calls POST /api/token/refresh with withCredentials: true
6a. If refresh succeeds:
   -> New access_token stored, original request retried
   -> User sees no interruption
6b. If refresh fails:
   -> onRefreshFailure callback fires -> AuthContext clears state
   -> ProtectedRoute detects isAuthenticated = false -> redirect to /login
```

### Flow 5: Logout

```
1. User clicks logout button in Sidebar
2. Sidebar calls logout() from AuthContext, then navigate('/login')
3. logout() calls POST /api/token/revoke with withCredentials: true
   -> Backend blocklists the refresh token, clears the cookie
4. AuthContext clears access_token and user from state
5. navigate('/login') renders the Login page
6. Any subsequent navigation to protected routes redirects to /login
```

---

## Error Handling

### Frontend Error Handling

| Scenario | Handling |
|---|---|
| Login with wrong credentials | `POST /api/token` returns 401 with `{ message: "Username or password is incorrect." }`. Login page displays this message. |
| Register with duplicate email | `POST /api/users` returns 400 with `{ error: "Email invalid or already registered" }`. Register page displays this message. |
| Register with duplicate username | `POST /api/users` returns 400 with `{ error: "Username invalid or already registered" }`. Register page displays this message. |
| Register with missing fields | `POST /api/users` returns 400 with `{ error: "Email and Username are required" }`. Register page displays this message. |
| Password mismatch on register | Client-side validation shows "Passwords do not match" before any API call. |
| Access token expired | 401 interceptor silently refreshes and retries. User sees no error. |
| Refresh token expired | Silent refresh fails. User is redirected to `/login`. No error message shown (natural session expiry). |
| Network error (backend down) | Axios throws a network error. Login/Register pages show "Login failed. Please try again." or similar generic message. |
| Silent refresh timeout (>10s) | After 10 seconds, treat as failure. Set `isLoading=false`, redirect to `/login`. |
| Silent refresh fails on page load | `isLoading` transitions to `false`, `isAuthenticated` stays `false`, `ProtectedRoute` redirects to `/login`. |

### Backend Error Handling

| Scenario | Response |
|---|---|
| `/api/token/refresh` with no cookie | 401 `{ message: "Missing cookie..." }` (Flask-JWT-Extended default) |
| `/api/token/refresh` with blocklisted token | 401 `{ message: "Token has been revoked" }` (from blocklist loader) |
| `/api/token/refresh` with expired token | 401 `{ message: "Token has expired" }` (Flask-JWT-Extended default) |
| `/api/token/revoke` with invalid token | 401 (same as above) |

---

## Security Considerations

1. **Access token in memory only**: The access token is stored in React state, not in localStorage or sessionStorage. This means it is not accessible to XSS attacks that read storage APIs. However, a sufficiently sophisticated XSS attack could still extract it from memory. The short 15-minute expiry limits the window of exposure.

2. **Refresh token as HttpOnly cookie**: The refresh token cannot be read by JavaScript at all. It is only sent by the browser to URLs matching the cookie path (`/api/token/*`). Combined with `SameSite=Strict`, this prevents CSRF attacks from triggering refresh calls.

3. **Token rotation on refresh**: Each call to `/api/token/refresh` blocklists the old refresh token and issues a new one. If a refresh token is somehow stolen, it can only be used once before the legitimate user's next refresh invalidates it.

4. **CORS with credentials**: `supports_credentials=True` in Flask-CORS is needed for cross-origin cookie handling. In development, the Vite proxy handles same-origin concerns. In production, CORS should be configured with specific allowed origins.

5. **No CSRF double-submit**: Since the refresh cookie is `SameSite=Strict`, cross-origin requests cannot include it. This makes CSRF attacks against the refresh endpoint impractical. Double-submit cookie protection can be added in a future hardening pass if needed.

6. **JWT_COOKIE_SECURE = False in development**: The `Secure` flag is disabled in development to allow HTTP. In production, this MUST be set to `True` to ensure the cookie is only sent over HTTPS.

---

## Testing Strategy

### Backend Tests (pytest)

| Test | Type | What it verifies |
|---|---|---|
| `test_login_returns_access_token_and_refresh_cookie` | Integration | `POST /api/token` returns access token in body and sets refresh cookie |
| `test_refresh_returns_new_tokens` | Integration | `POST /api/token/refresh` with valid refresh cookie returns new access token and new refresh cookie |
| `test_refresh_blocklists_old_token` | Integration | After refresh, the old refresh token's jti is in the TokenBlocklist |
| `test_refresh_with_blocklisted_token_fails` | Integration | Using a blocklisted refresh token returns 401 |
| `test_revoke_clears_cookie_and_blocklists` | Integration | `POST /api/token/revoke` adds jti to blocklist and clears cookie |
| `test_expired_access_token_returns_401` | Integration | An expired access token is rejected by protected endpoints |
| `test_token_blocklist_model` | Unit | TokenBlocklist.add() and TokenBlocklist.is_blocklisted() work correctly |

### Frontend Tests (Vitest + React Testing Library)

| Test | Type | What it verifies |
|---|---|---|
| `Login page renders form fields` | Component | Username, password inputs and submit button render |
| `Login page shows error on failed login` | Component | Error message appears when login fails |
| `Register page renders form fields` | Component | Username, email, password, confirm password inputs render |
| `Register page shows password mismatch error` | Component | Client-side validation for mismatched passwords |
| `ProtectedRoute redirects when not authenticated` | Component | Renders Navigate to /login when isAuthenticated is false |
| `ProtectedRoute shows loading state` | Component | Renders loading indicator when isLoading is true |
| `ProtectedRoute renders children when authenticated` | Component | Renders children when isAuthenticated is true |
| `Sidebar renders logout button` | Component | Logout button is visible in the sidebar |

---

## Technical Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Vite proxy does not forward Set-Cookie headers from backend | Medium | High | Verify during T-001 implementation. The Vite HTTP proxy should pass through all headers. If not, check proxy config or use `cookieDomainRewrite`. |
| Flask-JWT-Extended cookie handling conflicts with Flask-RESTful response pattern | Medium | Medium | Flask-RESTful returns dicts/tuples; cookie setting needs a `make_response()` call. The design accounts for this with explicit `make_response()` in token endpoints. |
| `withCredentials: true` causes CORS preflight issues | Low | Medium | In development, the Vite proxy eliminates CORS. In production, ensure Flask-CORS is configured with `supports_credentials=True` and specific `origins`. |
| Multiple tabs: one tab refreshes and blocklists the token while another tab uses the old token | Medium | Low | The old access token continues to work until it expires (15 min). The other tab's next refresh will fail, requiring a new login. This is acceptable for MVP. |
| Concurrent 401s cause race condition in refresh interceptor | Medium | Medium | The `failedQueue` pattern in the Axios interceptor ensures only one refresh is in-flight at a time. Other failed requests are queued and retried after refresh. |
| SQLite in tests does not support concurrent writes for blocklist | Low | Low | Tests are sequential within pytest. No concurrency issues expected. |

---

## Alternatives Considered

### Token Storage: localStorage vs. Memory + HttpOnly Cookie
**Current approach (M0)**: Access token in localStorage, read by Axios interceptor.
**New approach (M1)**: Access token in React state, refresh token as HttpOnly cookie.
**Why changed**: localStorage is vulnerable to XSS. Any injected JavaScript can read `localStorage.getItem('access_token')` and exfiltrate the token. Memory-based storage with HttpOnly cookies is the industry-standard pattern for SPAs.

### Refresh Strategy: Proactive vs. Reactive
**Alternative**: Set a timer to refresh the access token before it expires (proactive refresh).
**Chosen approach**: Refresh on 401 (reactive).
**Why**: Reactive refresh is simpler, handles all edge cases (clock skew, backend restarts), and avoids maintaining timer state. The brief 401 + retry adds negligible latency.

### Token Blocklist: Database Table vs. Redis
**Alternative**: Use Redis for the token blocklist (faster lookups).
**Chosen approach**: SQLAlchemy/PostgreSQL table.
**Why**: The project does not use Redis. Adding a new infrastructure dependency for a blocklist that is checked only on refresh (not on every API call) is unnecessary. The `jti` column is indexed for fast lookups.

### CSRF Protection: Double-Submit Cookie vs. SameSite Only
**Alternative**: Enable Flask-JWT-Extended's CSRF double-submit cookie protection.
**Chosen approach**: SameSite=Strict only.
**Why**: SameSite=Strict prevents cross-origin requests from including the cookie, which is the primary CSRF vector. Double-submit adds complexity (an extra header the frontend must send) with minimal benefit when SameSite is already Strict. Can be revisited in a hardening milestone.

### AuthContext: Navigate Internally vs. Let Components Handle Navigation
**Alternative**: Have AuthContext use `useNavigate()` to redirect to `/login` on logout or refresh failure.
**Chosen approach**: AuthContext only manages state; components handle navigation.
**Why**: AuthContext wraps the Router in the component tree (`main.tsx` renders `AuthProvider > App > Router`). Using `useNavigate()` inside AuthContext would require it to be inside the Router, changing the component hierarchy. Keeping navigation in components (ProtectedRoute for redirects, Sidebar for logout redirect) is cleaner.
