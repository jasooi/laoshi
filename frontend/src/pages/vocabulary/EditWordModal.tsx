import { useState, useEffect } from 'react'
import api from '../../lib/api'
import { Word } from '../../types/api'

interface EditWordModalProps {
  word: Word | null
  onClose: () => void
  onSaveSuccess: (updatedWord: Word) => void
}

const EditWordModal = ({ word, onClose, onSaveSuccess }: EditWordModalProps) => {
  const [editForm, setEditForm] = useState({ word: '', pinyin: '', meaning: '', source_name: '' })
  const [editError, setEditError] = useState<string | null>(null)
  const [editSaving, setEditSaving] = useState(false)

  useEffect(() => {
    if (word) {
      setEditForm({
        word: word.word,
        pinyin: word.pinyin,
        meaning: word.meaning,
        source_name: word.source_name || '',
      })
      setEditError(null)
    }
  }, [word])

  if (!word) return null

  const handleEditSubmit = async () => {
    if (!editForm.word.trim() || !editForm.pinyin.trim() || !editForm.meaning.trim()) {
      setEditError('Word, pinyin, and meaning are required.')
      return
    }
    setEditSaving(true)
    setEditError(null)
    try {
      const payload: Record<string, string> = {
        word: editForm.word.trim(),
        pinyin: editForm.pinyin.trim(),
        meaning: editForm.meaning.trim(),
      }
      if (editForm.source_name.trim()) {
        payload.source_name = editForm.source_name.trim()
      }
      const response = await api.put(`/api/words/${word.id}`, payload)
      const updatedWord = response.data as Word
      onSaveSuccess(updatedWord)
    } catch (error: unknown) {
      console.error('Error updating word:', error)
      const axiosError = error as { response?: { data?: { error?: string } } }
      setEditError(axiosError.response?.data?.error || 'Failed to update word.')
    } finally {
      setEditSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-xl font-semibold text-gray-900">Edit Word</h2>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="px-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Word (中文)</label>
            <input
              type="text"
              value={editForm.word}
              onChange={(e) => setEditForm({ ...editForm, word: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pinyin</label>
            <input
              type="text"
              value={editForm.pinyin}
              onChange={(e) => setEditForm({ ...editForm, pinyin: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Meaning</label>
            <input
              type="text"
              value={editForm.meaning}
              onChange={(e) => setEditForm({ ...editForm, meaning: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source Name</label>
            <input
              type="text"
              value={editForm.source_name}
              onChange={(e) => setEditForm({ ...editForm, source_name: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
        </div>

        {editError && (
          <div className="px-6 pt-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{editError}</p>
            </div>
          </div>
        )}

        <div className="px-6 py-6 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2.5 text-gray-700 font-medium border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleEditSubmit}
            disabled={editSaving}
            className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white font-medium rounded-full transition-colors"
          >
            {editSaving && (
              <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {editSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default EditWordModal
