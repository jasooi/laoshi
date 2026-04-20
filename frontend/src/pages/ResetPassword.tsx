import { useState, useMemo, FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { passwordResetApi } from '../lib/api'
import ButtonSpinner from '../components/ButtonSpinner'

const ResetPassword = () => {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [touched, setTouched] = useState({ password: false, confirmPassword: false })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const passwordError = useMemo(() => {
    if (!touched.password || password.length === 0) return null
    if (password.length < 8) return 'Password must be at least 8 characters'
    if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter'
    if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter'
    if (!/\d/.test(password)) return 'Password must contain at least one number'
    if (!/^[a-zA-Z0-9]+$/.test(password)) return 'Password must contain only letters and numbers'
    return null
  }, [password, touched.password])

  const confirmPasswordError = useMemo(() => {
    if (!touched.confirmPassword || confirmPassword.length === 0) return null
    if (password !== confirmPassword) return 'Passwords do not match'
    return null
  }, [password, confirmPassword, touched.confirmPassword])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (passwordError || confirmPasswordError) return
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsSubmitting(true)
    try {
      await passwordResetApi.resetPassword(token, password)
      setSuccess(true)
    } catch (err: any) {
      const message = err.response?.data?.error || 'Something went wrong. Please try again.'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
        <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-warm-black mb-3">Invalid Reset Link</h1>
          <p className="text-warm-muted mb-8">
            This password reset link is invalid. Please request a new one.
          </p>
          <Link
            to="/forgot-password"
            className="inline-block bg-sage hover:bg-sage/80 text-white font-semibold py-3 px-8 rounded-full transition-colors shadow-md"
          >
            Request New Link
          </Link>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
        <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-warm-black mb-3">Password Reset Successful</h1>
          <p className="text-warm-muted mb-8">
            Your password has been updated. You can now log in with your new password.
          </p>
          <Link
            to="/login"
            className="inline-block bg-sage hover:bg-sage/80 text-white font-semibold py-3 px-8 rounded-full transition-colors shadow-md"
          >
            Go to Login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full">
        <h1 className="text-2xl font-bold text-warm-black mb-2 text-center">
          Reset your password
        </h1>
        <p className="text-warm-muted mb-8 text-center">
          Enter your new password below.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="text-red-600 text-sm text-center" role="alert" aria-live="polite">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-warm-black mb-1">
              New Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, password: true }))}
              autoComplete="new-password"
              aria-invalid={passwordError ? 'true' : 'false'}
              className="w-full px-4 py-3 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              placeholder="Enter new password"
            />
            {passwordError ? (
              <p className="mt-1 text-sm text-red-600">{passwordError}</p>
            ) : (
              <p className="mt-1 text-xs text-warm-muted">
                8+ characters, uppercase, lowercase, number, alphanumeric only
              </p>
            )}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-warm-black mb-1">
              Confirm New Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, confirmPassword: true }))}
              autoComplete="new-password"
              aria-invalid={confirmPasswordError ? 'true' : 'false'}
              className="w-full px-4 py-3 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              placeholder="Confirm new password"
            />
            {confirmPasswordError && (
              <p className="mt-1 text-sm text-red-600">{confirmPasswordError}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !!passwordError || !!confirmPasswordError}
            className="w-full bg-sage hover:bg-sage/80 text-white font-semibold py-4 px-8 rounded-full transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="flex items-center justify-center gap-2">
              {isSubmitting && <ButtonSpinner />}
              {isSubmitting ? 'Resetting...' : 'Reset Password'}
            </span>
          </button>
        </form>
      </div>
    </div>
  )
}

export default ResetPassword
