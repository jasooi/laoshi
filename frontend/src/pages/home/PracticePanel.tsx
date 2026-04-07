import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import { practiceApi } from '../../lib/api'
import type { PracticeSession, FeedbackData, WordContext } from '../../types/api'
import { useHome } from './HomeContext'
import { FeedbackCard } from '../../components/FeedbackCard'
import FloatingWordPill from './FloatingWordPill'
import ConfidenceRating from './ConfidenceRating'
import { Send, ChevronsRight, ChevronLeft, AlertTriangle } from 'lucide-react'
import { motion } from 'framer-motion'
import laoshiLogo from '../../assets/laoshi-logo.png'

const RATE_LIMIT_MESSAGE = "Laoshi needs a breather — the AI rate limit has been reached. You can add your own API key in Settings to avoid this."

function isRateLimitError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 429
}

type PracticeStatus =
  | 'ai_typing'
  | 'waiting_for_user'
  | 'feedback_given'
  | 'rating_typing'
  | 'awaiting_rating'
  | 'rating_selected'
  | 'transitioning'
  | 'session_complete'

interface ChatMessage {
  id: string
  role: 'laoshi' | 'user'
  content: string
  feedback?: FeedbackData | null
  isGrouped?: boolean
  ratingData?: {
    wordId: number
    wordText: string
    quality?: number
  }
}

