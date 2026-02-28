import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { practiceApi } from '../lib/api'
import { FeedbackCard } from '../components/FeedbackCard'
import { SessionSummary } from '../components/SessionSummary'
import type { WordContext, FeedbackData, PracticeSummaryResponse } from '../types/api'

interface Message {
  id: number
  sender: 'laoshi' | 'user'
  text: string
  timestamp: string
  feedback?: FeedbackData
}

const Practice = () => {
  const navigate = useNavigate()
  
  // Session state
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionPhase, setSessionPhase] = useState<'initializing' | 'practicing' | 'completed'>('initializing')
  
  // Word state
  const [currentWord, setCurrentWord] = useState<WordContext | null>(null)
  const [showPinyin, setShowPinyin] = useState(false)
  const [showTranslation, setShowTranslation] = useState(false)
  
  // Progress state
  const [wordsTotal, setWordsTotal] = useState(0)
  const [wordsPracticed, setWordsPracticed] = useState(0)
  const [wordsSkipped, setWordsSkipped] = useState(0)
  
  // Chat state
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isWaiting, setIsWaiting] = useState(false)
  
  // Sidebar state
  const [practicedWordsOpen, setPracticedWordsOpen] = useState(false)
  const [skippedWordsOpen, setSkippedWordsOpen] = useState(false)
  const [practicedWords, setPracticedWords] = useState<WordContext[]>([])
  const [skippedWords, setSkippedWords] = useState<WordContext[]>([])
  
  // Summary state
  const [summary, setSummary] = useState<PracticeSummaryResponse | null>(null)

  // Track if current word received feedback (reset on word advance)
  const [currentWordAttempted, setCurrentWordAttempted] = useState(false)
  
  // Error state
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initializedRef = useRef(false)

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Initialize session on mount
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    
    const initSession = async () => {
      setIsWaiting(true)
      try {
        const response = await practiceApi.startSession()
        const data = response.data
        
        setSessionId(data.session.id)
        setCurrentWord(data.current_word)
        setWordsTotal(data.words_total)
        setWordsPracticed(data.words_practiced)
        setWordsSkipped(data.words_skipped)
        
        // Add greeting message
        const greetingMessage: Message = {
          id: Date.now(),
          sender: 'laoshi',
          text: data.greeting_message,
          timestamp: getCurrentTime(),
        }
        setMessages([greetingMessage])
        setSessionPhase('practicing')
      } catch (err: any) {
        const errorMsg = err.response?.data?.error || 'Failed to start practice session'
        setError(errorMsg)
      } finally {
        setIsWaiting(false)
      }
    }
    
    initSession()
  }, [])

  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleSubmit = async () => {
    if (!inputText.trim() || !sessionId || !currentWord) return

    // Add user message
    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      text: inputText,
      timestamp: getCurrentTime(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInputText('')
    setIsWaiting(true)

    try {
      const response = await practiceApi.sendMessage(sessionId, userMessage.text)
      const data = response.data
      
      const laoshiMessage: Message = {
        id: Date.now() + 1,
        sender: 'laoshi',
        text: data.laoshi_response,
        timestamp: getCurrentTime(),
        feedback: data.feedback || undefined,
      }
      setMessages((prev) => [...prev, laoshiMessage])

      // Mark current word as attempted if feedback was returned
      if (data.feedback) {
        setCurrentWordAttempted(true)
      }

      // Update progress counts
      setWordsPracticed(data.words_practiced)
      setWordsSkipped(data.words_skipped)
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Failed to send message'
      const errorMessage: Message = {
        id: Date.now() + 1,
        sender: 'laoshi',
        text: `Sorry, I had trouble processing that. ${errorMsg}`,
        timestamp: getCurrentTime(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsWaiting(false)
    }
  }

  const handleNextWord = async () => {
    if (!sessionId || !currentWord) return

    setIsWaiting(true)

    try {
      const response = await practiceApi.nextWord(sessionId)
      const data = response.data

      // Update sidebar trays based on whether user attempted this word
      if (currentWordAttempted) {
        setPracticedWords(prev => [...prev, currentWord])
      } else {
        setSkippedWords(prev => [...prev, currentWord])
      }

      // Reset for next word
      setCurrentWordAttempted(false)
      
      // Update progress
      setWordsPracticed(data.words_practiced)
      setWordsSkipped(data.words_skipped)
      
      if (data.session_complete) {
        // Session complete
        setSessionPhase('completed')
        if (data.summary) {
          setSummary(data.summary)
        }
      } else if (data.current_word) {
        // Next word available
        setCurrentWord(data.current_word)
        const laoshiMessage: Message = {
          id: Date.now(),
          sender: 'laoshi',
          text: data.laoshi_response,
          timestamp: getCurrentTime(),
        }
        setMessages((prev) => [...prev, laoshiMessage])
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Failed to advance to next word'
      const errorMessage: Message = {
        id: Date.now(),
        sender: 'laoshi',
        text: `Sorry, I had trouble moving to the next word. ${errorMsg}`,
        timestamp: getCurrentTime(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsWaiting(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleNewSession = () => {
    // Reset and start new session
    initializedRef.current = false
    setSessionId(null)
    setSessionPhase('initializing')
    setCurrentWord(null)
    setWordsTotal(0)
    setWordsPracticed(0)
    setWordsSkipped(0)
    setMessages([])
    setPracticedWords([])
    setSkippedWords([])
    setSummary(null)
    setCurrentWordAttempted(false)
    setError(null)
    
    // Trigger re-initialization
    setTimeout(() => {
      const initSession = async () => {
        setIsWaiting(true)
        try {
          const response = await practiceApi.startSession()
          const data = response.data
          
          setSessionId(data.session.id)
          setCurrentWord(data.current_word)
          setWordsTotal(data.words_total)
          setWordsPracticed(data.words_practiced)
          setWordsSkipped(data.words_skipped)
          
          const greetingMessage: Message = {
            id: Date.now(),
            sender: 'laoshi',
            text: data.greeting_message,
            timestamp: getCurrentTime(),
          }
          setMessages([greetingMessage])
          setSessionPhase('practicing')
        } catch (err: any) {
          const errorMsg = err.response?.data?.error || 'Failed to start practice session'
          setError(errorMsg)
        } finally {
          setIsWaiting(false)
        }
      }
      initSession()
    }, 0)
  }

  // Show error state
  if (error) {
    return (
      <div className="flex h-screen bg-gray-50 items-center justify-center">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center">
          <div className="text-6xl mb-4">😅</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Oops!</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex flex-col gap-3">
            <button
              onClick={() => navigate('/vocabulary')}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
            >
              Go to Vocabulary
            </button>
            <Link
              to="/home"
              className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Show initializing state
  if (sessionPhase === 'initializing') {
    return (
      <div className="flex h-screen bg-gray-50 items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Starting your practice session...</p>
        </div>
      </div>
    )
  }

  // Show completed state
  if (sessionPhase === 'completed' && summary) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <SessionSummary summary={summary} onNewSession={handleNewSession} />
      </div>
    )
  }

  const progressPercent = wordsTotal > 0 
    ? ((wordsPracticed + wordsSkipped) / wordsTotal) * 100 
    : 0

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Word Card Panel */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Back to Home */}
        <div className="p-4 border-b border-gray-100">
          <Link
            to="/home"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            <span>Back to Home</span>
          </Link>
        </div>

        {/* Progress */}
        <div className="px-4 py-3">
          <p className="text-sm text-gray-600 mb-2">
            {wordsPracticed + wordsSkipped} / {wordsTotal} words ({wordsPracticed} practiced, {wordsSkipped} skipped)
          </p>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-pink-500 via-purple-500 to-blue-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Current Word Section */}
        <div className="px-4 py-3">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Current Word
            </h3>
            <div className="flex gap-1">
              <button
                onClick={() => setShowPinyin(!showPinyin)}
                className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-colors ${
                  showPinyin
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title="Toggle Pinyin"
              >
                拼
              </button>
              <button
                onClick={() => setShowTranslation(!showTranslation)}
                className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-colors ${
                  showTranslation
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title="Toggle Translation"
              >
                文
              </button>
            </div>
          </div>

          {/* Word Card */}
          <div className="bg-gradient-to-br from-pink-50 via-purple-50 to-blue-50 rounded-2xl p-6 text-center">
            {currentWord ? (
              <>
                <div className="text-6xl font-medium text-gray-900 mb-4">
                  {currentWord.word}
                </div>

                {showPinyin && (
                  <div className="text-lg text-gray-600 mb-2">{currentWord.pinyin}</div>
                )}

                {showTranslation && (
                  <div className="text-gray-500">{currentWord.meaning}</div>
                )}
              </>
            ) : (
              <div className="py-8 text-gray-400">No word available</div>
            )}
          </div>
        </div>

        {/* Practiced Words Tray */}
        <div className="px-4 py-2">
          <button
            onClick={() => setPracticedWordsOpen(!practicedWordsOpen)}
            className="flex items-center justify-between w-full py-2 text-sm font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
          >
            <span>Practiced Words ({practicedWords.length})</span>
            <svg
              className={`w-5 h-5 transition-transform ${practicedWordsOpen ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
          {practicedWordsOpen && (
            <div className="py-2 text-sm text-gray-500">
              {practicedWords.length > 0 ? (
                practicedWords.map((word, idx) => (
                  <div key={idx} className="py-1">{word.word}</div>
                ))
              ) : (
                <p className="text-gray-400 italic">No words practiced yet</p>
              )}
            </div>
          )}
        </div>

        {/* Skipped Words Tray */}
        <div className="px-4 py-2">
          <button
            onClick={() => setSkippedWordsOpen(!skippedWordsOpen)}
            className="flex items-center justify-between w-full py-2 text-sm font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
          >
            <span>Skipped Words ({skippedWords.length})</span>
            <svg
              className={`w-5 h-5 transition-transform ${skippedWordsOpen ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
          {skippedWordsOpen && (
            <div className="py-2 text-sm text-gray-500">
              {skippedWords.length > 0 ? (
                skippedWords.map((word, idx) => (
                  <div key={idx} className="py-1">{word.word}</div>
                ))
              ) : (
                <p className="text-gray-400 italic">No words skipped</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="/laoshi-logo.png"
              alt="Laoshi"
              className="w-12 h-12 rounded-full object-cover"
            />
            <div>
              <h2 className="font-semibold text-gray-900">Laoshi</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-sm text-green-600">Online</span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.sender === 'laoshi' && (
                <img
                  src="/laoshi-logo.png"
                  alt="Laoshi"
                  className="w-8 h-8 rounded-full object-cover mr-3 mt-1"
                />
              )}
              <div
                className={`max-w-lg ${
                  message.sender === 'user'
                    ? 'bg-purple-600 text-white rounded-2xl rounded-br-md'
                    : 'bg-white border border-gray-200 text-gray-800 rounded-2xl rounded-bl-md'
                } px-5 py-3 shadow-sm`}
              >
                <p className="text-base whitespace-pre-wrap">{message.text}</p>
                
                {/* Render FeedbackCard inside laoshi message if feedback exists */}
                {message.sender === 'laoshi' && message.feedback && (
                  <div className="mt-3">
                    <FeedbackCard feedback={message.feedback} />
                  </div>
                )}
                
                <p
                  className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-purple-200' : 'text-gray-400'
                  }`}
                >
                  {message.timestamp}
                </p>
              </div>
            </div>
          ))}
          
          {/* Typing indicator */}
          {isWaiting && (
            <div className="flex justify-start">
              <img
                src="/laoshi-logo.png"
                alt="Laoshi"
                className="w-8 h-8 rounded-full object-cover mr-3 mt-1"
              />
              <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-5 py-3 shadow-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="bg-gray-50 rounded-2xl border border-gray-200 p-4">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your sentence here..."
              disabled={isWaiting}
              className="w-full bg-transparent resize-none outline-none text-gray-800 placeholder-gray-400 min-h-[60px] disabled:opacity-50"
              rows={2}
            />
            <div className="flex items-center justify-between mt-2">
              <button
                onClick={handleNextWord}
                disabled={isWaiting}
                className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors disabled:opacity-50"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
                <span className="text-sm">Next Word</span>
              </button>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-400">{inputText.length} characters</span>
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || isWaiting}
                  className="flex items-center gap-2 bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 disabled:from-gray-300 disabled:to-gray-300 text-white px-6 py-2.5 rounded-full font-medium transition-all"
                >
                  <span>Submit</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Practice
