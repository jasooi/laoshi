const Files = () => {
  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          <h1 className="text-3xl font-semibold text-gray-900">Files</h1>
        </div>
      </div>

      {/* Main Content Card - Empty State */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-16 flex flex-col items-center justify-center min-h-[500px]">
        {/* Icon */}
        <div className="w-32 h-32 rounded-full bg-purple-100 flex items-center justify-center mb-6">
          <svg className="w-16 h-16 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
        </div>

        {/* Message */}
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Import Vocabulary</h2>
        <p className="text-gray-500 text-lg">CSV import coming soon...</p>
      </div>
    </div>
  )
}

export default Files

