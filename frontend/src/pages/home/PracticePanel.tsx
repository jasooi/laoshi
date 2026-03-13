import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { practiceApi } from '../../lib/api'
import type { PracticeSession, PracticeResponse, PracticeSummaryResponse } from '../../types/api'
import { useHome } from './HomeContext'
import { Send, X, CheckCircle, Check, X as XIcon } from 'lucide-react'

// Quality rating modal
function QualityRatingModal({
  isOpen,
  onRate,
  onClose,
}: {
  isOpen: boolean
  onRate: (quality: number) => void
  onClose: () => void
}) {
  if (!isOpen) return null

  const ratings = [
    { value: 0, label: 'Blackout', emoji: '😵', desc: 'Complete blackout' },
    { value: 1, label: 'Wrong', emoji: '😞', desc: 'Incorrect response' },
    { value: 2, label: 'Hard', emoji: '😕', desc: 'Correct but difficult' },
    { value: 3, label: 'OK', emoji: '😐', desc: 'Correct with hesitation' },
    { value: 4, label: 'Good', emoji: '🙂', desc: 'Correct response' },
    { value: 5, label: 'Easy', emoji: '🤩', desc: 'Perfect response' },
  ]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-stone-800">How did you do?</h3>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-stone-500 text-sm mb-4">
          Rate your recall quality to optimize your review schedule
        </p>
        <div className="space-y-2">
          {ratings.map((rating) => (
            <button
              key={rating.value}
              onClick={() => onRate(rating.value)}
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-stone-200 hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
            >
              <span className="text-2xl">{rating.emoji}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-stone-800">{rating.label}</span>
                  <span className="text-xs text-stone-400">({rating.value})</span>
                </div>
                <p className="text-xs text-stone-500">{rating.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function PracticePanel() {
  const { deckId, sessionId } = useParams<{ deckId: string; sessionId: string }>()
  const [session, setSession] = useState<PracticeSession | null>(null)
  const [currentWord, setCurrentWord] = useState<PracticeResponse | null>(null)
  const [userSentence, setUserSentence] = useState('')
  const [feedback, setFeedback] = useState<PracticeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showQualityModal, setShowQualityModal] = useState(false)
  const [showSummary, setShowSummary] = useState(false)
  const [summary, setSummary] = useState<PracticeSummaryResponse | null>(null)
  const [sessionStats, setSessionStats] = useState({ words_practiced: 0, words_total: 0 })
  const { endPractice } = useHome()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (sessionId) {
      loadSession(parseInt(sessionId))
    }
  }, [sessionId])

  useEffect(() => {
    if (inputRef.current && !feedback) {
      inputRef.current.focus()
    }
  }, [feedback, currentWord])

  const loadSession = async (id: number) => {
    try {
      const response = await practiceApi.getSession(id)
      setSession(response.data.session)
      setSessionStats({
        words_practiced: response.data.session.words_practiced || 0,
        words_total: response.data.session.words_total || 0,
      })

      // Get first word
      const wordResponse = await practiceApi.nextWord(id)
      setCurrentWord(wordResponse.data)
    } catch (error) {
      console.error('Failed to load session:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!session || !userSentence.trim()) return

    setSubmitting(true)
    try {
      const response = await practiceApi.submitSentence(session.id, userSentence)
      setFeedback(response.data)
      setSessionStats({
        words_practiced: response.data.words_practiced || 0,
        words_total: response.data.words_total || 0,
      })
    } catch (error) {
      console.error('Failed to submit:', error)
      alert('Failed to submit sentence. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleNextWord = () => {
    setShowQualityModal(true)
  }

  const handleQualityRate = async (quality: number) => {
    setShowQualityModal(false)

    if (!session) return

    try {
      const response = await practiceApi.nextWord(session.id, quality)

      if (response.data.is_session_complete) {
        // Session complete - fetch summary
        const summaryResponse = await practiceApi.getSummary(session.id)
        setSummary(summaryResponse.data)
        setShowSummary(true)
      } else {
        // Next word
        setCurrentWord(response.data)
        setFeedback(null)
        setUserSentence('')
        setSessionStats({
          words_practiced: response.data.words_practiced || 0,
          words_total: response.data.words_total || 0,
        })
      }
    } catch (error) {
      console.error('Failed to get next word:', error)
    }
  }

  const handleEndSession = async () => {
    if (!session) return

    try {
      await practiceApi.endSession(session.id)
    } catch (error) {
      console.error('Failed to end session:', error)
    } finally {
      endPractice()
      navigate(`/home/deck/${deckId}`)
    }
  }

  const handleSummaryClose = () => {
    endPractice()
    navigate(`/home/deck/${deckId}`)
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-stone-400">Loading practice...</div>
      </div>
    )
  }

  if (!currentWord && !showSummary) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-stone-500 mb-4">No words available for practice</p>
          <button
            onClick={() => navigate(`/home/deck/${deckId}`)}
            className="text-primary-600 hover:text-primary-700"
          >
            Back to Deck
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-stone-50">
      {/* Header with progress */}
      <div className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-stone-800">Practice Session</h2>
          <button
            onClick={handleEndSession}
            className="text-stone-500 hover:text-stone-700 text-sm"
          >
            End Session
          </button>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 transition-all"
                style={{
                  width: `${
                    sessionStats.words_total > 0
                      ? (sessionStats.words_practiced / sessionStats.words_total) * 100
                      : 0
                  }%`,
                }}
              />
            </div>
          </div>
          <span className="text-sm text-stone-500 whitespace-nowrap">
            {sessionStats.words_practiced}/{sessionStats.words_total} words
          </span>
        </div>
      </div>

      {/* Practice content */}
      <div className="flex-1 overflow-y-auto p-6">
        {showSummary && summary ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-stone-800 mb-2">Session Complete!</h2>
              <p className="text-stone-600">
                {summary.words_practiced} words practiced, {summary.words_skipped} skipped
              </p>
            </div>
            <div className="bg-primary-50 rounded-xl p-6 border border-primary-100 mb-6">
              <p className="text-primary-900 leading-relaxed text-lg">{summary.summary_text}</p>
            </div>
            <div className="flex justify-center">
              <button
                onClick={handleSummaryClose}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
              >
                Back to Deck
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Target word */}
            <div className="bg-white rounded-xl shadow-sm border border-stone-200 p-6 text-center">
              <p className="text-sm text-stone-500 mb-2">Target Word</p>
              <h2 className="text-4xl font-bold text-stone-800 mb-2">
                {currentWord?.target_word}
              </h2>
              <p className="text-lg text-stone-600">
                {currentWord?.target_pinyin}
              </p>
              <p className="text-stone-500 mt-2">{currentWord?.target_english}</p>
            </div>

            {/* Input area */}
            {!feedback ? (
              <div className="bg-white rounded-xl shadow-sm border border-stone-200 p-6">
                <label className="block text-sm font-medium text-stone-700 mb-2">
                  Create a sentence using this word:
                </label>
                <textarea
                  ref={inputRef}
                  value={userSentence}
                  onChange={(e) => setUserSentence(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit()
                    }
                  }}
                  placeholder="Type your sentence in Chinese..."
                  className="w-full px-4 py-3 border border-stone-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  rows={3}
                  disabled={submitting}
                />
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={handleSubmit}
                    disabled={!userSentence.trim() || submitting}
                    className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-stone-300 disabled:cursor-not-allowed transition-colors"
                  >
                    <Send className="w-4 h-4" />
                    {submitting ? 'Checking...' : 'Submit'}
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Feedback */}
                <div className="bg-white rounded-xl shadow-sm border border-stone-200 p-6 space-y-4">
                  <div className="flex items-center gap-2">
                    {feedback.is_correct ? (
                      <>
                        <Check className="w-6 h-6 text-green-600" />
                        <span className="text-green-700 font-medium">Correct! Well done.</span>
                      </>
                    ) : (
                      <>
                        <XIcon className="w-6 h-6 text-amber-600" />
                        <span className="text-amber-700 font-medium">Needs improvement</span>
                      </>
                    )}
                  </div>
                  <div className="space-y-2">
                    <p className="text-stone-600"><strong>Your sentence:</strong> {feedback.user_sentence}</p>
                    {feedback.corrected_sentence && feedback.corrected_sentence !== feedback.user_sentence && (
                      <p className="text-stone-600"><strong>Corrected:</strong> {feedback.corrected_sentence}</p>
                    )}
                    <p className="text-stone-600">{feedback.explanation}</p>
                  </div>
                </div>

                {/* Next word button */}
                <div className="flex justify-center">
                  <button
                    onClick={handleNextWord}
                    className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                  >
                    <CheckCircle className="w-5 h-5" />
                    Next Word
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Quality rating modal */}
      <QualityRatingModal
        isOpen={showQualityModal}
        onRate={handleQualityRate}
        onClose={() => setShowQualityModal(false)}
      />
    </div>
  )
}
