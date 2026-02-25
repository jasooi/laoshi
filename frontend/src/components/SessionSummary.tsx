import { Link } from 'react-router-dom'
import type { PracticeSummaryResponse } from '../types/api'

interface SessionSummaryProps {
  summary: PracticeSummaryResponse
  onNewSession: () => void
}

export function SessionSummary({ summary, onNewSession }: SessionSummaryProps) {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Session Complete!</h2>
        <p className="text-gray-600">
          {summary.words_practiced} practiced, {summary.words_skipped} skipped
        </p>
      </div>

      {/* Summary text */}
      <div className="bg-purple-50 rounded-xl p-6 border border-purple-100">
        <p className="text-purple-900 leading-relaxed text-lg">{summary.summary_text}</p>
      </div>

      {/* Word results table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Word</th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Grammar</th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Usage</th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Naturalness</th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {summary.word_results.map((result, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{result.word}</td>
                <td className="px-4 py-3 text-center text-gray-600">
                  {result.is_skipped ? '—' : result.grammar_score?.toFixed(1) ?? '—'}
                </td>
                <td className="px-4 py-3 text-center text-gray-600">
                  {result.is_skipped ? '—' : result.usage_score?.toFixed(1) ?? '—'}
                </td>
                <td className="px-4 py-3 text-center text-gray-600">
                  {result.is_skipped ? '—' : result.naturalness_score?.toFixed(1) ?? '—'}
                </td>
                <td className="px-4 py-3 text-center">
                  {result.is_skipped ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      Skipped
                    </span>
                  ) : result.is_correct ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      ✓ Correct
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                      ✗ Needs work
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <button
          onClick={onNewSession}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
        >
          Start New Session
        </button>
        <Link
          to="/home"
          className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors text-center"
        >
          Back to Home
        </Link>
      </div>
    </div>
  )
}
