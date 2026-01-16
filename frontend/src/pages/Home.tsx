import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const Home = () => {
  const [totalWords, setTotalWords] = useState(0)
  const [wordsToday, setWordsToday] = useState(0)
  const [masteryProgress, setMasteryProgress] = useState(0)
  const [wordsWaiting, setWordsWaiting] = useState(0)
  const [loading, setLoading] = useState(true)

  // Fetch stats from API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Fetch vocabulary count
        const vocabResponse = await fetch('/api/vocabulary')
        if (vocabResponse.ok) {
          const vocabData = await vocabResponse.json()
          setTotalWords(vocabData.length || 0)
          setWordsWaiting(vocabData.length || 0) // For now, all words are waiting
        }

        // Fetch progress stats
        const progressResponse = await fetch('/api/progress/stats')
        if (progressResponse.ok) {
          const progressData = await progressResponse.json()
          setWordsToday(progressData.wordsToday || 0)
          setMasteryProgress(progressData.masteryProgress || 0)
        }
      } catch (error) {
        console.error('Error fetching stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  const hasWords = totalWords > 0

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header with Greeting and Total Word Count */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <span className="text-3xl">☀️</span>
          <h1 className="text-3xl font-semibold text-gray-900">{getGreeting()}</h1>
        </div>
        <div className="text-gray-500">
          Total: <span className="text-purple-600 font-medium">{totalWords} words</span>
        </div>
      </div>

      {/* Main Content Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-8">
        {/* Status Message */}
        <div className="flex items-center gap-2 mb-8">
          <span className="text-2xl">🎓</span>
          <h2 className="text-xl text-purple-600 font-medium">
            Laoshi is waiting for you to start practicing
          </h2>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-3 gap-6 mb-4">
          {/* Today's Progress */}
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-2xl bg-purple-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" strokeWidth="2" />
                  <circle cx="12" cy="12" r="3" fill="currentColor" />
                </svg>
              </div>
              <span className="text-gray-700 font-medium">Today's Progress</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{wordsToday}</div>
            <div className="text-sm text-gray-500 mb-2">words practiced</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-purple-500 h-2 rounded-full" style={{ width: '0%' }}></div>
            </div>
          </div>

          {/* Mastery Level */}
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <span className="text-gray-700 font-medium">Mastery Level</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{masteryProgress}%</div>
            <div className="text-sm text-gray-500 mb-2">overall progress</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${masteryProgress}%` }}></div>
            </div>
          </div>

          {/* Ready to Review */}
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-2xl bg-pink-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <span className="text-gray-700 font-medium">Ready to Review</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{wordsWaiting}</div>
            <div className="text-sm text-gray-500">words waiting</div>
          </div>
        </div>
      </div>

      {/* Start Practice Button */}
      <div className="flex flex-col items-center">
        {hasWords ? (
          <>
            <Link
              to="/practice"
              className="bg-gradient-to-r from-pink-500 via-purple-500 to-blue-500 hover:from-pink-600 hover:via-purple-600 hover:to-blue-600 text-white font-semibold py-5 px-12 rounded-full text-lg shadow-lg flex items-center gap-3 mb-3 transition-all transform hover:scale-105"
            >
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />
              </svg>
              Start Practicing
            </Link>
            <p className="text-gray-500 text-sm">
              Begin your learning journey and master new vocabulary
            </p>
          </>
        ) : (
          <>
            <div className="bg-gray-300 text-gray-500 font-semibold py-5 px-12 rounded-full text-lg shadow-sm flex items-center gap-3 mb-3 cursor-not-allowed">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />
              </svg>
              Start Practicing
            </div>
            <Link
              to="/vocabulary"
              className="text-purple-600 hover:text-purple-700 font-medium text-sm"
            >
              Import words to get started →
            </Link>
          </>
        )}
      </div>
    </div>
  )
}

export default Home
