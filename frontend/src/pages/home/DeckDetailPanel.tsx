import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { deckApi, practiceApi } from '../../lib/api'
import type { DeckWithStats } from '../../types/api'
import { useHome } from './HomeContext'
import { BookOpen, Play, ArrowRight } from 'lucide-react'

// Growth stage names
function getGrowthStage(masteryPercentage: number): string {
  if (masteryPercentage < 25) return 'Seedling'
  if (masteryPercentage < 75) return 'Growing'
  return 'Blooming'
}

// Growth icons
function getGrowthIcon(masteryPercentage: number): string {
  if (masteryPercentage < 25) return '🌱'
  if (masteryPercentage < 75) return '🌿'
  return '🌸'
}

// Circular progress component
function CircularProgress({ percentage }: { percentage: number }) {
  const radius = 50
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full transform -rotate-90">
        {/* Background circle */}
        <circle
          cx="64"
          cy="64"
          r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          className="text-stone-200"
        />
        {/* Progress circle */}
        <circle
          cx="64"
          cy="64"
          r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="text-primary-500 transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-stone-800">{percentage}%</span>
        <span className="text-xs text-stone-500">mastered</span>
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
      const sessionId = response.data.session.id
      startPractice(deck.id, sessionId)
      navigate(`/home/deck/${deck.id}/practice`)
    } catch (error) {
      console.error('Failed to start practice:', error)
      alert('Failed to start practice session. Please try again.')
    } finally {
      setStartingPractice(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-stone-400">Loading...</div>
      </div>
    )
  }

  if (!deck) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-stone-500 mb-4">Deck not found</p>
          <button
            onClick={() => navigate('/home')}
            className="text-primary-600 hover:text-primary-700"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  const growthStage = getGrowthStage(deck.mastery_percentage)
  const growthIcon = getGrowthIcon(deck.mastery_percentage)
  const masteredCount = deck.mastered_count || 0
  const wordCount = deck.word_count || 0

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-stone-50">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-stone-200 p-8">
        {/* Header */}
        <h1 className="text-2xl font-bold text-stone-800 text-center mb-2">
          {deck.name}
        </h1>
        {deck.description && (
          <p className="text-stone-500 text-center mb-6">{deck.description}</p>
        )}

        {/* Circular progress */}
        <div className="flex justify-center mb-6">
          <CircularProgress percentage={deck.mastery_percentage} />
        </div>

        {/* Stats */}
        <div className="text-center mb-6">
          <p className="text-lg text-stone-700">
            <span className="font-semibold">{masteredCount}</span>
            <span className="text-stone-400"> / </span>
            <span className="font-semibold">{wordCount}</span> words mastered
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="text-2xl">{growthIcon}</span>
            <span className="text-stone-600 font-medium">{growthStage}</span>
          </div>
        </div>

        {/* Laoshi message */}
        {deck.laoshi_message && (
          <div className="bg-primary-50 rounded-lg p-4 mb-6">
            <p className="text-stone-700 text-center italic">
              "{deck.laoshi_message}"
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleStartPractice}
            disabled={startingPractice || wordCount === 0}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-stone-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            <Play className="w-5 h-5" />
            {startingPractice ? 'Starting...' : 'Start Practice'}
          </button>

          <button
            onClick={() => navigate(`/library/deck/${deck.id}`)}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 border border-stone-300 text-stone-700 rounded-lg hover:bg-stone-50 transition-colors font-medium"
          >
            <BookOpen className="w-5 h-5" />
            Manage in Library
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
