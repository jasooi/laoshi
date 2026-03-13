import React, { createContext, useContext, useState, useCallback } from 'react'

interface HomeContextValue {
  selectedDeckId: number | null
  activePracticeSessionId: number | null
  showEndSessionModal: boolean
  pendingDeckId: number | null
  selectDeck: (deckId: number) => void
  startPractice: (deckId: number, sessionId: number) => void
  endPractice: () => void
  confirmEndSession: () => void
  cancelEndSession: () => void
  requestDeckSwitch: (deckId: number) => void
}

const HomeContext = createContext<HomeContextValue | undefined>(undefined)

export function HomeProvider({ children }: { children: React.ReactNode }) {
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)
  const [activePracticeSessionId, setActivePracticeSessionId] = useState<number | null>(null)
  const [showEndSessionModal, setShowEndSessionModal] = useState(false)
  const [pendingDeckId, setPendingDeckId] = useState<number | null>(null)

  const selectDeck = useCallback((deckId: number) => {
    setSelectedDeckId(deckId)
  }, [])

  const startPractice = useCallback((deckId: number, sessionId: number) => {
    setSelectedDeckId(deckId)
    setActivePracticeSessionId(sessionId)
  }, [])

  const endPractice = useCallback(() => {
    setActivePracticeSessionId(null)
    setShowEndSessionModal(false)
    setPendingDeckId(null)
  }, [])

  const confirmEndSession = useCallback(() => {
    setActivePracticeSessionId(null)
    setShowEndSessionModal(false)
    if (pendingDeckId !== null) {
      setSelectedDeckId(pendingDeckId)
      setPendingDeckId(null)
    }
  }, [pendingDeckId])

  const cancelEndSession = useCallback(() => {
    setShowEndSessionModal(false)
    setPendingDeckId(null)
  }, [])

  const requestDeckSwitch = useCallback((deckId: number) => {
    if (activePracticeSessionId !== null) {
      setPendingDeckId(deckId)
      setShowEndSessionModal(true)
    } else {
      setSelectedDeckId(deckId)
    }
  }, [activePracticeSessionId])

  return (
    <HomeContext.Provider
      value={{
        selectedDeckId,
        activePracticeSessionId,
        showEndSessionModal,
        pendingDeckId,
        selectDeck,
        startPractice,
        endPractice,
        confirmEndSession,
        cancelEndSession,
        requestDeckSwitch,
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
