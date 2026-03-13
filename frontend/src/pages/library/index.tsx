import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { deckApi, wordsApi } from '../../lib/api'
import type { DeckWithStats, Word } from '../../types/api'
import {
  Plus,
  Trash2,
  Upload,
  ArrowLeft,
  Check,
  Star,
  BookOpen,
} from 'lucide-react'

// Create Deck Modal
function CreateDeckModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean
  onClose: () => void
  onCreate: (name: string, description: string) => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim()) {
      onCreate(name.trim(), description.trim())
      setName('')
      setDescription('')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-stone-800 mb-4">Create New Deck</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., HSK 1 Vocabulary"
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={2}
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-stone-600 hover:text-stone-800 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-stone-300 font-medium"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Upload Words Modal
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
        <h3 className="text-lg font-semibold text-stone-800 mb-4">Upload Words</h3>
        <p className="text-sm text-stone-500 mb-4">
          Upload a CSV file with columns: word, pinyin, english
        </p>
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-stone-600 hover:text-stone-800 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-stone-300 font-medium"
            >
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Word status badge
function WordStatusBadge({ word }: { word: Word }) {
  if (word.is_mastered) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
        <Check className="w-3 h-3" />
        Mastered
      </span>
    )
  }
  if (word.next_review_date) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
        <BookOpen className="w-3 h-3" />
        In Review
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 bg-stone-100 text-stone-600 text-xs rounded-full">
      <Star className="w-3 h-3" />
      New
    </span>
  )
}

