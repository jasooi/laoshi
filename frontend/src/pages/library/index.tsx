import { useEffect, useState, useRef } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import Papa from 'papaparse'
import { deckApi } from '../../lib/api'
import type { DeckWithStats } from '../../types/api'
import CombineDecksModal from './CombineDecksModal'
import DeckWordsView from './DeckWordsView'
import ButtonSpinner from '../../components/ButtonSpinner'
import {
  Plus,
  Trash2,
  Upload,
  BookOpen,
  MoreVertical,
  Pencil,
  FolderPlus,
  Layers,
  ChevronDown,
} from 'lucide-react'

// --- Create Menu Dropdown ---

function CreateMenuDropdown({
  onCreateDeck,
  onUploadCSV,
  onCombineDecks,
}: {
  onCreateDeck: () => void
  onUploadCSV: () => void
  onCombineDecks: () => void
}) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-4 py-2.5 text-white bg-sage hover:bg-sage/90 rounded-lg transition-colors font-medium"
      >
        <Plus className="w-5 h-5" />
        Create New Deck
        <ChevronDown className="w-4 h-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-warm-gray py-1 z-10">
          <button
            onClick={() => {
              setOpen(false)
              onCreateDeck()
            }}
            className="w-full text-left px-3 py-2 text-sm text-warm-black hover:bg-warm-offwhite flex items-center gap-2"
          >
            <FolderPlus className="w-4 h-4" />
            Create Empty Deck
          </button>
          <button
            onClick={() => {
              setOpen(false)
              onUploadCSV()
            }}
            className="w-full text-left px-3 py-2 text-sm text-warm-black hover:bg-warm-offwhite flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Upload CSV
          </button>
          <button
            onClick={() => {
              setOpen(false)
              onCombineDecks()
            }}
            className="w-full text-left px-3 py-2 text-sm text-warm-black hover:bg-warm-offwhite flex items-center gap-2"
          >
            <Layers className="w-4 h-4" />
            Combine Decks
          </button>
        </div>
      )}
    </div>
  )
}

// --- Helpers ---

function getRecencyStyle(lastPracticedAt: string | null) {
  if (!lastPracticedAt) {
    return {
      border: 'border-l-neutral',
      badgeBg: 'bg-neutral-tint',
      badgeText: 'text-neutral',
      progressFill: 'bg-neutral',
      progressTrack: 'bg-neutral-tint',
    }
  }

  const hours = (Date.now() - new Date(lastPracticedAt).getTime()) / 3_600_000

  if (hours < 48) {
    return {
      border: 'border-l-sage',
      badgeBg: 'bg-sage-tint',
      badgeText: 'text-sage',
      progressFill: 'bg-sage',
      progressTrack: 'bg-sage-tint',
    }
  }
  if (hours < 120) {
    return {
      border: 'border-l-amber',
      badgeBg: 'bg-amber-tint',
      badgeText: 'text-amber',
      progressFill: 'bg-amber',
      progressTrack: 'bg-amber-tint',
    }
  }
  return {
    border: 'border-l-coral',
    badgeBg: 'bg-coral-tint',
    badgeText: 'text-coral',
    progressFill: 'bg-coral',
    progressTrack: 'bg-coral-tint',
  }
}

function getGrowthEmoji(masteryPercentage: number): string {
  if (masteryPercentage < 25) return '🌱'
  if (masteryPercentage < 75) return '🌿'
  return '🌸'
}

function formatRecency(dateString: string | null): string {
  if (!dateString) return 'Never'

  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (seconds < 60) return 'Just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days} days ago`
  return date.toLocaleDateString()
}

// --- Create Deck Modal ---

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
        <h3 className="text-lg font-semibold text-warm-black mb-4">Create New Deck</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., HSK 1 Vocabulary"
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium text-warm-black mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent resize-none"
              rows={2}
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
              disabled={!name.trim()}
              className="px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 disabled:bg-warm-gray font-medium"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Create Deck from CSV Modal ---

function CreateDeckCSVModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean
  onClose: () => void
  onCreate: (name: string, description: string, words: { word: string; pinyin: string; meaning: string }[]) => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleClose = () => {
    setName('')
    setDescription('')
    setFile(null)
    setError(null)
    onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !file) return

    setUploading(true)
    setError(null)

    try {
      const parseResult = await new Promise<Papa.ParseResult<Record<string, string>>>((resolve, reject) => {
        Papa.parse<Record<string, string>>(file, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => resolve(results),
          error: (err: Error) => reject(err),
        })
      })

      const headers = parseResult.meta.fields?.map(f => f.trim().toLowerCase()) || []

      // Accept either "meaning" or "english" as the third column
      const hasMeaning = headers.includes('meaning')
      const hasEnglish = headers.includes('english')

      if (!headers.includes('word') || !headers.includes('pinyin') || (!hasMeaning && !hasEnglish)) {
        setError('CSV must have columns: "word", "pinyin", and "meaning" (or "english").')
        return
      }

      if (parseResult.data.length === 0) {
        setError('CSV file contains no data rows.')
        return
      }

      // Build field mapping (handle original casing)
      const fieldMap: Record<string, string> = {}
      parseResult.meta.fields?.forEach(f => {
        fieldMap[f.trim().toLowerCase()] = f
      })

      const meaningKey = hasMeaning ? 'meaning' : 'english'

      const allRows = parseResult.data.map(row => ({
        word: (row[fieldMap['word']] || '').trim(),
        pinyin: (row[fieldMap['pinyin']] || '').trim(),
        meaning: (row[fieldMap[meaningKey]] || '').trim(),
      }))

      const validRows = allRows.filter(w => w.word && w.pinyin && w.meaning)
      const skippedCount = allRows.length - validRows.length

      if (validRows.length === 0) {
        setError('All rows have empty required fields (word, pinyin, or meaning/english).')
        return
      }

      onCreate(name.trim(), description.trim(), validRows)

      if (skippedCount > 0) {
        alert(`${skippedCount} row(s) were skipped due to missing data.`)
      }

      setName('')
      setDescription('')
      setFile(null)
      setError(null)
    } catch {
      setError('Failed to parse CSV file. Please check the format.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-warm-black mb-1">Create New Deck</h3>
        <p className="text-sm text-warm-muted mb-4">
          Upload a CSV with columns: word, pinyin, and meaning (or english)
        </p>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., HSK 1 Vocabulary"
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
              autoFocus
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent resize-none"
              rows={2}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-1">
              CSV File *
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null)
                setError(null)
              }}
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
            />
          </div>
          {error && (
            <div className="mb-4 bg-coral-tint border border-coral/30 rounded-lg p-3">
              <p className="text-sm text-coral">{error}</p>
            </div>
          )}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-warm-muted hover:text-warm-black font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || !file || uploading}
              className="px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 disabled:bg-warm-gray font-medium"
            >
              <span className="flex items-center gap-2">
                {uploading && <ButtonSpinner />}
                {uploading ? 'Creating...' : 'Create'}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Kebab Menu ---

function KebabMenu({
  onEdit,
  onDelete,
}: {
  onEdit: () => void
  onDelete: () => void
}) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation()
          setOpen(!open)
        }}
        className="p-1.5 rounded-lg text-warm-muted hover:text-warm-black hover:bg-warm-gray/50 transition-colors"
      >
        <MoreVertical className="w-4 h-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-warm-gray py-1 z-10">
          <button
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onEdit()
            }}
            className="w-full text-left px-3 py-2 text-sm text-warm-black hover:bg-warm-offwhite flex items-center gap-2"
          >
            <Pencil className="w-4 h-4" />
            Edit Deck
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onDelete()
            }}
            className="w-full text-left px-3 py-2 text-sm text-coral hover:bg-coral-tint flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Delete Deck
          </button>
        </div>
      )}
    </div>
  )
}

// --- Deck Card ---

