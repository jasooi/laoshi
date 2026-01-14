const Home = () => {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Progress Summary */}
      <div className="mb-8">
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Words Practiced Today</p>
            <p className="text-2xl font-semibold text-gray-900">0</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Mastery Progress</p>
            <p className="text-2xl font-semibold text-gray-900">0%</p>
          </div>
        </div>
      </div>

      {/* Start Practice Button */}
      <div className="mb-8">
        <button className="w-full bg-primary text-white px-6 py-4 rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-sm">
          Start Practice
        </button>
      </div>

      {/* Get Started Section (for new users) */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Get started</h2>
          <button className="text-sm text-gray-500 hover:text-gray-700">
            Don't show again
          </button>
        </div>
        <ul className="space-y-3">
          <li className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-gray-300 rounded"></div>
            <span className="text-gray-700">Import vocabulary from CSV</span>
          </li>
          <li className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-gray-300 rounded"></div>
            <span className="text-gray-700">Start practicing</span>
          </li>
        </ul>
      </div>
    </div>
  )
}

export default Home

