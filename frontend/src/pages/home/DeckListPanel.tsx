import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deckApi, progressApi } from '../../lib/api'
import type { DeckWithStats, StreakData } from '../../types/api'
import { useHome } from './HomeContext'
import { Flame, Plus, Sprout, Leaf, Flower2 } from 'lucide-react'

// Recency color hex values for inline styles (Home DeckListItem avatars)
function getRecencyColor(lastPracticedAt: string | null): { bg: string; bar: string; tint: string } {
  if (!lastPracticedAt) {
    return { bg: '#A8A5A0', bar: '#A8A5A0', tint: '#F2F1EF' }  // neutral
  }

  const hours = (Date.now() - new Date(lastPracticedAt).getTime()) / 3_600_000

  if (hours < 48) {
    return { bg: '#6B8F71', bar: '#6B8F71', tint: '#EDF2EE' }   // sage
  }
  if (hours < 120) {
    return { bg: '#C4973B', bar: '#C4973B', tint: '#FBF5E8' }   // amber
  }
  return { bg: '#D4715E', bar: '#D4715E', tint: '#FDF0ED' }     // coral
}

// Growth icons (Lucide) for DeckListItem avatars
function getGrowthIcon(masteryPercentage: number) {
  if (masteryPercentage < 25) return <Sprout size={20} strokeWidth={2} />
  if (masteryPercentage < 75) return <Leaf size={20} strokeWidth={2} />
  return <Flower2 size={20} strokeWidth={2} />
}

// Format time ago
function formatTimeAgo(dateString: string | null): string {
  if (!dateString) return 'Never'

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
  if (days < 30) return `${days}d ago`
  return date.toLocaleDateString()
}

// A streak is "alive" if the user practiced today or yesterday
function isStreakAlive(streak: StreakData): boolean {
  if (streak.current_streak === 0 || !streak.last_practice_date) return false
  const last = new Date(streak.last_practice_date)
  const now = new Date()
  // Compare calendar dates (not timestamps) to handle timezone edge cases
  const lastDate = new Date(last.getFullYear(), last.getMonth(), last.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = (today.getTime() - lastDate.getTime()) / 86_400_000
  return diffDays <= 1
}

interface DeckListItemProps {
  deck: DeckWithStats
  isActive: boolean
  onClick: () => void
}

function DeckListItem({ deck, isActive, onClick }: DeckListItemProps) {
  const colors = getRecencyColor(deck.last_practiced_at)
  const masteredCount = deck.mastered_count || 0
  const wordCount = deck.word_count || 0

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-5 py-4 border-b border-warm-gray transition-all relative ${
        isActive ? 'bg-sage-tint' : 'hover:bg-warm-offwhite'
      }`}
    >
      {/* Active indicator bar */}
      {isActive && (
        <div
          className="absolute left-0 top-0 bottom-0 w-[3px]"
          style={{ backgroundColor: colors.bg }}
        />
      )}

      <div className="flex items-start gap-3">
        {/* Recency-colored circle avatar with growth icon */}
        <div
          className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 text-white"
          style={{ backgroundColor: colors.bg }}
        >
          {getGrowthIcon(deck.mastery_percentage)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Name + time ago */}
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-warm-black truncate">{deck.name}</h3>
            <span className="text-[11px] text-warm-muted ml-2 flex-shrink-0">
              {formatTimeAgo(deck.last_practiced_at)}
            </span>
          </div>

          {/* Laoshi message preview */}
          {deck.laoshi_message && (
            <p className="text-sm text-warm-muted mt-0.5 truncate">
              {deck.laoshi_message}
            </p>
          )}
        </div>
      </div>

      {/* Progress bar indented under avatar */}
      <div className="pl-[56px] mt-2 flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-warm-gray/60 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${deck.mastery_percentage}%`, backgroundColor: colors.bar }}
          />
        </div>
        <span className="text-[10px] text-warm-muted flex-shrink-0">
          {masteredCount}/{wordCount}
        </span>
      </div>
    </button>
  )
}

interface DeckListPanelProps {
  width?: number
}

export default function DeckListPanel({ width }: DeckListPanelProps) {
  const [decks, setDecks] = useState<DeckWithStats[]>([])
  const [streak, setStreak] = useState<StreakData>({ current_streak: 0, last_practice_date: null })
  const [loading, setLoading] = useState(true)
  const { selectedDeckId, selectDeck, setDeckCount } = useHome()
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
      setDeckCount(decksRes.data.decks.length)
      setStreak(streakRes.data)
    } catch (error) {
      console.error('Failed to load decks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeckClick = (deckId: number) => {
    selectDeck(deckId)
    navigate(`/home/deck/${deckId}`)
  }

  if (loading) {
    return (
      <div className="bg-warm-offwhite border-r border-warm-gray p-4" style={width ? { width } : undefined}>
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-warm-gray rounded"></div>
          <div className="h-32 bg-warm-gray rounded"></div>
          <div className="h-32 bg-warm-gray rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-warm-offwhite border-r border-warm-gray flex flex-col h-full flex-shrink-0" style={width ? { width } : undefined}>
      {/* Streak badge — height aligned to sidebar Home button bottom + 3px */}
      <div className="h-[75px] px-4 border-b border-warm-gray flex items-center">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Flame className={`w-5 h-5 ${isStreakAlive(streak) ? 'text-orange-500' : 'text-warm-muted'}`} />
            <span className="font-semibold text-warm-black">
              {isStreakAlive(streak)
                ? `${streak.current_streak} day streak`
                : 'Start practicing to begin a streak!'}
            </span>
          </div>
          {isStreakAlive(streak) && (
            <span className="text-xs text-warm-muted">
              Keep it up!
            </span>
          )}
        </div>
      </div>

      {/* Deck list */}
      <div className="flex-1 overflow-y-auto">
        {decks.length === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-warm-muted mb-4">No decks yet</p>
            <button
              onClick={() => navigate('/library')}
              className="text-sage hover:text-sage/80 font-medium"
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
      <div className="p-4 border-t border-warm-gray">
        <button
          onClick={() => navigate('/library')}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Deck
        </button>
      </div>
    </div>
  )
}
