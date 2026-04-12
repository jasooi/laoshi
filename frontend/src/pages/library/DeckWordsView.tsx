import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { deckApi, wordsApi } from '../../lib/api'
import type { DeckWithStats, Word, PaginationMeta } from '../../types/api'
import {
  ArrowLeft,
  Upload,
  Search,
  ArrowUpDown,
  Pencil,
  Trash2,
} from 'lucide-react'

// --- Edit Word Modal ---

function EditWordModal({
  word,
  onClose,
  onSave,
}: {
  word: Word
  onClose: () => void
  onSave: (data: { word: string; pinyin: string; meaning: string; notes: string }) => void
}) {
  const [form, setForm] = useState({
    word: word.word,
    pinyin: word.pinyin,
    meaning: word.meaning,
    notes: word.notes || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (form.word.trim() && form.pinyin.trim() && form.meaning.trim()) {
      onSave({
        word: form.word.trim(),
        pinyin: form.pinyin.trim(),
        meaning: form.meaning.trim(),
        notes: form.notes.trim(),
      })
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-warm-black mb-4">Edit Word</h3>
        <form onSubmit={handleSubmit}>
          <div className="space-y-3 mb-6">
            <div>
              <label className="block text-sm font-medium text-warm-black mb-1">Word *</label>
              <input
                type="text"
                value={form.word}
                onChange={(e) => setForm({ ...form, word: e.target.value })}
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-warm-black mb-1">Pinyin *</label>
              <input
                type="text"
                value={form.pinyin}
                onChange={(e) => setForm({ ...form, pinyin: e.target.value })}
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-warm-black mb-1">Meaning *</label>
              <input
                type="text"
                value={form.meaning}
                onChange={(e) => setForm({ ...form, meaning: e.target.value })}
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-warm-black mb-1">Notes</label>
              <input
                type="text"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Optional notes..."
                className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-warm-muted hover:text-warm-black font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!form.word.trim() || !form.pinyin.trim() || !form.meaning.trim()}
              className="px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 disabled:bg-warm-gray font-medium"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Upload Words Modal ---

function UploadWordsModal({
  isOpen,
  onClose,
  onUpload,
}: {
  isOpen: boolean
  onClose: () => void
  onUpload: (file: File) => void
}) {
  const [file, setFile] = useState<File | null>(null)

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (file) {
      onUpload(file)
      setFile(null)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-warm-black mb-4">Upload Words</h3>
        <p className="text-sm text-warm-muted mb-4">
          Upload a CSV file with columns: word, pinyin, and meaning (or english)
        </p>
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-warm-muted hover:text-warm-black font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file}
              className="px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 disabled:bg-warm-gray font-medium"
            >
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Delete Confirmation Modal ---

function DeleteConfirmModal({
  word,
  onClose,
  onConfirm,
}: {
  word: Word
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h3 className="text-lg font-semibold text-warm-black mb-2">Delete Word</h3>
        <p className="text-warm-muted mb-6">
          Delete <strong>{word.word}</strong> ({word.meaning})? This cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-warm-muted hover:text-warm-black font-medium">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-coral text-white rounded-lg hover:bg-coral/90 font-medium"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

// --- Pagination ---

function Pagination({
  pagination,
  perPage,
  onPageChange,
  onPerPageChange,
}: {
  pagination: PaginationMeta
  perPage: number
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
}) {
  const { page, total, total_pages, has_prev, has_next } = pagination
  const start = (page - 1) * perPage + 1
  const end = Math.min(page * perPage, total)

  const pages: (number | '...')[] = []
  if (total_pages <= 7) {
    for (let i = 1; i <= total_pages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (page > 3) pages.push('...')
    for (let i = Math.max(2, page - 1); i <= Math.min(total_pages - 1, page + 1); i++) {
      pages.push(i)
    }
    if (page < total_pages - 2) pages.push('...')
    pages.push(total_pages)
  }

  return (
    <div className="flex items-center justify-between mt-4 text-sm">
      <span className="text-sage">
        Showing {start}–{end} of {total} words
      </span>
      <div className="flex items-center gap-1">
        <button
          disabled={!has_prev}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-1 rounded text-warm-muted hover:text-warm-black disabled:opacity-30"
        >
          &lt;
        </button>
        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`dots-${i}`} className="px-2 py-1 text-warm-muted">...</span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`px-2.5 py-1 rounded font-medium ${
                p === page
                  ? 'bg-sage text-white'
                  : 'text-warm-muted hover:text-warm-black hover:bg-warm-gray/50'
              }`}
            >
              {p}
            </button>
          )
        )}
        <button
          disabled={!has_next}
          onClick={() => onPageChange(page + 1)}
          className="px-2 py-1 rounded text-warm-muted hover:text-warm-black disabled:opacity-30"
        >
          &gt;
        </button>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-warm-muted">Per page:</span>
        <select
          value={perPage}
          onChange={(e) => onPerPageChange(Number(e.target.value))}
          className="px-2 py-1 border border-warm-gray rounded-lg text-warm-black focus:ring-1 focus:ring-sage"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
    </div>
  )
}

// --- Words Table ---

function WordsTable({
  deckId,
  refreshKey,
  onStatsChanged,
}: {
  deckId: number
  refreshKey: number
  onStatsChanged: () => void
}) {
  const [words, setWords] = useState<Word[]>([])
  const [pagination, setPagination] = useState<PaginationMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sortBy, setSortBy] = useState('pinyin')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [editingWord, setEditingWord] = useState<Word | null>(null)
  const [deletingWord, setDeletingWord] = useState<Word | null>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    loadWords()
  }, [deckId, page, perPage, sortBy, sortOrder, refreshKey, debouncedSearch])

  // Debounce search input
  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => {
      setPage(1)
      setDebouncedSearch(search)
    }, 300)
    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current)
    }
  }, [search])

  const loadWords = async () => {
    try {
      const response = await deckApi.getDeckWords(deckId, {
        page,
        per_page: perPage,
        search: debouncedSearch.trim(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      setWords(response.data.data)
      setPagination(response.data.pagination)
    } catch (error) {
      console.error('Failed to load words:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = () => {
    if (sortBy === 'pinyin' && sortOrder === 'asc') {
      setSortOrder('desc')
    } else if (sortBy === 'pinyin' && sortOrder === 'desc') {
      setSortBy('meaning')
      setSortOrder('asc')
    } else if (sortBy === 'meaning' && sortOrder === 'asc') {
      setSortOrder('desc')
    } else {
      setSortBy('pinyin')
      setSortOrder('asc')
    }
  }

  const getSortLabel = () => {
    const col = sortBy === 'pinyin' ? 'Pinyin' : 'Meaning'
    const dir = sortOrder === 'asc' ? '↑' : '↓'
    return `Sort by ${col} ${dir}`
  }

  const handleEditSave = async (data: { word: string; pinyin: string; meaning: string; notes: string }) => {
    if (!editingWord) return
    try {
      await wordsApi.updateWord(editingWord.id, data)
      setEditingWord(null)
      loadWords()
    } catch (error) {
      console.error('Failed to update word:', error)
      alert('Failed to update word')
    }
  }

  const handleDelete = async () => {
    if (!deletingWord) return
    try {
      await wordsApi.deleteWord(deletingWord.id)
      setDeletingWord(null)
      loadWords()
      onStatsChanged()
    } catch (error) {
      console.error('Failed to delete word:', error)
      alert('Failed to delete word')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-pulse text-warm-muted">Loading words...</div>
      </div>
    )
  }

  return (
    <div>
      {/* Search + Sort bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-muted" />
          <input
            type="text"
            placeholder="Search words..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-3 py-2.5 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent bg-white"
          />
        </div>
        <button
          onClick={handleSort}
          className="flex items-center gap-2 px-4 py-2.5 border border-warm-gray rounded-lg text-warm-black hover:bg-warm-gray/30 transition-colors whitespace-nowrap"
        >
          <ArrowUpDown className="w-4 h-4" />
          {getSortLabel()}
        </button>
      </div>

      {words.length === 0 && !debouncedSearch ? (
        <div className="text-center py-12">
          <p className="text-warm-muted">No words in this deck yet</p>
          <p className="text-sm text-warm-muted/70 mt-2">
            Upload a CSV file to add words
          </p>
        </div>
      ) : words.length === 0 && debouncedSearch ? (
        <div className="text-center py-12">
          <p className="text-warm-muted">No words matching "{debouncedSearch}"</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="bg-white rounded-lg border border-warm-gray overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-warm-gray">
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted w-12">#</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted">中文</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted">Pinyin</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted">Meaning</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted">Notes</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-warm-muted w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {words.map((word, index) => (
                    <tr key={word.id} className="border-b border-warm-gray/50 last:border-b-0 hover:bg-warm-offwhite/50">
                      <td className="px-4 py-3 text-sm text-warm-muted">
                        {pagination ? (pagination.page - 1) * perPage + index + 1 : index + 1}
                      </td>
                      <td className="px-4 py-3 font-medium text-warm-black text-lg">{word.word}</td>
                      <td className="px-4 py-3 text-warm-black">{word.pinyin}</td>
                      <td className="px-4 py-3 text-warm-black">{word.meaning}</td>
                      <td className="px-4 py-3 text-warm-muted text-sm">{word.notes || '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setEditingWord(word)}
                            className="p-1.5 text-warm-muted hover:text-sage transition-colors"
                            title="Edit"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeletingWord(word)}
                            className="p-1.5 text-warm-muted hover:text-coral transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {pagination && (
            <Pagination
              pagination={pagination}
              perPage={perPage}
              onPageChange={(p) => setPage(p)}
              onPerPageChange={(pp) => {
                setPerPage(pp)
                setPage(1)
              }}
            />
          )}
        </>
      )}

      {/* Edit modal */}
      {editingWord && (
        <EditWordModal
          word={editingWord}
          onClose={() => setEditingWord(null)}
          onSave={handleEditSave}
        />
      )}

      {/* Delete confirmation */}
      {deletingWord && (
        <DeleteConfirmModal
          word={deletingWord}
          onClose={() => setDeletingWord(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}

// --- Main DeckWordsView ---

export default function DeckWordsView({ onDeckDeleted }: { onDeckDeleted?: () => void }) {
  const { deckId } = useParams<{ deckId: string }>()
  const navigate = useNavigate()
  const [deck, setDeck] = useState<DeckWithStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (deckId) {
      loadDeck(parseInt(deckId))
    }
  }, [deckId])

  const loadDeck = async (id: number) => {
    try {
      const response = await deckApi.getDeck(id)
      setDeck(response.data)
    } catch (error) {
      console.error('Failed to load deck:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadWords = async (file: File) => {
    if (!deck) return
    try {
      await wordsApi.uploadWords(deck.id, file)
      setShowUploadModal(false)
      loadDeck(deck.id)
      setRefreshKey((k) => k + 1)
      onDeckDeleted?.()
    } catch (error) {
      console.error('Failed to upload words:', error)
      alert('Failed to upload words')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="animate-pulse text-warm-muted">Loading...</div>
      </div>
    )
  }

  if (!deck) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-warm-black mb-2">Deck not found</h2>
          <button
            onClick={() => navigate('/library')}
            className="text-sage hover:text-sage/80 font-medium"
          >
            Back to Library
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto bg-warm-offwhite">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <button
              onClick={() => navigate('/library')}
              className="flex items-center gap-1 text-sm text-warm-muted hover:text-warm-black mb-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Library
            </button>
            <h1 className="text-2xl font-bold text-warm-black">{deck.name}</h1>
            {deck.description && (
              <p className="text-warm-muted mt-1">{deck.description}</p>
            )}
          </div>
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 transition-colors"
          >
            <Upload className="w-4 h-4" />
            Upload Words
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg border border-warm-gray">
            <p className="text-sm text-warm-muted">Total Words</p>
            <p className="text-2xl font-bold text-warm-black">{deck.word_count || 0}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-warm-gray">
            <p className="text-sm text-warm-muted">Mastered</p>
            <p className="text-2xl font-bold text-sage">{deck.mastered_count || 0}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-warm-gray">
            <p className="text-sm text-warm-muted">Mastery</p>
            <p className="text-2xl font-bold text-sage">
              {deck.mastery_percentage}%
            </p>
          </div>
        </div>

        {/* Words table */}
        <WordsTable
          deckId={deck.id}
          refreshKey={refreshKey}
          onStatsChanged={() => loadDeck(deck.id)}
        />
      </div>

      {/* Upload Modal */}
      <UploadWordsModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUploadWords}
      />
    </div>
  )
}
