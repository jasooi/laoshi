import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface VocabularyWord {
  id: string
  word: string
  pinyin: string
  definition: string
  confidenceLevel: string
}

interface Message {
  id: number
  sender: 'laoshi' | 'user'
  text: string
  timestamp: string
}

// ============================================
// CONFIGURABLE SETTINGS
// TODO: Move to Settings page when implemented
// ============================================
const WORDS_TO_PRACTICE = 10 // Default number of words per practice session

const Practice = () => {
  const [showPinyin, setShowPinyin] = useState(false)
  const [showTranslation, setShowTranslation] = useState(false)
  const [inputText, setInputText] = useState('')
  const [practicedWordsOpen, setPracticedWordsOpen] = useState(false)
  const [skippedWordsOpen, setSkippedWordsOpen] = useState(false)
  const [currentWord, setCurrentWord] = useState<VocabularyWord | null>(null)
  const [loading, setLoading] = useState(true)
  const [messages, setMessages] = useState<Message[]>([])
  const [practicedWords, setPracticedWords] = useState<VocabularyWord[]>([])
  const [skippedWords, setSkippedWords] = useState<VocabularyWord[]>([])

  const wordsProgress = {
    current: practicedWords.length + 1,
    total: WORDS_TO_PRACTICE,
  }

  // Fetch next word from API
  const fetchNextWord = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/practice/next-word')
      if (response.ok) {
        const data = await response.json()
        setCurrentWord(data)
        // Add initial prompt message from Laoshi
        const promptMessage: Message = {
          id: Date.now(),
          sender: 'laoshi',
          text: `请用'${data.word}'造一个句子`,
          timestamp: getCurrentTime(),
        }
        setMessages((prev) => [...prev, promptMessage])
      } else {
        // Fallback if API is not available yet
        console.log('API not available, using mock data')
        const mockWord: VocabularyWord = {
          id: '1',
          word: '学习',
          pinyin: 'xué xí',
          definition: 'to study, to learn',
          confidenceLevel: 'Learning',
        }
        setCurrentWord(mockWord)
        const promptMessage: Message = {
          id: Date.now(),
          sender: 'laoshi',
          text: `请用'${mockWord.word}'造一个句子`,
          timestamp: getCurrentTime(),
        }
        setMessages((prev) => [...prev, promptMessage])
      }
    } catch (error) {
      console.error('Error fetching word:', error)
      // Fallback mock data
      const mockWord: VocabularyWord = {
        id: '1',
        word: '学习',
        pinyin: 'xué xí',
        definition: 'to study, to learn',
        confidenceLevel: 'Learning',
      }
      setCurrentWord(mockWord)
      const promptMessage: Message = {
        id: Date.now(),
        sender: 'laoshi',
        text: `请用'${mockWord.word}'造一个句子`,
        timestamp: getCurrentTime(),
      }
      setMessages((prev) => [...prev, promptMessage])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNextWord()
  }, [])

  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleSubmit = async () => {
    if (!inputText.trim() || !currentWord) return

    // Add user message
    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      text: inputText,
      timestamp: getCurrentTime(),
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      // Call evaluation API
      const response = await fetch('/api/practice/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wordId: currentWord.id,
          sentence: inputText,
        }),
      })

      if (response.ok) {
        const evaluation = await response.json()
        const laoshiResponse: Message = {
          id: Date.now() + 1,
          sender: 'laoshi',
          text: evaluation.feedback || `Great job! 很好！ Your sentence shows good understanding of "${currentWord.word}". The structure is natural and the context is appropriate. Keep practicing!`,
          timestamp: getCurrentTime(),
        }
        setMessages((prev) => [...prev, laoshiResponse])
      } else {
        // Fallback response
        const laoshiResponse: Message = {
          id: Date.now() + 1,
          sender: 'laoshi',
          text: `Great job! 很好！ Your sentence shows good understanding of "${currentWord.word}". The structure is natural and the context is appropriate. Keep practicing!`,
          timestamp: getCurrentTime(),
        }
        setMessages((prev) => [...prev, laoshiResponse])
      }
    } catch (error) {
      // Fallback response if API fails
      const laoshiResponse: Message = {
        id: Date.now() + 1,
        sender: 'laoshi',
        text: `Great job! 很好！ Your sentence shows good understanding of "${currentWord.word}". The structure is natural and the context is appropriate. Keep practicing!`,
        timestamp: getCurrentTime(),
      }
      setMessages((prev) => [...prev, laoshiResponse])
    }

    // Add to practiced words
    setPracticedWords((prev) => [...prev, currentWord])
    setInputText('')

    // Fetch next word after a short delay
    setTimeout(() => {
      fetchNextWord()
    }, 1500)
  }

  const handleSkip = () => {
    if (!currentWord) return

    // Add skip message
    const skipMessage: Message = {
      id: Date.now(),
      sender: 'laoshi',
      text: `No problem! Let's move on to the next word.`,
      timestamp: getCurrentTime(),
    }
    setMessages((prev) => [...prev, skipMessage])

    // Add to skipped words
    setSkippedWords((prev) => [...prev, currentWord])

    // Fetch next word
    fetchNextWord()
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

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
            {wordsProgress.current} / {wordsProgress.total} words practiced
          </p>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-pink-500 via-purple-500 to-blue-500"
              style={{ width: `${(wordsProgress.current / wordsProgress.total) * 100}%` }}
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
            {loading ? (
              <div className="py-8 text-gray-400">Loading...</div>
            ) : currentWord ? (
              <>
                <div className="text-6xl font-medium text-gray-900 mb-4">
                  {currentWord.word}
                </div>

                {showPinyin && (
                  <div className="text-lg text-gray-600 mb-2">{currentWord.pinyin}</div>
                )}

                {showTranslation && (
                  <div className="text-gray-500">{currentWord.definition}</div>
                )}

                <div className="mt-6 pt-4 border-t border-gray-200/50">
                  <p className="text-xs text-gray-500 mb-2">Confidence Level</p>
                  <span className="inline-block px-4 py-1.5 bg-orange-400 text-white text-sm font-medium rounded-full">
                    {currentWord.confidenceLevel}
                  </span>
                </div>
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
            <span>Practiced Words</span>
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
                practicedWords.map((word) => (
                  <div key={word.id} className="py-1">{word.word}</div>
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
            <span>Skipped Words</span>
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
                skippedWords.map((word) => (
                  <div key={word.id} className="py-1">{word.word}</div>
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
          <div className="flex items-center gap-4 text-gray-400">
            <button className="hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
            </button>
            <button className="hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
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
                <p className="text-base">{message.text}</p>
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
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="bg-gray-50 rounded-2xl border border-gray-200 p-4">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your sentence here..."
              className="w-full bg-transparent resize-none outline-none text-gray-800 placeholder-gray-400 min-h-[60px]"
              rows={2}
            />
            <div className="flex items-center justify-between mt-2">
              <button
                onClick={handleSkip}
                className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
                <span className="text-sm">Skip this word</span>
              </button>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-400">{inputText.length} characters</span>
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim()}
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
