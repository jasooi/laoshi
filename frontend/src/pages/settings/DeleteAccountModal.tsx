import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { accountApi } from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import ButtonSpinner from '../../components/ButtonSpinner'

interface DeleteAccountModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function DeleteAccountModal({ isOpen, onClose }: DeleteAccountModalProps) {
  const [password, setPassword] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { logout } = useAuth()
  const navigate = useNavigate()

  if (!isOpen) return null

  const handleDelete = async () => {
    if (!password.trim()) {
      setError('Please enter your password to confirm')
      return
    }

    setError(null)
    setIsDeleting(true)

    try {
      await accountApi.deleteAccount(password)
      await logout()
      navigate('/login', { replace: true })
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to delete account. Please try again.'
      setError(message)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleClose = () => {
    if (isDeleting) return
    setPassword('')
    setError(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-warm-black">Delete Account</h2>
        </div>

        {/* Warning */}
        <p className="text-warm-muted mb-6">
          All progress and user data will be deleted. Are you sure you want to proceed to delete your account?
        </p>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Password confirmation */}
        <div className="mb-6">
          <label htmlFor="deletePassword" className="block text-sm font-medium text-warm-black mb-1">
            Enter your password to confirm
          </label>
          <input
            type="password"
            id="deletePassword"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isDeleting}
            autoComplete="current-password"
            className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent disabled:bg-warm-offwhite disabled:cursor-not-allowed"
            placeholder="Enter your password"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={isDeleting}
            className="flex-1 px-4 py-2 border border-warm-gray text-warm-black rounded-lg hover:bg-warm-offwhite font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting || !password.trim()}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isDeleting && <ButtonSpinner />}
            {isDeleting ? 'Deleting...' : 'Delete Account'}
          </button>
        </div>
      </div>
    </div>
  )
}
