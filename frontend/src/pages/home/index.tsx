import { Routes, Route, Navigate } from 'react-router-dom'
import { HomeProvider, useHome } from './HomeContext'
import DeckListPanel from './DeckListPanel'
import DeckDetailPanel from './DeckDetailPanel'
import PracticePanel from './PracticePanel'
import EmptyDeckPlaceholder from './EmptyDeckPlaceholder'
import { AlertTriangle } from 'lucide-react'

// End session confirmation modal
function EndSessionModal() {
  const { showEndSessionModal, confirmEndSession, cancelEndSession } = useHome()

  if (!showEndSessionModal) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          </div>
          <h3 className="text-lg font-semibold text-stone-800">End Current Session?</h3>
        </div>
        <p className="text-stone-600 mb-6">
          You have an active practice session. Ending it will save your progress so far. Are you sure you want to continue?
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={cancelEndSession}
            className="px-4 py-2 text-stone-600 hover:text-stone-800 font-medium"
          >
            Cancel
          </button>
          <button
            onClick={confirmEndSession}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 font-medium"
          >
            End Session
          </button>
        </div>
      </div>
    </div>
  )
}

// Main home layout
function HomeLayout() {
  const { selectedDeckId } = useHome()

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left panel - Deck list */}
      <DeckListPanel />

      {/* Right panel - Content area */}
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={
            selectedDeckId ? (
              <Navigate to={`/home/deck/${selectedDeckId}`} replace />
            ) : (
              <EmptyDeckPlaceholder />
            )
          } />
          <Route path="deck/:deckId" element={<DeckDetailPanel />} />
          <Route path="deck/:deckId/practice/:sessionId" element={<PracticePanel />} />
        </Routes>
      </div>

      {/* Modals */}
      <EndSessionModal />
    </div>
  )
}

export default function Home() {
  return (
    <HomeProvider>
      <HomeLayout />
    </HomeProvider>
  )
}
