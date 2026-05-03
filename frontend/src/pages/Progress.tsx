import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { progressApi } from '../lib/api'
import type { ReportCardData } from '../types/api'
import laoshiLogo from '../assets/laoshi-logo.png'
import seal from '../assets/seal.png'

const Progress = () => {
  const [reportCard, setReportCard] = useState<ReportCardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'feedback' | 'scores'>('feedback')
  const [showTooltip, setShowTooltip] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const fetchReportCard = async () => {
      try {
        const response = await progressApi.getReportCard()
        setReportCard(response.data)
      } catch {
        // Failed to load report card data
      } finally {
        setLoading(false)
      }
    }
    fetchReportCard()
  }, [])

  const toggleTooltip = (key: string) => {
    setShowTooltip(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto flex items-center justify-center min-h-[500px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sage" />
      </div>
    )
  }

  // Full-page empty state for new users
  if (reportCard && reportCard.topline.sessions_completed === 0) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <svg className="w-8 h-8 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h1 className="text-2xl font-bold text-warm-black">Report Card</h1>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-16 flex flex-col items-center justify-center min-h-[500px]">
          <div className="w-32 h-32 rounded-full bg-sage-tint flex items-center justify-center mb-6">
            <svg className="w-16 h-16 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-warm-black mb-2">No practice data yet</h2>
          <p className="text-warm-muted text-lg mb-6">Complete a practice session to see your Report Card.</p>
          <Link
            to="/practice"
            className="px-6 py-3 bg-sage text-white rounded-lg font-medium hover:bg-sage/80 transition-colors"
          >
            Start Practicing
          </Link>
        </div>
      </div>
    )
  }

  if (!reportCard) return null

  // Time display logic
  const hours = reportCard.topline.time_practiced_hours
  const timeDisplay = hours < 1
    ? `${Math.round(hours * 60)} min`
    : `${hours} hrs`

  const chartData = reportCard.chart_data.map(d => ({
    ...d,
    displayDate: (() => {
      const date = new Date(d.date + 'T00:00:00')
      return `${date.getDate()}/${date.getMonth() + 1}`
    })(),
  }))

  const hasChartData = reportCard.chart_data.some(d => d.correct > 0 || d.incorrect > 0)

  // Calculate total sentences for the last 7 days
  const totalSentences = reportCard.chart_data.reduce(
    (sum, d) => sum + d.correct + d.incorrect,
    0
  )

  const scores = reportCard.score_breakdown
  const hasScores = scores.grammar.score !== null || scores.usage.score !== null || scores.naturalness.score !== null

  const scoreCards = [
    {
      key: 'grammar',
      label: 'Grammar',
      detail: scores.grammar,
      tooltipText: 'Evaluates word order, grammatical particles, verb aspect markers, and measure words.',
      icon: (
        <svg className="w-6 h-6 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      key: 'usage',
      label: 'Usage',
      detail: scores.usage,
      tooltipText: 'Evaluates whether the vocabulary word is used with correct meaning, context, and collocations.',
      icon: (
        <svg className="w-6 h-6 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
    },
    {
      key: 'naturalness',
      label: 'Naturalness',
      detail: scores.naturalness,
      tooltipText: 'Evaluates how native-like the expression sounds, including idiomatic usage.',
      icon: (
        <svg className="w-6 h-6 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ]

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <svg className="w-8 h-8 text-sage" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <h1 className="text-2xl font-bold text-warm-black">Report Card</h1>
      </div>

      {/* Topline Metrics */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Time Practiced */}
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span className="text-sm text-warm-muted">Time Practiced</span>
          </div>
          <div className="text-3xl font-bold text-warm-black">{timeDisplay}</div>
        </div>

        {/* Sessions Completed */}
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span className="text-sm text-warm-muted">Sessions Completed</span>
          </div>
          <div className="text-3xl font-bold text-warm-black">{reportCard.topline.sessions_completed}</div>
        </div>

        {/* Words Practiced */}
        <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span className="text-sm text-warm-muted">Words Practiced</span>
          </div>
          <div className="text-3xl font-bold text-warm-black">{reportCard.topline.words_practiced}</div>
        </div>
      </div>

      {/* Daily Sentences Chart */}
      <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-warm-black">Daily Sentences (last 7 days)</h2>
          {hasChartData && (
            <span className="text-sm text-warm-muted bg-warm-offwhite px-3 py-1 rounded-full">
              {totalSentences} sentence{totalSentences !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {hasChartData ? (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <XAxis dataKey="displayDate" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="correct" stackId="a" fill="#22c55e" name="Correct" />
              <Bar dataKey="incorrect" stackId="a" fill="#ef4444" name="Incorrect" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[250px]">
            <p className="text-warm-muted">No practice data in the last 7 days</p>
          </div>
        )}
      </div>

      {/* Score Breakdown */}
      <div className="bg-white rounded-2xl shadow-sm border border-warm-gray p-6">
        <div className="flex items-center gap-4 mb-6 border-b border-warm-gray">
          <button
            onClick={() => setActiveTab('feedback')}
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'feedback'
                ? 'border-sage text-sage'
                : 'border-transparent text-warm-muted hover:text-warm-black'
            }`}
          >
            Teacher Feedback
          </button>
          <button
            onClick={() => setActiveTab('scores')}
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'scores'
                ? 'border-sage text-sage'
                : 'border-transparent text-warm-muted hover:text-warm-black'
            }`}
          >
            Score Breakdown
          </button>
        </div>

        {activeTab === 'feedback' && (
          <>
            {reportCard.teacher_feedback ? (
              <div className="flex gap-4">
                <img
                  src={laoshiLogo}
                  alt="Laoshi"
                  className="w-16 h-16 rounded-full object-cover flex-shrink-0"
                />
                <div className="flex-1">
                  <p className="text-warm-black italic leading-relaxed">
                    {reportCard.teacher_feedback}
                  </p>
                  <div className="flex items-center justify-end gap-2 mt-4">
                    <img src={seal} alt="Seal" className="w-10 h-10 object-contain" />
                    <span className="text-warm-muted font-medium">-- Laoshi</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-warm-muted italic">Complete a session to get Laoshi's feedback!</p>
            )}
          </>
        )}

        {activeTab === 'scores' && (
          <>
            {hasScores ? (
              <div className="grid grid-cols-3 gap-6">
                {scoreCards.map(({ key, label, detail, tooltipText, icon }) => (
                  <div key={key} className="border border-warm-gray rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-10 h-10 rounded-xl bg-sage-tint flex items-center justify-center">
                        {icon}
                      </div>
                      <button
                        onClick={() => toggleTooltip(key)}
                        className="w-6 h-6 rounded-full bg-warm-offwhite flex items-center justify-center text-warm-muted hover:text-warm-black hover:bg-warm-gray text-xs font-medium"
                        title={`About ${label}`}
                      >
                        i
                      </button>
                    </div>
                    {showTooltip[key] && (
                      <div className="mb-3 p-2 bg-sage-tint rounded-lg text-xs text-sage">
                        {tooltipText}
                      </div>
                    )}
                    <div className="text-2xl font-bold text-warm-black mb-1">
                      {detail.score !== null ? `${detail.score.toFixed(1)}/10` : '--/10'}
                    </div>
                    <div className="text-sm font-medium text-warm-black mb-2">{label}</div>
                    {detail.description && (
                      <p className="text-xs text-warm-muted">{detail.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-warm-muted italic">Complete a practice session to see your scores.</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default Progress
