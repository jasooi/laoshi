import { useState, useCallback, useRef, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { HomeProvider, useHome } from './HomeContext'
import DeckListPanel from './DeckListPanel'
import DeckDetailPanel from './DeckDetailPanel'
import PracticePanel from './PracticePanel'
import EmptyDeckPlaceholder from './EmptyDeckPlaceholder'
import LoadingRitual from './LoadingRitual'
import { SessionSummary } from '../../components/SessionSummary'

const MIN_LEFT_WIDTH = 280
const MAX_LEFT_WIDTH = 600
const DEFAULT_LEFT_WIDTH = 384

function HomeLayout() {
  const { viewState, activeSessionData, summaryData, onLoadingComplete, backToHome } = useHome()
  const [leftWidth, setLeftWidth] = useState(DEFAULT_LEFT_WIDTH)
  const isDragging = useRef(false)

  const handleMouseDown = useCallback(() => {
    isDragging.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      // Subtract the sidebar width (80px) to get position relative to the home content area
      const sidebarWidth = 80
      const newWidth = Math.min(MAX_LEFT_WIDTH, Math.max(MIN_LEFT_WIDTH, e.clientX - sidebarWidth))
      setLeftWidth(newWidth)
    }

    const handleMouseUp = () => {
      if (!isDragging.current) return
      isDragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

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
      <DeckListPanel width={leftWidth} />

      {/* Drag handle */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1 cursor-col-resize bg-transparent hover:bg-sage/30 active:bg-sage/50 transition-colors flex-shrink-0"
      />

      <div className="flex-1 flex flex-col overflow-hidden h-full">
        <Routes>
          <Route path="/" element={<EmptyDeckPlaceholder />} />
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
