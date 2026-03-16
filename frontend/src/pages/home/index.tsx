import { Routes, Route, Navigate } from 'react-router-dom'
import { HomeProvider, useHome } from './HomeContext'
import DeckListPanel from './DeckListPanel'
import DeckDetailPanel from './DeckDetailPanel'
import PracticePanel from './PracticePanel'
import EmptyDeckPlaceholder from './EmptyDeckPlaceholder'
import LoadingRitual from './LoadingRitual'
import { SessionSummary } from '../../components/SessionSummary'

function HomeLayout() {
  const { viewState, activeSessionData, summaryData, onLoadingComplete, backToHome, selectedDeckId } = useHome()

  // Loading ritual
  if (viewState === 'loading') {
    return <LoadingRitual onReady={onLoadingComplete} />
  }

  // Practice chat
  if (viewState === 'practicing' && activeSessionData) {
    return <PracticePanel />
  }

  // Session summary
  if (viewState === 'summary' && summaryData) {
    return (
      <SessionSummary
        summary={summaryData}
        onNewSession={() => backToHome()}
      />
    )
  }

  // Default: Home view with deck list + detail
  return (
    <div className="flex h-full">
      <DeckListPanel />
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
        </Routes>
      </div>
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
