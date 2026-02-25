import { useState, FormEvent, useMemo } from 'react'
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
  const [touched, setTouched] = useState({ password: false, confirmPassword: false })

  const { login } = useAuth()
  const navigate = useNavigate()

  // Real-time password validation
  const passwordError = useMemo(() => {
    if (!touched.password || password.length === 0) return null
    if (password.length < 8) return 'Password must be at least 8 characters'
    if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter'
    if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter'
    if (!/\d/.test(password)) return 'Password must contain at least one number'
    if (!/^[a-zA-Z0-9]+$/.test(password)) return 'Password must contain only letters and numbers'
    return null
  }, [password, touched.password])

  // Real-time confirm password validation
  const confirmPasswordError = useMemo(() => {
    if (!touched.confirmPassword || confirmPassword.length === 0) return null
    if (password !== confirmPassword) return 'Passwords do not match'
    return null
  }, [password, confirmPassword, touched.confirmPassword])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    // Mark all fields as touched to show validation errors
    setTouched({ password: true, confirmPassword: true })

    // Client-side validation: password match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Client-side validation: password requirements
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (!/[A-Z]/.test(password)) {
      setError('Password must contain at least one uppercase letter')
      return
    }
    if (!/[a-z]/.test(password)) {
      setError('Password must contain at least one lowercase letter')
      return
    }
    if (!/\d/.test(password)) {
      setError('Password must contain at least one number')
      return
    }
    if (!/^[a-zA-Z0-9]+$/.test(password)) {
      setError('Password must contain only letters and numbers')
      return
    }

    // Client-side validation: username
    if (username.length < 3 || username.length > 20) {
      setError('Username must be between 3 and 20 characters')
      return
    }

    // Client-side validation: username format (alphanumeric + underscore, must start with letter)
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(username)) {
      setError('Username must start with a letter and contain only letters, numbers, and underscores')
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
              onBlur={() => setTouched(prev => ({ ...prev, password: true }))}
              autoComplete="new-password"
              className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent ${
                passwordError
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-300'
              }`}
              placeholder="Create a password"
              aria-invalid={passwordError ? 'true' : 'false'}
              aria-describedby={passwordError ? 'password-error' : 'password-help'}
            />
            {passwordError ? (
              <p id="password-error" className="mt-1 text-sm text-red-600">
                {passwordError}
              </p>
            ) : (
              <p id="password-help" className="mt-1 text-sm text-gray-500">
                Must be at least 8 characters with uppercase, lowercase, and number
              </p>
            )}
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
              onBlur={() => setTouched(prev => ({ ...prev, confirmPassword: true }))}
              autoComplete="new-password"
              className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent ${
                confirmPasswordError
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-300'
              }`}
              placeholder="Confirm your password"
              aria-invalid={confirmPasswordError ? 'true' : 'false'}
              aria-describedby={confirmPasswordError ? 'confirm-password-error' : undefined}
            />
            {confirmPasswordError && (
              <p id="confirm-password-error" className="mt-1 text-sm text-red-600">
                {confirmPasswordError}
              </p>
            )}
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
