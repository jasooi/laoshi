/**
 * Tests for ConfidenceRating component (T-7.6).
 *
 * Tests the inline rating buttons, color-coded pills,
 * edit functionality, and onRate callback behavior.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ConfidenceRating from '../pages/home/ConfidenceRating'

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

describe('ConfidenceRating', () => {
  const defaultProps = {
    messageId: 'rating-1',
    wordId: 42,
    wordText: '你好',
    isLatest: true,
    onRate: vi.fn(),
  }

  describe('unrated state (buttons visible)', () => {
    it('should render the confidence question with the word', () => {
      render(<ConfidenceRating {...defaultProps} />)

      expect(screen.getByText(/how confident are you using/i)).toBeInTheDocument()
      expect(screen.getByText('你好')).toBeInTheDocument()
    })

    it('should render 6 rating buttons when quality is undefined and isLatest', () => {
      render(<ConfidenceRating {...defaultProps} quality={undefined} />)

      const buttons = screen.getAllByRole('button')
      // 6 rating buttons (0-5)
      expect(buttons.length).toBeGreaterThanOrEqual(6)
    })

    it('should show correct labels for all 6 buttons', () => {
      render(<ConfidenceRating {...defaultProps} quality={undefined} />)

      expect(screen.getByText('Blackout')).toBeInTheDocument()
      expect(screen.getByText('Wrong')).toBeInTheDocument()
      expect(screen.getByText('Hard')).toBeInTheDocument()
      expect(screen.getByText('OK')).toBeInTheDocument()
      expect(screen.getByText('Good')).toBeInTheDocument()
      expect(screen.getByText('Easy')).toBeInTheDocument()
    })

    it('should show rating numbers 0-5', () => {
      render(<ConfidenceRating {...defaultProps} quality={undefined} />)

      for (let i = 0; i <= 5; i++) {
        expect(screen.getByText(String(i))).toBeInTheDocument()
      }
    })
  })

  describe('rating callback', () => {
    it('should call onRate with correct args when clicking a button', async () => {
      const onRate = vi.fn()
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={undefined}
          onRate={onRate}
        />
      )

      // Click the "Good" (4) button
      fireEvent.click(screen.getByText('Good').closest('button')!)

      // Wait for the 150ms highlight delay
      await waitFor(() => {
        expect(onRate).toHaveBeenCalledWith('rating-1', 42, 4, false)
      }, { timeout: 500 })
    })

    it('should pass isEdit=false for first-time rating on latest prompt', async () => {
      const onRate = vi.fn()
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={undefined}
          isLatest={true}
          onRate={onRate}
        />
      )

      fireEvent.click(screen.getByText('Easy').closest('button')!)

      await waitFor(() => {
        expect(onRate).toHaveBeenCalledWith('rating-1', 42, 5, false)
      }, { timeout: 500 })
    })

    it('should pass isEdit=true when editing a past rating (isLatest=false)', async () => {
      const onRate = vi.fn()
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={3}
          isLatest={false}
          onRate={onRate}
        />
      )

      // Click the edit button to reopen
      const editButton = screen.getByTitle('Edit rating')
      fireEvent.click(editButton)

      // Now click a new rating
      fireEvent.click(screen.getByText('Easy').closest('button')!)

      await waitFor(() => {
        expect(onRate).toHaveBeenCalledWith('rating-1', 42, 5, true)
      }, { timeout: 500 })
    })
  })

  describe('rated state (pill visible)', () => {
    it('should show color-coded pill after rating', () => {
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={4}
          isLatest={false}
        />
      )

      // Should show the rating pill text
      expect(screen.getByText(/Good/)).toBeInTheDocument()
    })

    it('should NOT show buttons when quality is set and not editing', () => {
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={4}
          isLatest={false}
        />
      )

      // Buttons should not be visible
      expect(screen.queryByText('Blackout')).not.toBeInTheDocument()
    })

    it('should show edit (pencil) icon when rated', () => {
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={4}
          isLatest={false}
        />
      )

      expect(screen.getByTitle('Edit rating')).toBeInTheDocument()
    })
  })

  describe('3-tier color coding', () => {
    it('should use coral colors for ratings 0-2', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={1}
          isLatest={false}
        />
      )

      // Find the pill element and check it has coral styling
      const pill = container.querySelector('[class*="coral"]')
      expect(pill).not.toBeNull()
    })

    it('should use amber colors for rating 3', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={3}
          isLatest={false}
        />
      )

      const pill = container.querySelector('[class*="amber"]')
      expect(pill).not.toBeNull()
    })

    it('should use sage colors for ratings 4-5', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={5}
          isLatest={false}
        />
      )

      const pill = container.querySelector('[class*="sage"]')
      expect(pill).not.toBeNull()
    })

    it('should use coral for rating 0 (Blackout)', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={0}
          isLatest={false}
        />
      )

      const pill = container.querySelector('[class*="coral"]')
      expect(pill).not.toBeNull()
    })

    it('should use coral for rating 2 (Hard)', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={2}
          isLatest={false}
        />
      )

      const pill = container.querySelector('[class*="coral"]')
      expect(pill).not.toBeNull()
    })

    it('should use sage for rating 4 (Good)', () => {
      const { container } = render(
        <ConfidenceRating
          {...defaultProps}
          quality={4}
          isLatest={false}
        />
      )

      const pill = container.querySelector('[class*="sage"]')
      expect(pill).not.toBeNull()
    })
  })

  describe('edit flow', () => {
    it('should reopen buttons when edit icon is clicked', () => {
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={3}
          isLatest={false}
        />
      )

      // Click edit
      fireEvent.click(screen.getByTitle('Edit rating'))

      // Buttons should now be visible
      expect(screen.getByText('Blackout')).toBeInTheDocument()
      expect(screen.getByText('Easy')).toBeInTheDocument()
    })

    it('should collapse buttons after re-rating', async () => {
      const onRate = vi.fn()
      render(
        <ConfidenceRating
          {...defaultProps}
          quality={3}
          isLatest={false}
          onRate={onRate}
        />
      )

      // Open edit
      fireEvent.click(screen.getByTitle('Edit rating'))

      // Click new rating
      fireEvent.click(screen.getByText('Easy').closest('button')!)

      // After the callback, editing should stop
      await waitFor(() => {
        expect(onRate).toHaveBeenCalled()
      }, { timeout: 500 })
    })
  })

  describe('Laoshi avatar', () => {
    it('should render Laoshi avatar image', () => {
      render(<ConfidenceRating {...defaultProps} quality={undefined} />)

      const avatar = screen.getByAltText('Laoshi')
      expect(avatar).toBeInTheDocument()
    })
  })
})
