import { useState, useEffect } from 'react'
import { settingsApi } from '../lib/api'
import type { UserSettings } from '../types/api'
import { Info } from 'lucide-react'
import EditApiKeyModal from './settings/EditApiKeyModal'

const Settings = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // Modal states
  const [activeModal, setActiveModal] = useState<'deepseek' | 'gemini' | null>(null)
  // Form states
  const [preferredName, setPreferredName] = useState('')
  const [wordsPerSession, setWordsPerSession] = useState<number>(5)

  // Fetch settings on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await settingsApi.getSettings()
        setSettings(response.data)
        setPreferredName(response.data.preferred_name || '')
        setWordsPerSession(response.data.words_per_session || 5)
      } catch (err) {
        setError('Failed to load settings')
      } finally {
        setIsLoading(false)
      }
    }

    fetchSettings()
  }, [])

  // Clear save message after 3 seconds
  useEffect(() => {
    if (saveMessage) {
      const timer = setTimeout(() => setSaveMessage(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [saveMessage])

  const handleSaveProfile = async () => {
    try {
      const response = await settingsApi.updateSettings({
        preferred_name: preferredName || null,
        words_per_session: wordsPerSession,
      })
      setSettings(response.data)
      setSaveMessage('Profile settings saved successfully')
    } catch (err) {
      setError('Failed to save profile settings')
    }
  }

  const handleKeySaved = (provider: 'deepseek' | 'gemini', key: string | null) => {
    setSettings((prev) =>
      prev
        ? {
            ...prev,
            [`${provider}_api_key`]: key,
          }
        : null
    )
    setSaveMessage(`${provider === 'deepseek' ? 'DeepSeek' : 'Gemini'} API key saved successfully`)
  }

  const handleValidationError = (errorMsg: string) => {
    // This is called when modal closes after validation failure
    // Show error banner at page level
    setError(`Error saving key: ${errorMsg}`)
    // Clear error after 5 seconds
    setTimeout(() => setError(null), 5000)
  }

  const maskApiKey = (key: string | null): string => {
    if (!key) return 'Not configured'
    if (key.length <= 8) return '••••••••'
    return key.slice(0, 4) + '••••••••••••••••' + key.slice(-4)
  }

  if (isLoading) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sage"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <svg className="w-8 h-8 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <h1 className="text-2xl font-bold text-warm-black">Settings</h1>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-red-700">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Success Message */}
      {saveMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl flex items-start gap-3">
          <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-green-700">{saveMessage}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Profile Settings */}
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-sage-tint flex items-center justify-center">
              <svg className="w-5 h-5 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-warm-black">Profile</h2>
          </div>

          <div className="space-y-6">
            <div>
              <label htmlFor="preferredName" className="block text-sm font-medium text-warm-black mb-2">
                Preferred Name
              </label>
              <input
                type="text"
                id="preferredName"
                value={preferredName}
                onChange={(e) => setPreferredName(e.target.value)}
                placeholder="How should we address you?"
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="wordsPerSession" className="block text-sm font-medium text-warm-black mb-2">
                Words per Session
              </label>
              <select
                id="wordsPerSession"
                value={wordsPerSession}
                onChange={(e) => setWordsPerSession(Number(e.target.value))}
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-sage focus:border-transparent"
              >
                <option value={3}>3 words</option>
                <option value={5}>5 words</option>
                <option value={10}>10 words</option>
                <option value={15}>15 words</option>
                <option value={20}>20 words</option>
              </select>
            </div>

            <button
              onClick={handleSaveProfile}
              className="w-full mt-2 px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/80 font-medium transition-colors"
            >
              Save Profile Settings
            </button>
          </div>
        </div>

        {/* API Keys */}
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-warm-black">API Keys</h2>
          </div>

          <div className="space-y-6">
            {/* DeepSeek Key */}
            <div className="border border-warm-gray rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <h3 className="font-medium text-warm-black">DeepSeek</h3>
                    <div className="relative group">
                      <Info className="w-4 h-4 text-warm-muted group-hover:text-warm-black transition-colors cursor-help" />
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full hidden group-hover:block z-10 pb-2">
                        <div className="bg-warm-black text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
                          Get a DeepSeek API key:{' '}
                          <a href="https://developer.puter.com/tutorials/how-to-get-deepseek-api-key/" target="_blank" rel="noopener noreferrer" className="text-sage-tint underline">
                            Follow this guide
                          </a>
                          <div className="absolute left-1/2 -translate-x-1/2 top-full -mt-2 w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-warm-black" />
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-warm-muted">Conversation and feedback generation</p>
                </div>
                <button
                  onClick={() => setActiveModal('deepseek')}
                  className="px-3 py-1.5 text-sm font-medium text-sage hover:text-sage/80 hover:bg-sage-tint rounded-lg transition-colors"
                >
                  Edit
                </button>
              </div>
              <div className="text-sm font-mono text-warm-muted bg-warm-offwhite px-3 py-2 rounded-lg">
                {maskApiKey(settings?.deepseek_api_key || null)}
              </div>
            </div>

            {/* Gemini Key */}
            <div className="border border-warm-gray rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <h3 className="font-medium text-warm-black">Gemini</h3>
                    <div className="relative group">
                      <Info className="w-4 h-4 text-warm-muted group-hover:text-warm-black transition-colors cursor-help" />
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full hidden group-hover:block z-10 pb-2">
                        <div className="bg-warm-black text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
                          Get a Gemini API key:{' '}
                          <a href="https://ai.google.dev/gemini-api/docs/api-key" target="_blank" rel="noopener noreferrer" className="text-sage-tint underline">
                            Follow this guide
                          </a>
                          <div className="absolute left-1/2 -translate-x-1/2 top-full -mt-2 w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-warm-black" />
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-warm-muted">Sentence evaluation and scoring</p>
                </div>
                <button
                  onClick={() => setActiveModal('gemini')}
                  className="px-3 py-1.5 text-sm font-medium text-sage hover:text-sage/80 hover:bg-sage-tint rounded-lg transition-colors"
                >
                  Edit
                </button>
              </div>
              <div className="text-sm font-mono text-warm-muted bg-warm-offwhite px-3 py-2 rounded-lg">
                {maskApiKey(settings?.gemini_api_key || null)}
              </div>
            </div>

            <p className="text-xs text-warm-muted">
              Your API keys are encrypted and stored securely. They are only used for your practice sessions.
            </p>
          </div>
        </div>
      </div>

      {/* Modals */}
      <EditApiKeyModal
        isOpen={activeModal === 'deepseek'}
        onClose={() => setActiveModal(null)}
        provider="deepseek"
        currentKey={settings?.deepseek_api_key || null}
        onKeySaved={(key) => handleKeySaved('deepseek', key)}
        onValidationError={handleValidationError}
      />

      <EditApiKeyModal
        isOpen={activeModal === 'gemini'}
        onClose={() => setActiveModal(null)}
        provider="gemini"
        currentKey={settings?.gemini_api_key || null}
        onKeySaved={(key) => handleKeySaved('gemini', key)}
        onValidationError={handleValidationError}
      />
    </div>
  )
}

export default Settings

