import type { PracticeSummaryResponse } from '../types/api'
import { progressApi } from '../lib/api'
import { useHome } from '../pages/home/HomeContext'
import { Check, X } from 'lucide-react'
import { motion } from 'framer-motion'

interface SessionSummaryProps {
  summary: PracticeSummaryResponse
  onNewSession: () => void
}

export function SessionSummary({ summary, onNewSession }: SessionSummaryProps) {
  const { backToHome } = useHome()

  const handleBackToHome = () => {
    progressApi.generateFeedback().catch(() => {})
    backToHome()
  }

  return (
    <div className="h-full overflow-y-auto bg-warm-offwhite">
      <div className="max-w-[56rem] mx-auto py-16 px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <h2 className="font-serif text-3xl font-medium text-warm-black">
            Session Complete!
          </h2>
          <p className="text-warm-black/50 mt-2">
            {summary.words_practiced} practiced, {summary.words_skipped} skipped
          </p>
        </div>

        {/* AI Summary */}
        <div className="bg-sage-tint border border-sage/15 rounded-2xl p-8 mb-10">
          <p className="italic text-base text-warm-black/70 leading-relaxed">
            {summary.summary_text}
          </p>
        </div>

        {/* Results table */}
        <div className="bg-white border border-warm-gray rounded-2xl shadow-sm overflow-hidden mb-12">
          {/* Header row */}
          <div className="bg-warm-offwhite/50 border-b border-warm-gray/50 grid grid-cols-5 gap-4 py-4 px-6">
            {['Word', 'Grammar', 'Usage', 'Naturalness', 'Status'].map((col) => (
              <span key={col} className="text-[11px] uppercase font-bold tracking-wider text-warm-black/40">
                {col}
              </span>
            ))}
          </div>

          {/* Data rows */}
          {summary.word_results.map((result, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + idx * 0.05 }}
              className={`grid grid-cols-5 gap-4 py-4 px-6 items-center ${
                idx < summary.word_results.length - 1 ? 'border-b border-warm-gray/30' : ''
              }`}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-serif text-lg text-warm-black">{result.word}</span>
              </div>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '\u2014' : result.grammar_score?.toFixed(1) ?? '\u2014'}
              </span>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '\u2014' : result.usage_score?.toFixed(1) ?? '\u2014'}
              </span>
              <span className="text-sm tabular-nums text-warm-black/70">
                {result.is_skipped ? '\u2014' : result.naturalness_score?.toFixed(1) ?? '\u2014'}
              </span>
              <div>
                {result.is_skipped ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warm-gray/30 text-warm-black/50">
                    Skipped
                  </span>
                ) : result.is_correct ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage-tint text-sage">
                    <Check className="w-3 h-3" /> Correct
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-coral/10 text-coral">
                    <X className="w-3 h-3" /> Needs work
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={onNewSession}
            className="px-8 py-3.5 bg-sage hover:bg-sage/90 text-white font-medium rounded-xl shadow-sm transition-colors"
          >
            Start New Session
          </button>
          <button
            onClick={handleBackToHome}
            className="px-8 py-3.5 bg-white border border-warm-gray text-warm-black font-medium rounded-xl hover:bg-warm-offwhite transition-colors"
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  )
}
