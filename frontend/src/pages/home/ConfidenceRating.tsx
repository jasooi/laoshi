import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Pencil } from 'lucide-react'
import laoshiLogo from '../../assets/laoshi-logo.png'

const RATINGS = [
  { value: 0, label: 'Blackout' },
  { value: 1, label: 'Very Hard' },
  { value: 2, label: 'Hard' },
  { value: 3, label: 'OK' },
  { value: 4, label: 'Good' },
  { value: 5, label: 'Easy' },
]

/** 3-tier color coding: 0-2 coral, 3 amber, 4-5 sage */
function getRatingColor(quality: number): { bg: string; text: string } {
  if (quality <= 2) return { bg: 'bg-coral/15', text: 'text-coral' }
  if (quality === 3) return { bg: 'bg-amber/15', text: 'text-amber' }
  return { bg: 'bg-sage/15', text: 'text-sage' }
}

interface ConfidenceRatingProps {
  messageId: string
  wordId: number
  wordText: string
  quality?: number
  isLatest: boolean
  onRate: (messageId: string, wordId: number, quality: number, isEdit: boolean) => void
}

export default function ConfidenceRating({
  messageId, wordId, wordText, quality, isLatest, onRate,
}: ConfidenceRatingProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [highlightedValue, setHighlightedValue] = useState<number | null>(null)

  const showButtons = (quality === undefined && isLatest) || isEditing
  const selectedLabel = quality !== undefined
    ? RATINGS.find(r => r.value === quality)?.label
    : null

  const handleClick = (value: number) => {
    setHighlightedValue(value)
    setTimeout(() => {
      const isEdit = !isLatest || quality !== undefined
      onRate(messageId, wordId, value, isEdit)
      setIsEditing(false)
      setHighlightedValue(null)
    }, 150)
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const colors = quality !== undefined ? getRatingColor(quality) : null

  return (
    <div className="flex gap-3 mb-4">
      {/* Laoshi avatar */}
      <img
        src={laoshiLogo}
        alt="Laoshi"
        className="w-7 h-7 rounded-full flex-shrink-0 self-end mb-5"
      />

      <div className="max-w-[75%]">
        {/* Message bubble */}
        <div
          className={`bg-white border border-warm-gray/40 shadow-sm px-4 py-3 ${
            showButtons
              ? 'rounded-2xl rounded-tl-sm rounded-b-[4px]'
              : 'rounded-2xl rounded-tl-sm'
          }`}
        >
          <p className="text-[15px] text-warm-black leading-relaxed">
            Before we move on &mdash; how confident are you using{' '}
            <span className="font-serif font-medium">{wordText}</span>?
          </p>

          {/* Color-coded rating pill + edit icon (shown after rating) */}
          {quality !== undefined && !isEditing && colors && (
            <div className="flex items-center gap-2 mt-2">
              <motion.span
                key={quality}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.2, delay: 0.05 }}
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
              >
                {quality} &mdash; {selectedLabel}
              </motion.span>
              <button
                onClick={handleEdit}
                className="text-warm-black/30 hover:text-warm-black/50 transition-colors"
                title="Edit rating"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Rating button row */}
        <AnimatePresence>
          {showButtons && (
            <motion.div
              initial={{ opacity: isEditing ? 0 : 1, height: isEditing ? 0 : 'auto' }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="flex border border-t-0 border-warm-gray/40 rounded-b-2xl bg-white shadow-sm">
                {RATINGS.map((rating, idx) => (
                  <button
                    key={rating.value}
                    onClick={() => handleClick(rating.value)}
                    className={`flex-1 flex flex-col items-center justify-center py-3 min-h-[56px] transition-colors ${
                      idx < RATINGS.length - 1 ? 'border-r border-warm-gray/30' : ''
                    } ${
                      highlightedValue === rating.value
                        ? 'bg-sage/15'
                        : quality === rating.value
                          ? 'bg-warm-offwhite'
                          : 'hover:bg-warm-offwhite/80'
                    }`}
                  >
                    <span className="text-lg font-medium text-warm-black">
                      {rating.value}
                    </span>
                    <span className="text-[10px] font-medium text-warm-black/40">
                      {rating.label}
                    </span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Timestamp */}
        <p className="text-[10px] text-warm-black/30 mt-1">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
