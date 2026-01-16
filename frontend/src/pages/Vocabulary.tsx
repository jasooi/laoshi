import { useState, useEffect, useRef } from 'react'

interface VocabularyWord {
  id: string
  word: string
  pinyin: string
  definition: string
  sourceName: string
}

const Vocabulary = () => {
  const [words, setWords] = useState<VocabularyWord[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'pinyin' | 'word'>('pinyin')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [sourceName, setSourceName] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch vocabulary from API
  useEffect(() => {
    fetchVocabulary()
  }, [])

  const fetchVocabulary = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/vocabulary')
      if (response.ok) {
        const data = await response.json()
        setWords(data)
      } else {
        console.log('API not available, using empty data')
        setWords([])
      }
    } catch (error) {
      console.error('Error fetching vocabulary:', error)
      setWords([])
    } finally {
      setLoading(false)
    }
  }

  // Filter and sort words
  const filteredWords = words
    .filter(word =>
      word.word.toLowerCase().includes(searchQuery.toLowerCase()) ||
      word.pinyin.toLowerCase().includes(searchQuery.toLowerCase()) ||
      word.definition.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'pinyin') {
        return a.pinyin.localeCompare(b.pinyin)
      }
      return a.word.localeCompare(b.word)
    })

  // Handle file selection
  const handleFileSelect = (file: File) => {
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      alert('Only .csv files are accepted')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('Maximum file size is 10 MB')
      return
    }
    setSelectedFile(file)
  }

  // Handle drag and drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile || !sourceName.trim()) {
      alert('Please select a file and enter a source name')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('sourceName', sourceName)

      const response = await fetch('/api/vocabulary/import', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Import successful:', result)
        setShowUploadModal(false)
        setSelectedFile(null)
        setSourceName('')
        fetchVocabulary()
      } else {
        const error = await response.json()
        alert(`Import failed: ${error.message || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error uploading file:', error)
      alert('Failed to upload file. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  // Handle delete word
  const handleDelete = async (wordId: string) => {
    if (!confirm('Are you sure you want to delete this word?')) return

    try {
      const response = await fetch(`/api/vocabulary/${wordId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setWords(words.filter(w => w.id !== wordId))
      } else {
        alert('Failed to delete word')
      }
    } catch (error) {
      console.error('Error deleting word:', error)
      alert('Failed to delete word')
    }
  }

  // Handle edit word (placeholder - could open a modal)
  const handleEdit = (wordId: string) => {
    console.log('Edit word:', wordId)
    // TODO: Implement edit modal
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Vocabulary</h1>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium py-2.5 px-5 rounded-full transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import from file
        </button>
      </div>

      {/* Main Content Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
        {/* Search and Sort Bar */}
        <div className="p-4 border-b border-gray-100 flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <svg className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search words..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setSortBy(sortBy === 'pinyin' ? 'word' : 'pinyin')}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
            <span className="text-gray-700">Sort by {sortBy === 'pinyin' ? 'Pinyin' : 'Word'}</span>
          </button>
        </div>

        {/* Table or Empty State */}
        {loading ? (
          <div className="p-16 text-center text-gray-500">Loading...</div>
        ) : words.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-purple-100 flex items-center justify-center">
              <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <p className="text-gray-600 text-lg">
              No words yet... Let's start by clicking <span className="text-purple-600 font-medium">Import from file</span> to add some words!
            </p>
          </div>
        ) : (
          <>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">#</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">中文</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Pinyin</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Meaning</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Source Name</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredWords.map((word, index) => (
                    <tr key={word.id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-3 text-sm text-gray-500">{index + 1}</td>
                      <td className="px-4 py-3 text-base font-medium text-gray-900">{word.word}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{word.pinyin}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{word.definition}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{word.sourceName}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleEdit(word.id)}
                            className="p-2 text-gray-400 hover:text-purple-600 transition-colors"
                            title="Edit"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDelete(word.id)}
                            className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                            title="Delete"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
              Showing {filteredWords.length} of {words.length} words
            </div>
          </>
        )}
      </div>

      {/* Upload File Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            {/* Modal Header */}
            <div className="p-6 pb-4">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-xl font-semibold text-gray-900">Upload file</h2>
                <button
                  onClick={() => {
                    setShowUploadModal(false)
                    setSelectedFile(null)
                    setSourceName('')
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="text-sm text-gray-500">Only .csv files are accepted</p>
            </div>

            {/* Upload Area */}
            <div className="px-6">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  isDragging
                    ? 'border-purple-500 bg-purple-50'
                    : selectedFile
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                {selectedFile ? (
                  <>
                    <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-purple-100 flex items-center justify-center">
                      <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <p className="text-purple-600 font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </>
                ) : (
                  <>
                    <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-purple-100 flex items-center justify-center">
                      <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                    </div>
                    <p>
                      <span className="text-purple-600 font-medium">Click to Upload</span>
                      <span className="text-gray-600"> or drag and drop</span>
                    </p>
                    <p className="text-sm text-gray-400 mt-1">Maximum file size 10 MB</p>
                  </>
                )}
              </div>
            </div>

            {/* Source Name Input */}
            <div className="px-6 py-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name your source file
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Words from this file will be tagged with the following name for easy identification
              </p>
              <input
                type="text"
                placeholder="e.g., Kitchen Vocabulary"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* Modal Footer */}
            <div className="px-6 pb-6 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setSelectedFile(null)
                  setSourceName('')
                }}
                className="px-5 py-2.5 text-gray-700 font-medium border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || !sourceName.trim() || uploading}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white font-medium rounded-full transition-colors"
              >
                {uploading ? 'Uploading...' : 'Attach File'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Vocabulary
