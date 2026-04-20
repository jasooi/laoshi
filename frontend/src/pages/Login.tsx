import { useState, FormEvent } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ButtonSpinner from '../components/ButtonSpinner'

const Login = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Get the page the user was trying to access before being redirected
  // Always land on /home for home deck detail pages so the placeholder shows first
  const savedPath = (location.state as { from?: { pathname: string } })?.from?.pathname || '/home'
  const from = savedPath.startsWith('/home/deck/') ? '/home' : savedPath

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full">
        <h1 className="text-2xl font-bold text-warm-black mb-2 text-center">
          Welcome back
        </h1>
        <p className="text-warm-muted mb-8 text-center">
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
            <label htmlFor="username" className="block text-sm font-medium text-warm-black mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full px-4 py-3 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-warm-black mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-4 py-3 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-sage hover:bg-sage/80 text-white font-semibold py-4 px-8 rounded-full transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="flex items-center justify-center gap-2">
              {isSubmitting && <ButtonSpinner />}
              {isSubmitting ? 'Logging in...' : 'Log in'}
            </span>
          </button>
        </form>

        <p className="text-center mt-4">
          <Link to="/forgot-password" className="text-sm text-sage hover:text-sage/80 font-medium">
            Forgot password?
          </Link>
        </p>

        <p className="text-center mt-4 text-warm-muted">
          Don't have an account?{' '}
          <Link to="/register" className="text-sage hover:text-sage/80 font-medium">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Login
