import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deckApi, progressApi } from '../../lib/api'
import type { DeckWithStats, StreakData } from '../../types/api'
import { useHome } from './HomeContext'
import { Flame, Plus } from 'lucide-react'

// Growth icons based on mastery percentage
function getGrowthIcon(masteryPercentage: number): string {
  if (masteryPercentage < 25) return '🌱'
  if (masteryPercentage < 75) return '🌿'
  return '🌸'
}

// Recency colors
function getRecencyColor(lastPracticedAt: string | null): {
  text: string
  bg: string
  badge: string
  label: string
} {
  if (!lastPracticedAt) {
    return { text: 'text-stone-400', bg: 'bg-stone-300', badge: '⚫', label: 'Never' }
  }

  const hoursSince = (Date.now() - new Date(lastPracticedAt).getTime()) / (1000 * 60 * 60)

  if (hoursSince < 48) {
    return { text: 'text-green-500', bg: 'bg-green-500', badge: '🟢', label: '< 48h' }
  }
  if (hoursSince < 120) {
    return { text: 'text-yellow-500', bg: 'bg-yellow-500', badge: '🟡', label: '2-5d' }
  }
  return { text: 'text-red-500', bg: 'bg-red-500', badge: '🔴', label: '> 5d' }
}

// Format time ago
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
  if (days < 30) return `${days}d ago`
  return date.toLocaleDateString()
}

interface DeckListItemProps {
  deck: DeckWithStats
  isActive: boolean
  onClick: () => void
}

function DeckListItem({ deck, isActive, onClick }: DeckListItemProps) {
  const colors = getRecencyColor(deck.last_practiced_at)
  const growthIcon = getGrowthIcon(deck.mastery_percentage)
  const masteredCount = deck.mastered_count || 0
  const wordCount = deck.word_count || 0

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-lg border transition-all ${
        isActive
          ? 'border-primary-500 bg-primary-50'
          : 'border-stone-200 bg-white hover:border-primary-300 hover:bg-stone-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-stone-800 truncate">{deck.name}</h3>
          <p className="text-sm text-stone-500 mt-1 line-clamp-1">
            {masteredCount}/{wordCount} words mastered
          </p>
        </div>
        <span className={`text-2xl ml-2 ${colors.text}`}>{growthIcon}</span>
      </div>

      {/* Progress bar colored by recency */}
      <div className="mt-3">
        <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${colors.bg} transition-all`}
            style={{ width: `${deck.mastery_percentage}%` }}
          />
        </div>
      </div>

      {/* Recency badge */}
      <div className="mt-2 flex items-center text-xs text-stone-500">
        <span>{colors.badge}</span>
        <span className="ml-1">{formatTimeAgo(deck.last_practiced_at)}</span>
      </div>

      {/* Laoshi message preview */}
      {deck.laoshi_message && (
        <p className="mt-2 text-xs text-stone-600 line-clamp-2 italic">
          "{deck.laoshi_message}"
        </p>
      )}
    </button>
  )
}

export default function DeckListPanel() {
  const [decks, setDecks] = useState<DeckWithStats[]>([])
  const [streak, setStreak] = useState<StreakData>({ current_streak: 0, last_practice_date: null })
  const [loading, setLoading] = useState(true)
  const { selectedDeckId, requestDeckSwitch } = useHome()
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [decksRes, streakRes] = await Promise.all([
        deckApi.getDecks(),
        progressApi.getStreak(),
      ])
      setDecks(decksRes.data.decks)
      setStreak(streakRes.data)
    } catch (error) {
      console.error('Failed to load decks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeckClick = (deckId: number) => {
    requestDeckSwitch(deckId)
  }

  if (loading) {
    return (
      <div className="w-full md:w-80 lg:w-96 bg-stone-50 border-r border-stone-200 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-stone-200 rounded"></div>
          <div className="h-32 bg-stone-200 rounded"></div>
          <div className="h-32 bg-stone-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full md:w-80 lg:w-96 bg-stone-50 border-r border-stone-200 flex flex-col h-full">
      {/* Streak badge */}
      <div className="p-4 border-b border-stone-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="w-5 h-5 text-orange-500" />
            <span className="font-semibold text-stone-800">
              {streak.current_streak} day streak
            </span>
          </div>
          <span className="text-xs text-stone-500">
            {streak.last_practice_date
              ? 'Keep it up!'
              : 'Start practicing today!'}
          </span>
        </div>
      </div>

      {/* Deck list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {decks.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-stone-500 mb-4">No decks yet</p>
            <button
              onClick={() => navigate('/library')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Create your first deck →
            </button>
          </div>
        ) : (
          decks.map((deck) => (
            <DeckListItem
              key={deck.id}
              deck={deck}
              isActive={selectedDeckId === deck.id}
              onClick={() => handleDeckClick(deck.id)}
            />
          ))
        )}
      </div>

      {/* New deck button */}
      <div className="p-4 border-t border-stone-200">
        <button
          onClick={() => navigate('/library')}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Deck
        </button>
      </div>
    </div>
  )
}
