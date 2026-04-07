import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import axios from 'axios'
import { deckApi, practiceApi } from '../../lib/api'
import type { DeckWithStats } from '../../types/api'
import { useHome } from './HomeContext'
import { Play, ArrowRight } from 'lucide-react'

// Format time ago for "Last practiced" pill
function formatTimeAgo(dateString: string | null): string {
  if (!dateString) return 'Never practiced'

  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (seconds < 60) return 'Just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days} days ago`
  return date.toLocaleDateString()
}

// Reusable ProgressRing SVG component
function ProgressRing({
  percentage,
  size = 160,
  strokeWidth = 10,
}: {
  percentage: number
  size?: number
  strokeWidth?: number
}) {
  const center = size / 2
  const radius = center - strokeWidth
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="w-full h-full transform -rotate-90">
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          className="text-warm-gray"
        />
        {/* Fill */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="text-sage transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-warm-black">{percentage}%</span>
        <span className="text-xs text-warm-muted">mastered</span>
      </div>
    </div>
  )
}

export default function DeckDetailPanel() {
  const { deckId } = useParams<{ deckId: string }>()
  const [deck, setDeck] = useState<DeckWithStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [startingPractice, setStartingPractice] = useState(false)
  const { startPractice } = useHome()
  const navigate = useNavigate()

  useEffect(() => {
    if (deckId) {
      loadDeck(parseInt(deckId))
    }
  }, [deckId])

  const loadDeck = async (id: number) => {
    try {
      const response = await deckApi.getDeck(id)
      setDeck(response.data)
    } catch (error) {
      console.error('Failed to load deck:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStartPractice = async () => {
    if (!deck) return

    setStartingPractice(true)
    try {
      const response = await practiceApi.startSession(deck.id)
      startPractice({
        sessionId: response.data.session.id,
        deckId: deck.id,
        deckName: deck.name,
        greeting: response.data.greeting_message,
        currentWord: response.data.current_word,
      })
    } catch (error) {
      console.error('Failed to start practice:', error)
      if (axios.isAxiosError(error) && error.response?.status === 429) {
        alert('AI rate limit reached. Add your own API key in Settings to continue practicing.')
      } else {
        alert('Failed to start practice session. Please try again.')
      }
    } finally {
      setStartingPractice(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-warm-muted">Loading...</div>
      </div>
    )
  }

  if (!deck) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-warm-muted mb-4">Deck not found</p>
          <button
            onClick={() => navigate('/home')}
            className="text-sage hover:text-sage/80"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  const masteredCount = deck.mastered_count || 0
  const wordCount = deck.word_count || 0
  const practicedCount = wordCount - masteredCount

  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-warm-offwhite p-8 relative overflow-hidden">
      {/* Decorative blur circle */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-sage-tint rounded-full opacity-50 blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
        className="max-w-3xl w-full bg-white rounded-3xl p-12 border border-warm-gray shadow-sm relative"
      >
        {/* 2-column layout: progress ring + content */}
        <div className="flex gap-12 items-start">
          {/* Left: Progress ring */}
          <div className="flex-shrink-0">
            <ProgressRing percentage={deck.mastery_percentage} />
          </div>

          {/* Right: Content */}
          <div className="flex-1 min-w-0">
            {/* Last practiced pill */}
            <span className="inline-flex items-center px-3 py-1 bg-warm-gray/30 text-warm-black/60 rounded-full text-xs mb-3">
              Last practiced {formatTimeAgo(deck.last_practiced_at)}
            </span>

            {/* Deck name (serif) */}
            <h1 className="font-serif text-4xl text-warm-black mb-6">{deck.name}</h1>

            {/* 3-column stats */}
            <div className="grid grid-cols-3 gap-6 mb-6">
              <div>
                <p className="text-2xl font-medium text-warm-black">{wordCount}</p>
                <p className="text-xs text-warm-muted">Total Words</p>
              </div>
              <div>
                <p className="text-2xl font-medium text-warm-black">{practicedCount}</p>
                <p className="text-xs text-warm-muted">Practiced</p>
              </div>
              <div>
                <p className="text-2xl font-medium text-sage">{masteredCount}</p>
                <p className="text-xs text-warm-muted">Mastered</p>
              </div>
            </div>

            {/* Laoshi message quote box */}
            {deck.laoshi_message && (
              <div className="bg-sage-tint/50 p-5 rounded-2xl border border-warm-gray/50 mb-6">
                <p className="text-warm-black/80 italic text-sm">
                  "{deck.laoshi_message}"
                </p>
              </div>
            )}

            {/* Button row */}
            <div className="flex items-center gap-6">
              <button
                onClick={handleStartPractice}
                disabled={startingPractice || wordCount === 0}
                className="flex items-center gap-2 bg-sage hover:bg-sage/90 text-white px-8 py-4 rounded-xl text-lg font-medium disabled:bg-warm-gray disabled:cursor-not-allowed transition-colors"
              >
                <Play className="w-5 h-5" />
                {startingPractice ? 'Starting...' : 'Start Practice'}
              </button>

              <button
                onClick={() => navigate(`/library/deck/${deck.id}`)}
                className="group flex items-center gap-1 text-warm-black/40 hover:text-warm-black transition-colors text-sm font-medium"
              >
                Manage in Library
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