function DeckCard({
  deck,
  onClick,
  onDelete,
  onUpdate,
}: {
  deck: DeckWithStats
  onClick: () => void
  onDelete: () => void
  onUpdate: (name: string, description: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(deck.name)
  const [editDescription, setEditDescription] = useState(deck.description || '')
  const nameInputRef = useRef<HTMLInputElement>(null)

  const recency = getRecencyStyle(deck.last_practiced_at)
  const growth = getGrowthEmoji(deck.mastery_percentage)
  const wordCount = deck.word_count || 0

  useEffect(() => {
    if (editing && nameInputRef.current) {
      nameInputRef.current.focus()
      nameInputRef.current.select()
    }
  }, [editing])

  const handleSave = () => {
    if (editName.trim()) {
      onUpdate(editName.trim(), editDescription.trim())
      setEditing(false)
    }
  }

  const handleCancel = () => {
    setEditName(deck.name)
    setEditDescription(deck.description || '')
    setEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  if (editing) {
    return (
      <div
        className={`h-[240px] bg-white rounded-lg border-l-[3px] ${recency.border} ring-2 ring-sage p-4 flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={nameInputRef}
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full px-2 py-1.5 border border-warm-gray rounded-md text-sm font-semibold text-warm-black focus:ring-1 focus:ring-sage focus:border-transparent mb-2"
        />
        <textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          placeholder="Description..."
          className="w-full px-2 py-1.5 border border-warm-gray rounded-md text-sm text-warm-muted focus:ring-1 focus:ring-sage focus:border-transparent resize-none flex-1"
        />
        <div className="flex justify-end gap-2 mt-3">
          <button
            onClick={handleCancel}
            className="px-3 py-1.5 text-sm text-warm-muted hover:text-warm-black font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!editName.trim()}
            className="px-3 py-1.5 text-sm bg-sage text-white rounded-md hover:bg-sage/90 disabled:bg-warm-gray font-medium"
          >
            Save
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={`group h-[240px] bg-white rounded-lg border-l-[3px] ${recency.border} shadow-sm cursor-pointer transition-all hover:shadow-md flex flex-col p-4`}
    >
      {/* Header: name + recency badge + kebab */}
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-warm-black truncate flex-1 min-w-0">{deck.name}</h3>
        <div className="flex items-center gap-1.5 ml-2 shrink-0">
          <span className={`inline-flex items-center px-2 py-0.5 text-xs rounded-full ${recency.badgeBg} ${recency.badgeText}`}>
            {formatRecency(deck.last_practiced_at)}
          </span>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <KebabMenu
              onEdit={() => setEditing(true)}
              onDelete={onDelete}
            />
          </div>
        </div>
      </div>

      {/* Description */}
      {deck.description && (
        <p className="text-sm text-warm-muted mt-1 line-clamp-2">{deck.description}</p>
      )}

      <div className="mt-auto">
        {/* Stats row */}
        <div className="flex items-center justify-between text-sm text-warm-muted mb-2">
          <span>{wordCount} words</span>
          <span>{growth} {deck.mastery_percentage}% mastered</span>
        </div>

        {/* Progress bar */}
        <div className={`h-1.5 ${recency.progressTrack} rounded-full overflow-hidden`}>
          <div
            className={`h-full ${recency.progressFill} transition-all rounded-full`}
            style={{ width: `${deck.mastery_percentage}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// --- Deck Grid View (main library view) ---

function DeckGrid({
  decks,
  loading,
  onCreateDeck,
  onUploadCSV,
  onCombineDecks,
  onDeleteDeck,
  onUpdateDeck,
}: {
  decks: DeckWithStats[]
  loading: boolean
  onCreateDeck: () => void
  onUploadCSV: () => void
  onCombineDecks: () => void
  onDeleteDeck: (deck: DeckWithStats) => void
  onUpdateDeck: (deck: DeckWithStats, name: string, description: string) => void
}) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="animate-pulse text-warm-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto bg-warm-offwhite">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Page header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-warm-black">Deck Library</h1>
            <p className="text-warm-muted mt-1">Manage your flashcard decks</p>
          </div>
          <CreateMenuDropdown
            onCreateDeck={onCreateDeck}
            onUploadCSV={onUploadCSV}
            onCombineDecks={onCombineDecks}
          />
        </div>

        {/* Deck grid */}
        {decks.length === 0 ? (
          <div className="text-center py-16 flex flex-col items-center">
            <div className="w-32 h-32 rounded-full bg-sage-tint flex items-center justify-center mb-6">
              <BookOpen className="w-16 h-16 text-sage" />
            </div>
            <h2 className="text-2xl font-semibold text-warm-black mb-2">No decks yet</h2>
            <p className="text-warm-muted text-lg">
              Create your first deck to start learning ☝
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {decks.map((deck) => (
              <DeckCard
                key={deck.id}
                deck={deck}
                onClick={() => navigate(`/library/deck/${deck.id}`)}
                onDelete={() => onDeleteDeck(deck)}
                onUpdate={(name, desc) => onUpdateDeck(deck, name, desc)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// --- Main Library Component ---

export default function Library() {
  const navigate = useNavigate()
  const [decks, setDecks] = useState<DeckWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showCombineModal, setShowCombineModal] = useState(false)

  useEffect(() => {
    loadDecks()
  }, [])

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

  const handleDeleteDeck = async (deckToDelete: DeckWithStats) => {
    const wordCount = deckToDelete.word_count || 0
    if (
      !confirm(
        `Delete "${deckToDelete.name}"? This will permanently delete ${wordCount} word${wordCount !== 1 ? 's' : ''}. This cannot be undone.`
      )
    ) {
      return
    }
    try {
      await deckApi.deleteDeck(deckToDelete.id)
      setDecks(decks.filter((d) => d.id !== deckToDelete.id))
    } catch (error) {
      console.error('Failed to delete deck:', error)
      alert('Failed to delete deck')
    }
  }

  const handleUpdateDeck = async (deck: DeckWithStats, name: string, description: string) => {
    try {
      await deckApi.updateDeck(deck.id, { name, description })
      setDecks(decks.map((d) =>
        d.id === deck.id ? { ...d, name, description } : d
      ))
    } catch (error) {
      console.error('Failed to update deck:', error)
      alert('Failed to update deck')
    }
  }

  const handleCreateDeckFromCSV = async (name: string, description: string, words: { word: string; pinyin: string; meaning: string }[]) => {
    try {
      const deckResponse = await deckApi.createDeck({ name, description })
      const newDeck = deckResponse.data
      await deckApi.addWordsToDeck(newDeck.id, words)
      setShowUploadModal(false)
      loadDecks()
      navigate(`/library/deck/${newDeck.id}`)
    } catch (error) {
      console.error('Failed to create deck from CSV:', error)
      alert('Failed to create deck')
    }
  }

  const handleCombineDecks = async (name: string, description: string, sourceDeckIds: number[]) => {
    try {
      const response = await deckApi.combineDecks({ name, description, source_deck_ids: sourceDeckIds })
      setDecks([...decks, response.data])
      setShowCombineModal(false)
      navigate(`/library/deck/${response.data.id}`)
    } catch (error) {
      console.error('Failed to combine decks:', error)
      alert('Failed to combine decks')
    }
  }

  return (
    <>
      <Routes>
        <Route path="/" element={
          <DeckGrid
            decks={decks}
            loading={loading}
            onCreateDeck={() => setShowCreateModal(true)}
            onUploadCSV={() => setShowUploadModal(true)}
            onCombineDecks={() => setShowCombineModal(true)}
            onDeleteDeck={handleDeleteDeck}
            onUpdateDeck={handleUpdateDeck}
          />
        } />
        <Route path="deck/:deckId" element={
          <DeckWordsView onDeckDeleted={loadDecks} />
        } />
      </Routes>

      {/* Modals */}
      <CreateDeckModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateDeck}
      />
      <CreateDeckCSVModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onCreate={handleCreateDeckFromCSV}
      />
      <CombineDecksModal
        isOpen={showCombineModal}
        onClose={() => setShowCombineModal(false)}
        decks={decks}
        onCombine={handleCombineDecks}
      />
    </>
  )
}
