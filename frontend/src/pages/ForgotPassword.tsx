import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { passwordResetApi } from '../lib/api'
import ButtonSpinner from '../components/ButtonSpinner'

const ForgotPassword = () => {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [emailSent, setEmailSent] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const response = await passwordResetApi.requestReset(email.trim())

      if (!response.data.registered) {
        setError('This email is not registered')
        setIsSubmitting(false)
        return
      }

      setEmailSent(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (emailSent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
        <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-sage/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-warm-black mb-3">Check your email</h1>
          <p className="text-warm-muted mb-8">
            The password reset email has been sent to your email address. Please check your inbox and follow the link to reset your password.
          </p>
          <Link
            to="/login"
            className="inline-block bg-sage hover:bg-sage/80 text-white font-semibold py-3 px-8 rounded-full transition-colors shadow-md"
          >
            Back to Login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full">
        <h1 className="text-2xl font-bold text-warm-black mb-2 text-center">
          Forgot password?
        </h1>
        <p className="text-warm-muted mb-8 text-center">
          Enter your registered email and we'll send you a link to reset your password.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="text-red-600 text-sm text-center" role="alert" aria-live="polite">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-warm-black mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full px-4 py-3 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              placeholder="Enter your email address"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-sage hover:bg-sage/80 text-white font-semibold py-4 px-8 rounded-full transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="flex items-center justify-center gap-2">
              {isSubmitting && <ButtonSpinner />}
              {isSubmitting ? 'Sending...' : 'Next'}
            </span>
          </button>
        </form>

        <p className="text-center mt-6 text-warm-muted">
          <Link to="/login" className="text-sage hover:text-sage/80 font-medium">
            Back to Login
          </Link>
        </p>
      </div>
    </div>
  )
}

export default ForgotPassword
