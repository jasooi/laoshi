import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { WordContext } from '../../types/api'

interface FloatingWordPillProps {
  word: WordContext
  notes?: string | null
}

export default function FloatingWordPill({ word, notes }: FloatingWordPillProps) {
  const [expanded, setExpanded] = useState(false)
  const pillRef = useRef<HTMLDivElement>(null)

  // Click outside to collapse
  useEffect(() => {
    if (!expanded) return

    const handleClickOutside = (e: MouseEvent) => {
      if (pillRef.current && !pillRef.current.contains(e.target as Node)) {
        setExpanded(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [expanded])

  return (
    <div className="sticky top-0 z-10 flex justify-center px-6 pt-3 pb-2"
      style={{
        background: 'linear-gradient(to bottom, rgba(245,243,238,0.95) 60%, transparent)',
      }}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={word.word_id}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        >
          <motion.div
            ref={pillRef}
            layout
            transition={{ duration: 0.28, ease: [0.25, 0.1, 0.25, 1] }}
            className={`bg-white border border-warm-gray/60 ${
              expanded ? 'rounded-2xl max-w-[42rem] w-full' : 'rounded-full cursor-pointer hover:border-warm-gray'
            }`}
            onClick={() => !expanded && setExpanded(true)}
          >
            {expanded ? (
              /* Expanded state */
              <div className="p-6">
                <div className="flex gap-8">
                  {/* Left column */}
                  <div className="flex-shrink-0 min-w-[100px] flex flex-col justify-center">
                    <span className="text-5xl font-serif text-warm-black leading-none mb-2">
                      {word.word}
                    </span>
                    <span className="text-sm font-medium text-sage">
                      {word.pinyin}
                    </span>
                  </div>

                  {/* Right column */}
                  <div className="flex-1 min-w-0">
                    <p className="text-base text-warm-black/80 leading-relaxed mb-4">
                      {word.meaning}
                    </p>

                    {notes && (
                      <div className="bg-warm-offwhite rounded-lg p-3 mb-3">
                        <p className="text-xs text-warm-black/40 mb-1">Your note</p>
                        <p className="text-sm text-warm-black/70">{notes}</p>
                      </div>
                    )}
                  </div>

                  {/* Collapse button */}
                  <button
                    onClick={(e) => { e.stopPropagation(); setExpanded(false) }}
                    className="self-start p-1.5 text-warm-black/30 hover:text-warm-black/60 transition-colors"
                  >
                    <ChevronUp className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              /* Collapsed state */
              <div className="flex items-center gap-3 px-5 py-2">
                <span className="text-xl font-serif font-medium text-warm-black">
                  {word.word}
                </span>
                <span className="text-sm text-warm-black/40">
                  {word.pinyin}
                </span>
                <span className="text-warm-black/20">&mdash;</span>
                <span className="text-sm text-warm-black/50 truncate max-w-[240px]">
                  {word.meaning}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-warm-black/25 flex-shrink-0" />
              </div>
            )}
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
