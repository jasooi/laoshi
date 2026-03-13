import { useNavigate } from 'react-router-dom'
import { BookOpen, Plus } from 'lucide-react'

export default function EmptyDeckPlaceholder() {
  const navigate = useNavigate()

  return (
    <div className="flex-1 flex items-center justify-center bg-stone-50 p-8">
      <div className="max-w-md w-full text-center">
        <div className="w-24 h-24 bg-stone-200 rounded-full flex items-center justify-center mx-auto mb-6">
          <BookOpen className="w-12 h-12 text-stone-400" />
        </div>
        <h2 className="text-2xl font-bold text-stone-800 mb-2">
          Welcome to Laoshi Coach!
        </h2>
        <p className="text-stone-500 mb-6">
          Select a deck from the list to start practicing, or create a new deck to begin your learning journey.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate('/library')}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            Create New Deck
          </button>
        </div>
        <p className="text-sm text-stone-400 mt-6">
          Tip: Decks are collections of vocabulary words. You can organize words by theme, difficulty, or any way you like!
        </p>
      </div>
    </div>
  )
}