// Deck card component
function DeckCard({
  deck,
  isSelected,
  onClick,
  onDelete,
}: {
  deck: DeckWithStats
  isSelected: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
}) {
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border cursor-pointer transition-all ${
        isSelected
          ? 'border-primary-500 bg-primary-50'
          : 'border-stone-200 bg-white hover:border-primary-300 hover:bg-stone-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-stone-800 truncate">{deck.name}</h3>
          {deck.description && (
            <p className="text-sm text-stone-500 mt-1 line-clamp-1">{deck.description}</p>
          )}
          <p className="text-xs text-stone-400 mt-2">
            {deck.word_count || 0} words · {deck.mastered_count || 0} mastered
          </p>
        </div>
        <button
          onClick={onDelete}
          className="p-1 text-stone-400 hover:text-red-500 transition-colors"
          title="Delete deck"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// Word list component
function WordList({
  deckId,
  onMarkAsMastered,
}: {
  deckId: number
  onMarkAsMastered: (wordId: number, marked: boolean) => void
}) {
  const [words, setWords] = useState<Word[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    loadWords(1)
  }, [deckId])

  const loadWords = async (pageNum: number) => {
    try {
      const response = await wordsApi.getWords(deckId, pageNum)
      if (pageNum === 1) {
        setWords(response.data.data)
      } else {
        setWords((prev) => [...prev, ...response.data.data])
      }
      setHasMore(response.data.data.length === 20)
      setPage(pageNum)
    } catch (error) {
      console.error('Failed to load words:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsMastered = async (wordId: number, currentMarked: boolean) => {
    try {
      await wordsApi.markAsMastered(wordId, !currentMarked)
      onMarkAsMastered(wordId, !currentMarked)
      // Refresh word list
      loadWords(1)
    } catch (error) {
      console.error('Failed to mark word:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-pulse text-stone-400">Loading words...</div>
      </div>
    )
  }

  if (words.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-stone-500">No words in this deck yet</p>
        <p className="text-sm text-stone-400 mt-2">
          Upload a CSV file to add words
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {words.map((word) => (
        <div
          key={word.id}
          className="flex items-center justify-between p-3 bg-white rounded-lg border border-stone-200"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-stone-800">{word.word}</span>
              <span className="text-sm text-stone-500">{word.pinyin}</span>
              <WordStatusBadge word={word} />
            </div>
            <p className="text-sm text-stone-600 truncate">{word.meaning}</p>
          </div>
          <button
            onClick={() => handleMarkAsMastered(word.id, word.marked_as_known || false)}
            className={`ml-2 px-3 py-1 text-sm rounded-lg transition-colors ${
              word.marked_as_known
                ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
            }`}
            title={word.marked_as_known ? 'Unmark as mastered' : 'Mark as mastered'}
          >
            {word.marked_as_known ? (
              <span className="flex items-center gap-1">
                <Star className="w-3 h-3 fill-current" />
                Mastered
              </span>
            ) : (
              'Mark Mastered'
            )}
          </button>
        </div>
      ))}
      {hasMore && (
        <button
          onClick={() => loadWords(page + 1)}
          className="w-full py-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Load more...
        </button>
      )}
    </div>
  )
}

// Main Library component
export default function Library() {
  const { deckId } = useParams<{ deckId: string }>()
  const navigate = useNavigate()
  const [decks, setDecks] = useState<DeckWithStats[]>([])
  const [selectedDeck, setSelectedDeck] = useState<DeckWithStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)

  useEffect(() => {
    loadDecks()
  }, [])

  useEffect(() => {
    if (deckId && decks.length > 0) {
      const deck = decks.find((d) => d.id === parseInt(deckId))
      if (deck) {
        setSelectedDeck(deck)
      }
    }
  }, [deckId, decks])

  const loadDecks = async () => {
    try {
      const response = await deckApi.getDecks()
      setDecks(response.data.decks)
    } catch (error) {
      console.error('Failed to load decks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateDeck = async (name: string, description: string) => {
    try {
      const response = await deckApi.createDeck({ name, description })
      setDecks([...decks, response.data])
      setShowCreateModal(false)
      navigate(`/library/deck/${response.data.id}`)
    } catch (error) {
      console.error('Failed to create deck:', error)
      alert('Failed to create deck')
    }
  }

  const handleDeleteDeck = async (e: React.MouseEvent, deckId: number) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this deck? This action cannot be undone.')) {
      return
    }
    try {
      await deckApi.deleteDeck(deckId)
      setDecks(decks.filter((d) => d.id !== deckId))
      if (selectedDeck?.id === deckId) {
        setSelectedDeck(null)
        navigate('/library')
      }
    } catch (error) {
      console.error('Failed to delete deck:', error)
      alert('Failed to delete deck')
    }
  }

  const handleUploadWords = async (file: File) => {
    if (!selectedDeck) return
    try {
      await wordsApi.uploadWords(selectedDeck.id, file)
      setShowUploadModal(false)
      // Refresh decks to update word count
      loadDecks()
      alert('Words uploaded successfully!')
    } catch (error) {
      console.error('Failed to upload words:', error)
      alert('Failed to upload words')
    }
  }

  const handleMarkAsMastered = (_wordId: number, marked: boolean) => {
    // Update local deck stats
    if (selectedDeck) {
      const newMasteredCount = marked
        ? (selectedDeck.mastered_count || 0) + 1
        : Math.max(0, (selectedDeck.mastered_count || 0) - 1)
      setSelectedDeck({ ...selectedDeck, mastered_count: newMasteredCount })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="animate-pulse text-stone-400">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Left sidebar - Deck list */}
      <div className="w-80 bg-stone-50 border-r border-stone-200 flex flex-col">
        <div className="p-4 border-b border-stone-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-stone-800">Library</h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
              title="Create new deck"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {decks.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-stone-500 mb-4">No decks yet</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                Create your first deck
              </button>
            </div>
          ) : (
            decks.map((deck) => (
              <DeckCard
                key={deck.id}
                deck={deck}
                isSelected={selectedDeck?.id === deck.id}
                onClick={() => navigate(`/library/deck/${deck.id}`)}
                onDelete={(e) => handleDeleteDeck(e, deck.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right panel - Deck details */}
      <div className="flex-1 overflow-y-auto p-6">
        {selectedDeck ? (
          <div>
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <button
                  onClick={() => navigate('/library')}
                  className="flex items-center gap-1 text-sm text-stone-500 hover:text-stone-700 mb-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to Library
                </button>
                <h1 className="text-2xl font-bold text-stone-800">{selectedDeck.name}</h1>
                {selectedDeck.description && (
                  <p className="text-stone-500 mt-1">{selectedDeck.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                >
                  <Upload className="w-4 h-4" />
                  Upload Words
                </button>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white p-4 rounded-lg border border-stone-200">
                <p className="text-sm text-stone-500">Total Words</p>
                <p className="text-2xl font-bold text-stone-800">{selectedDeck.word_count || 0}</p>
              </div>
              <div className="bg-white p-4 rounded-lg border border-stone-200">
                <p className="text-sm text-stone-500">Mastered</p>
                <p className="text-2xl font-bold text-green-600">{selectedDeck.mastered_count || 0}</p>
              </div>
              <div className="bg-white p-4 rounded-lg border border-stone-200">
                <p className="text-sm text-stone-500">Mastery</p>
                <p className="text-2xl font-bold text-primary-600">
                  {selectedDeck.mastery_percentage}%
                </p>
              </div>
            </div>

            {/* Words list */}
            <div>
              <h3 className="text-lg font-semibold text-stone-800 mb-4">Words</h3>
              <WordList
                deckId={selectedDeck.id}
                onMarkAsMastered={handleMarkAsMastered}
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <BookOpen className="w-16 h-16 text-stone-300 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-stone-700 mb-2">Select a Deck</h2>
              <p className="text-stone-500">
                Choose a deck from the sidebar to view and manage its words
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateDeckModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateDeck}
      />
      <UploadWordsModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUploadWords}
      />
    </div>
  )
}
