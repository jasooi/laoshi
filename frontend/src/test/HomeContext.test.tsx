/**
 * Tests for HomeContext state management (T-7.3).
 *
 * Tests the viewState-driven rendering, localStorage persistence,
 * and state transitions for the practice session lifecycle.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import React from 'react'
import { HomeProvider, useHome } from '../pages/home/HomeContext'

// Helper component to access and display context values
function TestConsumer({ onContext }: { onContext: (ctx: ReturnType<typeof useHome>) => void }) {
  const ctx = useHome()
  React.useEffect(() => {
    onContext(ctx)
  })
  return (
    <div>
      <span data-testid="viewState">{ctx.viewState}</span>
      <span data-testid="selectedDeckId">{ctx.selectedDeckId ?? 'null'}</span>
      <span data-testid="sessionId">{ctx.activeSessionData?.sessionId ?? 'null'}</span>
    </div>
  )
}

// Helper to render with context and capture latest values
function renderWithContext() {
  let latestCtx: ReturnType<typeof useHome> | null = null

  const result = render(
    <HomeProvider>
      <TestConsumer onContext={(ctx) => { latestCtx = ctx }} />
    </HomeProvider>
  )

  return {
    ...result,
    getCtx: () => latestCtx!,
  }
}

const STORAGE_KEY = 'laoshi_active_session'

describe('HomeContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('initial state', () => {
    it('should have viewState "home" initially', () => {
      const { getCtx } = renderWithContext()
      expect(getCtx().viewState).toBe('home')
    })

    it('should have null selectedDeckId initially', () => {
      const { getCtx } = renderWithContext()
      expect(getCtx().selectedDeckId).toBeNull()
    })

    it('should have null activeSessionData initially', () => {
      const { getCtx } = renderWithContext()
      expect(getCtx().activeSessionData).toBeNull()
    })

    it('should have null summaryData initially', () => {
      const { getCtx } = renderWithContext()
      expect(getCtx().summaryData).toBeNull()
    })
  })

  describe('selectDeck', () => {
    it('should update selectedDeckId', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().selectDeck(42)
      })

      expect(getCtx().selectedDeckId).toBe(42)
    })
  })

  describe('startPractice', () => {
    it('should set viewState to "loading"', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      expect(getCtx().viewState).toBe('loading')
    })

    it('should set activeSessionData', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      expect(getCtx().activeSessionData).not.toBeNull()
      expect(getCtx().activeSessionData!.sessionId).toBe(10)
      expect(getCtx().activeSessionData!.deckId).toBe(5)
      expect(getCtx().activeSessionData!.deckName).toBe('Test Deck')
    })

    it('should save session to localStorage', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      expect(stored.sessionId).toBe(10)
      expect(stored.deckId).toBe(5)
      expect(stored.deckName).toBe('Test Deck')
    })

    it('should update selectedDeckId to match session deck', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      expect(getCtx().selectedDeckId).toBe(5)
    })
  })

  describe('onLoadingComplete', () => {
    it('should transition viewState from "loading" to "practicing"', () => {
      const { getCtx } = renderWithContext()

      // First start practice (sets to loading)
      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })
      expect(getCtx().viewState).toBe('loading')

      // Then complete loading
      act(() => {
        getCtx().onLoadingComplete()
      })
      expect(getCtx().viewState).toBe('practicing')
    })
  })

  describe('endPractice', () => {
    it('should reset viewState to "home"', () => {
      const { getCtx } = renderWithContext()

      // Start practice first
      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      // End practice
      act(() => {
        getCtx().endPractice()
      })

      expect(getCtx().viewState).toBe('home')
    })

    it('should clear activeSessionData', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      act(() => {
        getCtx().endPractice()
      })

      expect(getCtx().activeSessionData).toBeNull()
    })

    it('should clear localStorage', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      act(() => {
        getCtx().endPractice()
      })

      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    })
  })

  describe('showSummary', () => {
    it('should set viewState to "summary"', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      act(() => {
        getCtx().showSummary({
          words_practiced: 3,
          words_skipped: 0,
          summary_text: 'Good job!',
          word_results: [],
        } as any)
      })

      expect(getCtx().viewState).toBe('summary')
    })

    it('should store summaryData', () => {
      const { getCtx } = renderWithContext()

      const summary = {
        words_practiced: 3,
        words_skipped: 0,
        summary_text: 'Good job!',
        word_results: [],
      }

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      act(() => {
        getCtx().showSummary(summary as any)
      })

      expect(getCtx().summaryData).not.toBeNull()
      expect(getCtx().summaryData!.summary_text).toBe('Good job!')
    })

    it('should clear localStorage when showing summary', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({
          sessionId: 10,
          deckId: 5,
          deckName: 'Test Deck',
        })
      })

      act(() => {
        getCtx().showSummary({ words_practiced: 3, words_skipped: 0, summary_text: 'Done!', word_results: [] } as any)
      })

      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    })
  })

  describe('backToHome', () => {
    it('should reset viewState to "home"', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({ sessionId: 10, deckId: 5, deckName: 'Test Deck' })
      })
      act(() => {
        getCtx().showSummary({ words_practiced: 3, words_skipped: 0, summary_text: 'Done!', word_results: [] } as any)
      })

      act(() => {
        getCtx().backToHome()
      })

      expect(getCtx().viewState).toBe('home')
    })

    it('should clear activeSessionData and summaryData', () => {
      const { getCtx } = renderWithContext()

      act(() => {
        getCtx().startPractice({ sessionId: 10, deckId: 5, deckName: 'Test Deck' })
      })
      act(() => {
        getCtx().showSummary({ words_practiced: 3, words_skipped: 0, summary_text: 'Done!', word_results: [] } as any)
      })
      act(() => {
        getCtx().backToHome()
      })

      expect(getCtx().activeSessionData).toBeNull()
      expect(getCtx().summaryData).toBeNull()
    })
  })

  describe('localStorage restoration', () => {
    it('should restore session from localStorage on mount', () => {
      // Pre-seed localStorage before rendering
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        sessionId: 42,
        deckId: 7,
        deckName: 'Restored Deck',
      }))

      const { getCtx } = renderWithContext()

      // Should restore to practicing state
      expect(getCtx().viewState).toBe('practicing')
      expect(getCtx().activeSessionData).not.toBeNull()
      expect(getCtx().activeSessionData!.sessionId).toBe(42)
      expect(getCtx().activeSessionData!.deckId).toBe(7)
      expect(getCtx().selectedDeckId).toBe(7)
    })

    it('should handle corrupt localStorage gracefully', () => {
      localStorage.setItem(STORAGE_KEY, 'not-valid-json{{{')

      const { getCtx } = renderWithContext()

      // Should fall back to home state
      expect(getCtx().viewState).toBe('home')
      expect(getCtx().activeSessionData).toBeNull()
      // Corrupt data should be cleared
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    })
  })

  describe('useHome outside provider', () => {
    it('should throw when used outside HomeProvider', () => {
      // Suppress React error boundary console output
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      function BadComponent() {
        useHome()
        return null
      }

      expect(() => {
        render(<BadComponent />)
      }).toThrow('useHome must be used within a HomeProvider')

      consoleSpy.mockRestore()
    })
  })
})
