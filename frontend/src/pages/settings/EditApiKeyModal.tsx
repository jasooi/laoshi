import { useState } from 'react'
import { settingsApi } from '../../lib/api'
import ButtonSpinner from '../../components/ButtonSpinner'

interface EditApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
  provider: 'deepseek' | 'gemini'
  currentKey: string | null
  onKeySaved: (key: string | null) => void
  onValidationError: (error: string) => void
}

const providerLabels: Record<string, string> = {
  deepseek: 'DeepSeek',
  gemini: 'Gemini',
}

const providerDescriptions: Record<string, string> = {
  deepseek: 'Used for conversation and feedback generation',
  gemini: 'Used for sentence evaluation and scoring',
}

export default function EditApiKeyModal({
  isOpen,
  onClose,
  provider,
  currentKey,
  onKeySaved,
}: EditApiKeyModalProps) {
  const [apiKey, setApiKey] = useState(currentKey || '')
  const [isLoading, setIsLoading] = useState(false)
  const [inlineError, setInlineError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setInlineError(null)

    // If clearing the key, save directly without validation
    if (!apiKey.trim()) {
      setIsLoading(true)
      try {
        await settingsApi.updateSettings({
          [`${provider}_api_key`]: null,
        } as Partial<{
          deepseek_api_key: string | null
          gemini_api_key: string | null
        }>)
        onKeySaved(null)
        onClose()
      } catch (err) {
        setInlineError('Failed to clear API key. Please try again.')
      } finally {
        setIsLoading(false)
      }
      return
    }

    // Validate the key before saving
    setIsLoading(true)
    try {
      const validationResponse = await settingsApi.validateKey(provider, apiKey.trim())

      if (!validationResponse.data.valid) {
        // Validation failed - stay open with inline error
        setInlineError(validationResponse.data.error || 'Invalid API key')
        setIsLoading(false)
        return
      }

      // Validation passed - save the key
      await settingsApi.updateSettings({
        [`${provider}_api_key`]: apiKey.trim(),
      } as Partial<{
        deepseek_api_key: string | null
        gemini_api_key: string | null
      }>)
      onKeySaved(apiKey.trim())
      onClose()
    } catch (err) {
      // Network or server error - stay open with inline error
      setInlineError('Failed to validate API key. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    if (isLoading) return // Prevent closing while loading
    setInlineError(null)
    setApiKey(currentKey || '')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-warm-black">
            Edit {providerLabels[provider]} API Key
          </h2>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-warm-muted hover:text-warm-black disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Description */}
        <p className="text-sm text-warm-muted mb-4">{providerDescriptions[provider]}</p>

        {/* Inline Error */}
        {inlineError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-red-700">{inlineError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="apiKey" className="block text-sm font-medium text-warm-black mb-1">
              API Key
            </label>
            <input
              type="password"
              id="apiKey"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              disabled={isLoading}
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent disabled:bg-warm-offwhite disabled:cursor-not-allowed"
            />
            <p className="mt-1 text-xs text-warm-muted">
              Leave empty to clear the current key
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-warm-gray text-warm-black rounded-lg hover:bg-warm-offwhite font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/80 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading && <ButtonSpinner />}
              {isLoading ? 'Validating...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
