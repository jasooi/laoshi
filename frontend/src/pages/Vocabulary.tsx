import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'
import { Word, PaginationMeta } from '../types/api'
import Pagination from '../components/Pagination'
import UploadModal from './vocabulary/UploadModal'
import EditWordModal from './vocabulary/EditWordModal'

const Vocabulary = () => {
  const [words, setWords] = useState<Word[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sortBy, setSortBy] = useState<'pinyin' | 'word'>('pinyin')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [pagination, setPagination] = useState<PaginationMeta | null>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadWarning, setUploadWarning] = useState<string | null>(null)
  const [editingWord, setEditingWord] = useState<Word | null>(null)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Fetch vocabulary from API
  const fetchVocabulary = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get('/api/words', {
        params: {
          page,
          per_page: perPage,
          search: debouncedSearch || undefined,
          sort_by: sortBy,
        }
      })
      setWords(response.data.data)
      setPagination(response.data.pagination)
    } catch (error) {
      console.error('Error fetching vocabulary:', error)
      setWords([])
      setPagination(null)
    } finally {
      setLoading(false)
    }
  }, [page, perPage, debouncedSearch, sortBy])

  useEffect(() => {
    fetchVocabulary()
  }, [fetchVocabulary])

  // Handle sort toggle
  const handleSortToggle = () => {
    setSortBy(sortBy === 'pinyin' ? 'word' : 'pinyin')
    setPage(1)
  }

  // Handle delete word (non-optimistic)
  const handleDelete = async (wordId: number) => {
    if (!confirm('Are you sure you want to delete this word?')) return

    try {
      await api.delete(`/api/words/${wordId}`)
      fetchVocabulary()
    } catch (error) {
      console.error('Error deleting word:', error)
      alert('Failed to delete word')
    }
  }

  // Callbacks for modals
  const handleUploadSuccess = () => {
    setShowUploadModal(false)
    setPage(1)
    fetchVocabulary()
  }

  const handleEditSave = () => {
    setEditingWord(null)
    fetchVocabulary()
  }

  const handlePerPageChange = (newPerPage: number) => {
    setPerPage(newPerPage)
    setPage(1)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Fixed header */}
      <div className="flex-shrink-0 px-8 pt-8">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold text-gray-900">Vocabulary</h1>
          <button
            onClick={() => { setShowUploadModal(true); setUploadWarning(null) }}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium py-2.5 px-5 rounded-full transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import from file
          </button>
        </div>

        {/* Upload Warning Banner */}
        {uploadWarning && (
          <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
            <p className="text-sm text-amber-700">{uploadWarning}</p>
            <button onClick={() => setUploadWarning(null)} className="text-amber-400 hover:text-amber-600 ml-3">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Card with table */}
      <div className="flex-1 flex flex-col overflow-hidden mx-8 mb-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        {/* Search and Sort Bar */}
        <div className="flex-shrink-0 p-4 border-b border-gray-100 flex items-center justify-between gap-4">
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
            onClick={handleSortToggle}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
            <span className="text-gray-700">Sort by {sortBy === 'pinyin' ? 'Pinyin' : 'Word'}</span>
          </button>
        </div>

        {/* Table or Empty/Loading State */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">Loading...</div>
        ) : words.length === 0 && !debouncedSearch ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-purple-100 flex items-center justify-center">
                <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <p className="text-gray-600 text-lg">
                No words yet... Let's start by clicking <span className="text-purple-600 font-medium">Import from file</span> to add some words!
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Scrollable table */}
            <div className="flex-1 overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-white border-b border-gray-100 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">#</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">中文</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Pinyin</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Meaning</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Source Name</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {words.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        No words match your search.
                      </td>
                    </tr>
                  ) : (
                    words.map((word, index) => (
                      <tr key={word.id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-4 py-3 text-sm text-gray-500">{(page - 1) * perPage + index + 1}</td>
                        <td className="px-4 py-3 text-base font-medium text-gray-900">{word.word}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{word.pinyin}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{word.meaning}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{word.source_name}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setEditingWord(word)}
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
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            {pagination && (
              <div className="flex-shrink-0 border-t border-gray-100">
                <Pagination
                  page={page}
                  totalPages={pagination.total_pages}
                  total={pagination.total}
                  perPage={perPage}
                  hasNext={pagination.has_next}
                  hasPrev={pagination.has_prev}
                  onPageChange={setPage}
                  onPerPageChange={handlePerPageChange}
                />
              </div>
            )}
          </>
        )}
      </div>

      {/* Modals */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={handleUploadSuccess}
        onUploadWarning={setUploadWarning}
      />
      <EditWordModal
        word={editingWord}
        onClose={() => setEditingWord(null)}
        onSaveSuccess={handleEditSave}
      />
    </div>
  )
}

export default Vocabulary
