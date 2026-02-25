import type { FeedbackData } from '../types/api'

interface FeedbackCardProps {
  feedback: FeedbackData
}

function getScoreColor(score: number): string {
  if (score >= 8) return 'bg-green-100 text-green-800 border-green-200'
  if (score >= 5) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
  return 'bg-red-100 text-red-800 border-red-200'
}

export function FeedbackCard({ feedback }: FeedbackCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm space-y-4">
      {/* Score badges */}
      <div className="flex flex-wrap gap-3">
        <div className={`px-3 py-2 rounded-lg border ${getScoreColor(feedback.grammarScore)}`}>
          <div className="text-xs font-medium uppercase tracking-wide">Grammar</div>
          <div className="text-lg font-bold">{feedback.grammarScore}/10</div>
        </div>
        <div className={`px-3 py-2 rounded-lg border ${getScoreColor(feedback.usageScore)}`}>
          <div className="text-xs font-medium uppercase tracking-wide">Usage</div>
          <div className="text-lg font-bold">{feedback.usageScore}/10</div>
        </div>
        <div className={`px-3 py-2 rounded-lg border ${getScoreColor(feedback.naturalnessScore)}`}>
          <div className="text-xs font-medium uppercase tracking-wide">Naturalness</div>
          <div className="text-lg font-bold">{feedback.naturalnessScore}/10</div>
        </div>
      </div>

      {/* Correctness indicator */}
      <div className="flex items-center gap-2">
        {feedback.isCorrect ? (
          <>
            <span className="text-green-600 text-xl">✓</span>
            <span className="text-green-700 font-medium">Correct! Well done.</span>
          </>
        ) : (
          <>
            <span className="text-amber-600 text-xl">⚠</span>
            <span className="text-amber-700 font-medium">Needs improvement</span>
          </>
        )}
      </div>

      {/* Feedback text */}
      <p className="text-gray-700 leading-relaxed">{feedback.feedback}</p>

      {/* Corrections */}
      {feedback.corrections && feedback.corrections.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-2">Corrections:</h4>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            {feedback.corrections.map((correction, idx) => (
              <li key={idx}>{correction}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Explanations */}
      {feedback.explanations && feedback.explanations.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-2">Explanations:</h4>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            {feedback.explanations.map((explanation, idx) => (
              <li key={idx}>{explanation}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Example sentences */}
      {feedback.exampleSentences && feedback.exampleSentences.length > 0 && (
        <div className="bg-purple-50 rounded-lg p-3">
          <h4 className="font-semibold text-purple-900 mb-2">Example sentences:</h4>
          <ul className="space-y-2">
            {feedback.exampleSentences.map((sentence, idx) => (
              <li key={idx} className="text-purple-800 font-medium">
                {sentence}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