// Chat message bubble
function ChatBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%]">
          <div className="bg-sage rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-[15px] text-white leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
          <p className="text-[10px] text-warm-black/30 mt-1 text-right">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-3 ${message.isGrouped ? 'mb-1.5' : 'mb-4'}`}>
      {message.isGrouped ? (
        <div className="w-7 flex-shrink-0" />
      ) : (
        <img
          src={laoshiLogo}
          alt="Laoshi"
          className="w-7 h-7 rounded-full flex-shrink-0 self-end mb-5"
        />
      )}
      <div className="max-w-[75%]">
        <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 border border-warm-gray/40 shadow-sm">
          <p className="text-[15px] text-warm-black leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
        {message.feedback && (
          <div className="mt-2">
            <FeedbackCard feedback={message.feedback} />
          </div>
        )}
        {!message.isGrouped && (
          <p className="text-[10px] text-warm-black/30 mt-1">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  )
}

export default function PracticePanel() {
  const { activeSessionData, endPractice, showSummary: showSummaryFn } = useHome()

  const [session, setSession] = useState<PracticeSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentWord, setCurrentWord] = useState<WordContext | null>(null)
  const [deckName, setDeckName] = useState(activeSessionData?.deckName || '')
  const [userInput, setUserInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<PracticeStatus>('ai_typing')
  const [sessionStats, setSessionStats] = useState({ words_practiced: 0, words_total: 0 })
  const [showEndModal, setShowEndModal] = useState(false)
  const [showDivider, setShowDivider] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const initializedRef = useRef(false)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status, showDivider])

  // Focus input when ready for input
  useEffect(() => {
    if ((status === 'waiting_for_user' || status === 'feedback_given') && inputRef.current) {
      inputRef.current.focus()
    }
  }, [status, currentWord])

  // Load session on mount
  useEffect(() => {
    if (activeSessionData?.sessionId && !initializedRef.current) {
      initializedRef.current = true
      loadSession(activeSessionData.sessionId)
    }
  }, [activeSessionData])

  const loadSession = async (id: number) => {
    try {
      const response = await practiceApi.getSession(id)
      const sessionData = response.data.session
      setSession(sessionData)
      setSessionStats({
        words_practiced: sessionData.words_practiced || 0,
        words_total: sessionData.words_total || 0,
      })

      if (!deckName && response.data.deck_name) {
        setDeckName(response.data.deck_name)
      }

      let greetingContent = ''
      // Use context data if available (fresh session start)
      if (activeSessionData?.greeting && activeSessionData?.currentWord) {
        setCurrentWord(activeSessionData.currentWord)
        greetingContent = activeSessionData.greeting
      } else if (response.data.current_word) {
        // Page refresh fallback
        const word = response.data.current_word
        setCurrentWord(word)
        greetingContent = `Let's practice with ${word.word} (${word.pinyin})! This word means "${word.meaning}". Try making a sentence using it.`
      }

      setLoading(false)

      if (greetingContent) {
        setStatus('ai_typing')
        await addLaoshiMessages(greetingContent)
      }
      setStatus('waiting_for_user')
    } catch (error) {
      console.error('Failed to load session:', error)
      setLoading(false)
    }
  }

  const addMessage = (role: 'laoshi' | 'user', content: string, feedback?: FeedbackData | null) => {
    setMessages(prev => [...prev, {
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      role,
      content,
      feedback,
    }])
  }

  const addLaoshiMessages = async (content: string, feedback?: FeedbackData | null): Promise<void> => {
    const parts = content.split(/\n\n+/).filter(p => p.trim())
    if (parts.length === 0) return

    for (let i = 0; i < parts.length; i++) {
      if (i > 0) {
        setStatus('ai_typing')
        await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 400))
      }

      const isLast = i === parts.length - 1
      setMessages(prev => [...prev, {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role: 'laoshi',
        content: parts[i],
        feedback: isLast ? feedback : undefined,
        isGrouped: !isLast,
      }])
    }
  }

  const handleSubmit = async () => {
    if (!session || !userInput.trim() || (status !== 'waiting_for_user' && status !== 'feedback_given')) return

    const sentence = userInput.trim()
    setUserInput('')
    addMessage('user', sentence)
    setStatus('ai_typing')

    try {
      const response = await practiceApi.sendMessage(session.id, sentence)
      const data = response.data

      await addLaoshiMessages(data.laoshi_response, data.feedback)
      setSessionStats({
        words_practiced: data.words_practiced,
        words_total: data.words_total,
      })

      if (data.session_complete) {
        const summaryResponse = await practiceApi.getSummary(session.id)
        showSummaryFn(summaryResponse.data)
      } else {
        setStatus('feedback_given')
      }
    } catch (error) {
      console.error('Failed to submit:', error)
      addMessage('laoshi', isRateLimitError(error) ? RATE_LIMIT_MESSAGE : 'Sorry, something went wrong. Please try again.')
      setStatus('waiting_for_user')
    }
  }

  const handleNextWord = () => {
    setStatus('rating_typing')
    setTimeout(() => {
      // Add rating prompt as a message
      const ratingMsgId = `rating-${Date.now()}`
      setMessages(prev => [...prev, {
        id: ratingMsgId,
        role: 'laoshi',
        content: '',
        ratingData: {
          wordId: currentWord!.word_id,
          wordText: currentWord!.word,
          quality: undefined,
        },
      }])
      setStatus('awaiting_rating')
    }, 800)
  }

  const handleRate = async (messageId: string, wordId: number, quality: number, isEdit: boolean) => {
    // Update the rating in the message
    setMessages(prev => prev.map(m =>
      m.id === messageId
        ? { ...m, ratingData: { ...m.ratingData!, quality } }
        : m
    ))

    if (isEdit) {
      // Retroactive edit: call rerate API
      try {
        await practiceApi.rerateWord(wordId, session!.id, quality)
      } catch (error) {
        console.error('Failed to rerate word:', error)
      }
    } else {
      // First-time rating: advance to next word
      setStatus('rating_selected')
      if (!session) return

      try {
        const response = await practiceApi.nextWord(session.id, quality)
        const data = response.data

        setSessionStats({
          words_practiced: data.words_practiced,
          words_total: data.words_total,
        })

        if (data.session_complete) {
          if (data.summary) {
            showSummaryFn(data.summary)
          } else {
            const summaryResponse = await practiceApi.getSummary(session.id)
            showSummaryFn(summaryResponse.data)
          }
        } else {
          setTimeout(() => {
            setShowDivider(true)
            setStatus('transitioning')
            setTimeout(async () => {
              setShowDivider(false)
              if (data.current_word) setCurrentWord(data.current_word)
              if (data.laoshi_response) {
                setStatus('ai_typing')
                await addLaoshiMessages(data.laoshi_response)
              }
              setStatus('waiting_for_user')
              setUserInput('')
            }, 600)
          }, 500)
        }
      } catch (error) {
        console.error('Failed to get next word:', error)
        if (isRateLimitError(error)) {
          addMessage('laoshi', RATE_LIMIT_MESSAGE)
        }
        setStatus('feedback_given')
      }
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
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-chat-bg">
        <div className="animate-pulse text-warm-muted">Loading practice session...</div>
      </div>
    )
  }

  // No word available
  if (!currentWord) {
    return (
      <div className="h-full flex items-center justify-center bg-chat-bg">
        <div className="text-center">
          <p className="text-warm-muted mb-4">No words available for practice</p>
          <button
            onClick={() => endPractice()}
            className="text-sage hover:text-sage/80"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  const progressPercent = sessionStats.words_total > 0
    ? (sessionStats.words_practiced / sessionStats.words_total) * 100
    : 0

  const isInputLocked = ['rating_typing', 'awaiting_rating', 'rating_selected', 'transitioning', 'session_complete'].includes(status)
  const isSessionComplete = status === 'session_complete'

  // Find the last rating message ID for isLatest check
  const ratingMessages = messages.filter(m => m.ratingData)
  const lastRatingMsgId = ratingMessages.length > 0 ? ratingMessages[ratingMessages.length - 1].id : undefined

  return (
    <div className="h-full flex flex-col bg-chat-bg">
      {/* Progress bar */}
      <div className="h-[3px] bg-warm-gray/30 flex-shrink-0">
        <div
          className="h-full bg-sage transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Chat header */}
      <div className="h-14 bg-white/90 backdrop-blur-sm border-b border-warm-gray/50 flex items-center flex-shrink-0">
        <div className="max-w-3xl w-full mx-auto px-6 flex items-center justify-between">
          {/* Left side */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowEndModal(true)}
              className="text-warm-black/50 hover:text-warm-black transition-colors"
            >
              <ChevronLeft className="w-[18px] h-[18px]" />
            </button>
            <div className="w-8 h-8 rounded-full bg-warm-offwhite border border-warm-gray/50 flex items-center justify-center">
              <img src={laoshiLogo} alt="Laoshi" className="w-6 h-6 object-contain" />
            </div>
            <div>
              <p className="text-sm font-medium text-warm-black leading-tight">Laoshi</p>
              <div className="flex items-center gap-1">
                {status === 'ai_typing' || status === 'rating_typing' ? (
                  <span className="text-[10px] text-warm-black/50 font-medium">typing...</span>
                ) : (
                  <>
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                    <span className="text-[10px] text-green-600 font-medium">Online</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right side */}
          <div className="text-right">
            <p className="text-[11px] text-warm-black/50 font-medium">{deckName}</p>
            <p className="text-[10px] text-warm-black/30">
              {sessionStats.words_practiced} / {sessionStats.words_total}
            </p>
          </div>
        </div>
      </div>

      {/* Chat area (scrollable) */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6">
          {/* Floating word pill */}
          {currentWord && <FloatingWordPill word={currentWord} />}

          {/* Messages */}
          {messages.map((msg) => (
            msg.ratingData ? (
              <ConfidenceRating
                key={msg.id}
                messageId={msg.id}
                wordId={msg.ratingData.wordId}
                wordText={msg.ratingData.wordText}
                quality={msg.ratingData.quality}
                isLatest={msg.id === lastRatingMsgId && status !== 'waiting_for_user'}
                onRate={handleRate}
              />
            ) : (
              <ChatBubble key={msg.id} message={msg} />
            )
          ))}

          {/* Typing indicator */}
          {(status === 'ai_typing' || status === 'rating_typing') && (
            <div className="flex gap-3 mb-4">
              <img
                src={laoshiLogo}
                alt="Laoshi"
                className="w-7 h-7 rounded-full flex-shrink-0 self-end mb-5"
              />
              <div className="max-w-[75%]">
                <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 border border-warm-gray/40 shadow-sm">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-warm-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-warm-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-warm-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Word divider */}
          {showDivider && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="flex items-center gap-4 my-6"
            >
              <div className="flex-1 h-px bg-warm-gray/50" />
              <span className="text-[11px] text-warm-black/25 font-medium tracking-wide uppercase">
                next word
              </span>
              <div className="flex-1 h-px bg-warm-gray/50" />
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="bg-white border-t border-warm-gray/50 px-6 py-4 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          {isSessionComplete ? (
            <div className="flex justify-center">
              <motion.button
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => {
                  if (session) {
                    practiceApi.getSummary(session.id).then(res => showSummaryFn(res.data))
                  }
                }}
                className="flex items-center gap-2 bg-sage hover:bg-sage/90 text-white font-medium px-8 py-3.5 rounded-xl shadow-sm transition-colors"
              >
                View Session Summary
              </motion.button>
            </div>
          ) : isInputLocked ? (
            <div className="bg-warm-offwhite/60 border border-warm-gray/50 rounded-2xl py-5 flex items-center justify-center opacity-60">
              <p className="text-sm text-warm-black/40">Rate your confidence to continue</p>
            </div>
          ) : (
            <div className="border border-warm-gray rounded-2xl focus-within:border-sage focus-within:ring-1 focus-within:ring-sage overflow-hidden transition-colors">
              <textarea
                ref={inputRef}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
                placeholder="Type your sentence here..."
                className="w-full px-4 pt-4 pb-2 bg-warm-offwhite resize-none text-[15px] text-warm-black placeholder:text-warm-black/30 focus:outline-none min-h-[80px]"
                disabled={status !== 'waiting_for_user' && status !== 'feedback_given'}
                style={{ opacity: (status !== 'waiting_for_user' && status !== 'feedback_given') ? 0.5 : 1 }}
              />
              <div className="bg-white border-t border-warm-gray/50 px-4 py-2.5 flex items-center justify-between">
                <button
                  onClick={handleNextWord}
                  disabled={status !== 'feedback_given'}
                  className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
                    status === 'feedback_given'
                      ? 'text-warm-black/50 hover:text-warm-black'
                      : 'text-warm-black/30 cursor-not-allowed'
                  }`}
                >
                  <ChevronsRight className="w-4 h-4" />
                  Next Word
                </button>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-warm-black/40">
                    {userInput.length} characters
                  </span>
                  <button
                    onClick={handleSubmit}
                    disabled={!userInput.trim() || (status !== 'waiting_for_user' && status !== 'feedback_given')}
                    className={`flex items-center gap-1.5 px-6 py-2 rounded-full text-sm font-medium transition-colors disabled:opacity-50 ${userInput.trim() ? 'bg-sage text-white hover:bg-sage-dark' : 'bg-warm-gray/50 text-warm-black/50 hover:bg-sage hover:text-white'}`}
                  >
                    Submit
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* End Session Modal */}
      {showEndModal && (
        <div className="fixed inset-0 z-[60] bg-warm-black/20 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            className="bg-white rounded-2xl shadow-xl max-w-md w-full p-8"
          >
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-yellow-600" />
              </div>
              <h3 className="text-xl font-medium text-warm-black">End Current Session?</h3>
            </div>
            <p className="text-base text-warm-black/60 leading-relaxed mb-8">
              You have an active practice session. Ending it will save your progress so far. Are you sure you want to continue?
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={() => setShowEndModal(false)}
                className="px-6 py-2.5 text-warm-black/60 hover:text-warm-black font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowEndModal(false); handleEndSession() }}
                className="px-6 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl shadow-sm font-medium transition-colors"
              >
                End Session
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
