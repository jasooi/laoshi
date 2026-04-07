import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { WordContext, PracticeSummaryResponse } from '../../types/api'

export type ViewState = 'home' | 'loading' | 'practicing' | 'summary'

interface ActiveSessionData {
  sessionId: number
  deckId: number
  deckName: string
  greeting?: string
  currentWord?: WordContext
}

interface HomeContextValue {
  selectedDeckId: number | null
  viewState: ViewState
  activeSessionData: ActiveSessionData | null
  summaryData: PracticeSummaryResponse | null
  deckCount: number
  selectDeck: (deckId: number) => void
  setDeckCount: (count: number) => void
  startPractice: (data: ActiveSessionData) => void
  onLoadingComplete: () => void
  endPractice: () => void
  showSummary: (summary: PracticeSummaryResponse) => void
  backToHome: () => void
}

const STORAGE_KEY = 'laoshi_active_session'

function saveSession(data: ActiveSessionData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    sessionId: data.sessionId,
    deckId: data.deckId,
    deckName: data.deckName,
  }))
}

function loadSession(): ActiveSessionData | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return null
    return JSON.parse(saved)
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEY)
}

const HomeContext = createContext<HomeContextValue | undefined>(undefined)

export function HomeProvider({ children }: { children: React.ReactNode }) {
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)
  const [viewState, setViewState] = useState<ViewState>('home')
  const [activeSessionData, setActiveSessionData] = useState<ActiveSessionData | null>(null)
  const [summaryData, setSummaryData] = useState<PracticeSummaryResponse | null>(null)
  const [deckCount, setDeckCountState] = useState(0)

  const setDeckCount = useCallback((count: number) => {
    setDeckCountState(count)
  }, [])

  // Restore active session from localStorage on mount
  useEffect(() => {
    const saved = loadSession()
    if (saved) {
      setActiveSessionData(saved)
      setSelectedDeckId(saved.deckId)
      setViewState('practicing')
    }
  }, [])

  const selectDeck = useCallback((deckId: number) => {
    setSelectedDeckId(deckId)
  }, [])

  const startPractice = useCallback((data: ActiveSessionData) => {
    setActiveSessionData(data)
    setSelectedDeckId(data.deckId)
    saveSession(data)
    setViewState('loading')
  }, [])

  const onLoadingComplete = useCallback(() => {
    setViewState('practicing')
  }, [])

  const endPractice = useCallback(() => {
    setActiveSessionData(null)
    setSummaryData(null)
    clearSession()
    setViewState('home')
  }, [])

  const showSummary = useCallback((summary: PracticeSummaryResponse) => {
    setSummaryData(summary)
    clearSession()
    setViewState('summary')
  }, [])

  const backToHome = useCallback(() => {
    setActiveSessionData(null)
    setSummaryData(null)
    setViewState('home')
  }, [])

  return (
    <HomeContext.Provider
      value={{
        selectedDeckId,
        viewState,
        activeSessionData,
        summaryData,
        deckCount,
        selectDeck,
        setDeckCount,
        startPractice,
        onLoadingComplete,
        endPractice,
        showSummary,
        backToHome,
      }}
    >
      {children}
    </HomeContext.Provider>
  )
}

export function useHome() {
  const context = useContext(HomeContext)
  if (context === undefined) {
    throw new Error('useHome must be used within a HomeProvider')
  }
  return context
}
