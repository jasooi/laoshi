import { useState, useEffect, useRef } from 'react'
import { Check, Info } from 'lucide-react'
import type { DeckWithStats } from '../../types/api'

interface CombineDecksModalProps {
  isOpen: boolean
  onClose: () => void
  decks: DeckWithStats[]
  onCombine: (name: string, description: string, sourceDeckIds: number[]) => void
}

export default function CombineDecksModal({
  isOpen,
  onClose,
  decks,
  onCombine,
}: CombineDecksModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedDeckIds, setSelectedDeckIds] = useState<Set<number>>(new Set())
  const nameInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen && nameInputRef.current) {
      nameInputRef.current.focus()
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) {
      setName('')
      setDescription('')
      setSelectedDeckIds(new Set())
    }
  }, [isOpen])

  if (!isOpen) return null

  const toggleDeck = (deckId: number) => {
    const newSelected = new Set(selectedDeckIds)
    if (newSelected.has(deckId)) {
      newSelected.delete(deckId)
    } else {
      newSelected.add(deckId)
    }
    setSelectedDeckIds(newSelected)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim() && selectedDeckIds.size >= 2) {
      onCombine(name.trim(), description.trim(), Array.from(selectedDeckIds))
    }
  }

  const selectedDecks = decks.filter((d) => selectedDeckIds.has(d.id))
  const totalWords = selectedDecks.reduce((sum, d) => sum + (d.word_count || 0), 0)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-warm-black mb-1">Combine Decks</h3>
        <p className="text-sm text-warm-muted mb-4">
          Select two or more decks to combine into a new deck
        </p>

        <form onSubmit={handleSubmit}>
          {/* Deck Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-2">
              Select Decks *
            </label>
            <div className="space-y-2 max-h-[200px] overflow-y-auto border border-warm-gray rounded-lg p-2">
              {decks.length === 0 ? (
                <p className="text-sm text-warm-muted text-center py-4">No decks available</p>
              ) : (
                decks.map((deck) => (
                  <button
                    key={deck.id}
                    type="button"
                    onClick={() => toggleDeck(deck.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors ${
                      selectedDeckIds.has(deck.id)
                        ? 'bg-sage-tint text-sage'
                        : 'hover:bg-warm-offwhite text-warm-black'
                    }`}
                  >
                    <div>
                      <span className="font-medium">{deck.name}</span>
                      <span className="text-sm ml-2 opacity-70">
                        ({deck.word_count || 0} words)
                      </span>
                    </div>
                    {selectedDeckIds.has(deck.id) && (
                      <Check className="w-4 h-4" />
                    )}
                  </button>
                ))
              )}
            </div>
            {selectedDeckIds.size > 0 && (
              <p className="text-xs text-warm-muted mt-1">
                {selectedDeckIds.size} deck{selectedDeckIds.size !== 1 ? 's' : ''} selected
                ({totalWords} words total)
              </p>
            )}
          </div>

          {/* New Deck Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-black mb-1">
              New Deck Name *
            </label>
            <input
              ref={nameInputRef}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Combined HSK 1 & 2"
              className="w-full px-3 py-2 border border-warm-gray rounded-lg focus:ring-2 focus:ring-sage focus:border-transparent"
            />
          </div>

          {/* New Deck Description */}
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

          {/* Info Note */}
          <div className="mb-6 p-3 bg-sage-tint/50 rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 text-sage mt-0.5 flex-shrink-0" />
            <p className="text-sm text-sage">
              Words will be copied (not moved) to the new deck. SRS progress and mastery status
              are preserved. The original decks will remain unchanged.
            </p>
          </div>

          {/* Actions */}
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
              disabled={!name.trim() || selectedDeckIds.size < 2}
              className="px-4 py-2 bg-sage text-white rounded-lg hover:bg-sage/90 disabled:bg-warm-gray font-medium"
            >
              Combine {selectedDeckIds.size > 0 ? `(${selectedDeckIds.size})` : ''}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
