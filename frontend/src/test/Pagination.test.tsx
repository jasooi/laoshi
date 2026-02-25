import { render, screen, fireEvent } from '@testing-library/react'
import { vi, beforeEach, describe, it, expect } from 'vitest'
import Pagination from '../components/Pagination'

describe('Pagination', () => {
  const defaultProps = {
    page: 1,
    totalPages: 5,
    total: 50,
    perPage: 10,
    hasNext: true,
    hasPrev: false,
    onPageChange: vi.fn(),
    onPerPageChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ---------------------------------------------------------------------------
  // 1. Renders page numbers correctly
  // ---------------------------------------------------------------------------
  describe('renders page numbers correctly', () => {
    it('should render buttons 1 through 5 when totalPages is 5 and page is 3 (all in range)', () => {
      // Arrange — page=3 means current±1 plus first/last covers all 5 pages
      render(<Pagination {...defaultProps} page={3} totalPages={5} hasPrev={true} hasNext={true} />)

      // Act / Assert — one assertion per visible page number
      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '4' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '5' })).toBeInTheDocument()
    })

    it('should highlight the current page button with the active style', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={1} totalPages={5} />)

      // Act
      const activeButton = screen.getByRole('button', { name: '1' })

      // Assert — active page carries the purple background class
      expect(activeButton).toHaveClass('bg-purple-600')
    })
  })

  // ---------------------------------------------------------------------------
  // 2. Previous button disabled on page 1
  // ---------------------------------------------------------------------------
  describe('Previous button', () => {
    it('should be disabled when hasPrev is false', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={1} hasPrev={false} />)

      // Act
      const prevButton = screen.getByText('<').closest('button')

      // Assert
      expect(prevButton).toBeDisabled()
    })

    it('should carry the cursor-not-allowed class when hasPrev is false', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={1} hasPrev={false} />)

      // Act
      const prevButton = screen.getByText('<').closest('button')

      // Assert
      expect(prevButton).toHaveClass('cursor-not-allowed')
    })

    it('should not be disabled when hasPrev is true', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={2} hasPrev={true} />)

      // Act
      const prevButton = screen.getByText('<').closest('button')

      // Assert
      expect(prevButton).not.toBeDisabled()
    })
  })

  // ---------------------------------------------------------------------------
  // 3. Next button disabled on last page
  // ---------------------------------------------------------------------------
  describe('Next button', () => {
    it('should be disabled when hasNext is false', () => {
      // Arrange
      render(
        <Pagination
          {...defaultProps}
          page={5}
          totalPages={5}
          hasNext={false}
          hasPrev={true}
        />
      )

      // Act
      const nextButton = screen.getByText('>').closest('button')

      // Assert
      expect(nextButton).toBeDisabled()
    })

    it('should carry the cursor-not-allowed class when hasNext is false', () => {
      // Arrange
      render(
        <Pagination
          {...defaultProps}
          page={5}
          totalPages={5}
          hasNext={false}
          hasPrev={true}
        />
      )

      // Act
      const nextButton = screen.getByText('>').closest('button')

      // Assert
      expect(nextButton).toHaveClass('cursor-not-allowed')
    })

    it('should not be disabled when hasNext is true', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={1} hasNext={true} />)

      // Act
      const nextButton = screen.getByText('>').closest('button')

      // Assert
      expect(nextButton).not.toBeDisabled()
    })
  })

  // ---------------------------------------------------------------------------
  // 4. Clicking a page number calls onPageChange with the correct value
  // ---------------------------------------------------------------------------
  describe('clicking a page number', () => {
    it('should call onPageChange with 3 when page 3 button is clicked', () => {
      // Arrange — page=2 so that page 3 is visible (current+1)
      const onPageChange = vi.fn()
      render(
        <Pagination {...defaultProps} page={2} totalPages={5} hasPrev={true} onPageChange={onPageChange} />
      )

      // Act
      fireEvent.click(screen.getByRole('button', { name: '3' }))

      // Assert
      expect(onPageChange).toHaveBeenCalledTimes(1)
      expect(onPageChange).toHaveBeenCalledWith(3)
    })

    it('should call onPageChange with the previous page when Previous is clicked', () => {
      // Arrange
      const onPageChange = vi.fn()
      render(
        <Pagination
          {...defaultProps}
          page={3}
          totalPages={5}
          hasPrev={true}
          onPageChange={onPageChange}
        />
      )

      // Act
      fireEvent.click(screen.getByText('<').closest('button')!)

      // Assert
      expect(onPageChange).toHaveBeenCalledTimes(1)
      expect(onPageChange).toHaveBeenCalledWith(2)
    })

    it('should call onPageChange with the next page when Next is clicked', () => {
      // Arrange
      const onPageChange = vi.fn()
      render(
        <Pagination
          {...defaultProps}
          page={3}
          totalPages={5}
          hasNext={true}
          onPageChange={onPageChange}
        />
      )

      // Act
      fireEvent.click(screen.getByText('>').closest('button')!)

      // Assert
      expect(onPageChange).toHaveBeenCalledTimes(1)
      expect(onPageChange).toHaveBeenCalledWith(4)
    })
  })

  // ---------------------------------------------------------------------------
  // 5. Per-page dropdown renders options and calls onPerPageChange
  // ---------------------------------------------------------------------------
  describe('per-page dropdown', () => {
    it('should render the default per-page options 10, 20, and 50', () => {
      // Arrange
      render(<Pagination {...defaultProps} />)

      // Act
      const select = screen.getByRole('combobox')
      const options = Array.from(select.querySelectorAll('option')).map(
        (opt) => Number((opt as HTMLOptionElement).value)
      )

      // Assert
      expect(options).toEqual([10, 20, 50])
    })

    it('should call onPerPageChange with 20 when "20" is selected', () => {
      // Arrange
      const onPerPageChange = vi.fn()
      render(<Pagination {...defaultProps} onPerPageChange={onPerPageChange} />)

      // Act
      fireEvent.change(screen.getByRole('combobox'), { target: { value: '20' } })

      // Assert
      expect(onPerPageChange).toHaveBeenCalledTimes(1)
      expect(onPerPageChange).toHaveBeenCalledWith(20)
    })

    it('should call onPerPageChange with 50 when "50" is selected', () => {
      // Arrange
      const onPerPageChange = vi.fn()
      render(<Pagination {...defaultProps} onPerPageChange={onPerPageChange} />)

      // Act
      fireEvent.change(screen.getByRole('combobox'), { target: { value: '50' } })

      // Assert
      expect(onPerPageChange).toHaveBeenCalledTimes(1)
      expect(onPerPageChange).toHaveBeenCalledWith(50)
    })

    it('should render custom perPageOptions when provided', () => {
      // Arrange
      render(
        <Pagination {...defaultProps} perPageOptions={[5, 25, 100]} />
      )

      // Act
      const select = screen.getByRole('combobox')
      const options = Array.from(select.querySelectorAll('option')).map(
        (opt) => Number((opt as HTMLOptionElement).value)
      )

      // Assert
      expect(options).toEqual([5, 25, 100])
    })
  })

  // ---------------------------------------------------------------------------
  // 6. "Showing X–Y of Z" text is correct
  // ---------------------------------------------------------------------------
  describe('showing range text', () => {
    it('should show "Showing 11\u201320 of 25 words" for page=2, perPage=10, total=25', () => {
      // Arrange
      render(
        <Pagination
          {...defaultProps}
          page={2}
          perPage={10}
          total={25}
          totalPages={3}
          hasPrev={true}
          hasNext={true}
        />
      )

      // Assert — the en-dash (\u2013) is used by the component
      expect(
        screen.getByText('Showing 11\u201320 of 25 words')
      ).toBeInTheDocument()
    })

    it('should show "Showing 1\u201310 of 50 words" for the first page of defaults', () => {
      // Arrange
      render(<Pagination {...defaultProps} page={1} perPage={10} total={50} />)

      // Assert
      expect(
        screen.getByText('Showing 1\u201310 of 50 words')
      ).toBeInTheDocument()
    })

    it('should cap the end value at total when last page is not full', () => {
      // Arrange — page=3, perPage=10, total=25 means items 21–25
      render(
        <Pagination
          {...defaultProps}
          page={3}
          perPage={10}
          total={25}
          totalPages={3}
          hasPrev={true}
          hasNext={false}
        />
      )

      // Assert
      expect(
        screen.getByText('Showing 21\u201325 of 25 words')
      ).toBeInTheDocument()
    })
  })

  // ---------------------------------------------------------------------------
  // 7. Ellipsis renders for large page counts
  // ---------------------------------------------------------------------------
  describe('ellipsis for large page counts', () => {
    it('should render "..." between non-consecutive page groups for page=5, totalPages=16', () => {
      // Arrange
      // getPageNumbers(5, 16) produces set {1, 4, 5, 6, 16}
      // sorted gaps: 1→4 (gap 3) and 6→16 (gap 10) both insert '...'
      // result: [1, '...', 4, 5, 6, '...', 16]
      render(
        <Pagination
          {...defaultProps}
          page={5}
          totalPages={16}
          total={160}
          hasPrev={true}
          hasNext={true}
        />
      )

      // Act
      const ellipses = screen.getAllByText('...')

      // Assert — two gaps means two ellipsis spans
      expect(ellipses).toHaveLength(2)
    })

    it('should still render all non-ellipsis page buttons when ellipsis is present', () => {
      // Arrange — expected visible pages: 1, 4, 5, 6, 16
      render(
        <Pagination
          {...defaultProps}
          page={5}
          totalPages={16}
          total={160}
          hasPrev={true}
          hasNext={true}
        />
      )

      // Assert
      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '4' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '5' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '6' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '16' })).toBeInTheDocument()
    })

    it('should not render ellipsis when all pages fit consecutively', () => {
      // Arrange — page=3, totalPages=5 produces [1,2,3,4,5] with no gaps
      render(<Pagination {...defaultProps} page={3} totalPages={5} hasPrev={true} hasNext={true} />)

      // Assert
      expect(screen.queryByText('...')).not.toBeInTheDocument()
    })
  })

  // ---------------------------------------------------------------------------
  // 8. Shows "Showing 0 of 0 words" when total is 0
  // ---------------------------------------------------------------------------
  describe('empty state', () => {
    it('should show "Showing 0 of 0 words" when total is 0', () => {
      // Arrange
      render(
        <Pagination
          {...defaultProps}
          total={0}
          totalPages={1}
          page={1}
          hasPrev={false}
          hasNext={false}
        />
      )

      // Assert
      expect(screen.getByText('Showing 0 of 0 words')).toBeInTheDocument()
    })

    it('should not render the "Showing X\u2013Y of Z" format when total is 0', () => {
      // Arrange
      render(
        <Pagination
          {...defaultProps}
          total={0}
          totalPages={1}
          page={1}
          hasPrev={false}
          hasNext={false}
        />
      )

      // Assert — the en-dash range format must be absent
      expect(
        screen.queryByText(/Showing \d+\u2013\d+ of \d+ words/)
      ).not.toBeInTheDocument()
    })
  })
})
