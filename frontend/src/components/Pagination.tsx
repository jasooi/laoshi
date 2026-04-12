interface PaginationProps {
  page: number
  totalPages: number
  total: number
  perPage: number
  hasNext: boolean
  hasPrev: boolean
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
  perPageOptions?: number[]
}

function getPageNumbers(page: number, totalPages: number): (number | '...')[] {
  if (totalPages <= 0) return []
  if (totalPages === 1) return [1]

  const pages = new Set<number>()

  // Always include first and last page
  pages.add(1)
  pages.add(totalPages)

  // Always include current page and its neighbors
  pages.add(page)
  if (page - 1 >= 1) pages.add(page - 1)
  if (page + 1 <= totalPages) pages.add(page + 1)

  // Sort and insert ellipsis for gaps of 2+
  const sorted = Array.from(pages).sort((a, b) => a - b)
  const result: (number | '...')[] = []

  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] >= 2) {
      result.push('...')
    }
    result.push(sorted[i])
  }

  return result
}

const Pagination = ({
  page,
  totalPages,
  total,
  perPage,
  hasNext,
  hasPrev,
  onPageChange,
  onPerPageChange,
  perPageOptions = [10, 20, 50],
}: PaginationProps) => {
  const start = total === 0 ? 0 : (page - 1) * perPage + 1
  const end = Math.min(page * perPage, total)

  const pageNumbers = getPageNumbers(page, totalPages)

  return (
    <div className="px-4 py-3 flex items-center justify-between">
      {/* Left: item count */}
      <span className="text-sm text-warm-muted">
        {total === 0
          ? 'Showing 0 of 0 words'
          : `Showing ${start}\u2013${end} of ${total} words`}
      </span>

      {/* Center: page navigation */}
      <div className="flex items-center gap-1">
        {/* Previous button */}
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrev}
          className={`px-3 py-1.5 text-sm rounded-lg ${
            hasPrev
              ? 'text-warm-black hover:bg-warm-offwhite'
              : 'text-warm-muted/50 cursor-not-allowed'
          }`}
        >
          &lt;
        </button>

        {/* Page number buttons */}
        {pageNumbers.map((item, index) =>
          item === '...' ? (
            <span
              key={`ellipsis-${index}`}
              className="px-3 py-1.5 text-sm text-warm-muted"
            >
              ...
            </span>
          ) : (
            <button
              key={item}
              onClick={() => onPageChange(item)}
              className={`px-3 py-1.5 text-sm min-w-[2rem] rounded-lg ${
                item === page
                  ? 'bg-sage text-white'
                  : 'border border-warm-gray text-warm-black hover:bg-warm-offwhite'
              }`}
            >
              {item}
            </button>
          )
        )}

        {/* Next button */}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
          className={`px-3 py-1.5 text-sm rounded-lg ${
            hasNext
              ? 'text-warm-black hover:bg-warm-offwhite'
              : 'text-warm-muted/50 cursor-not-allowed'
          }`}
        >
          &gt;
        </button>
      </div>

      {/* Right: per-page selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm text-warm-muted">Per page:</label>
        <select
          value={perPage}
          onChange={(e) => onPerPageChange(Number(e.target.value))}
          className="text-sm border border-warm-gray rounded-lg px-2 py-1.5 text-warm-black focus:outline-none focus:ring-2 focus:ring-sage"
        >
          {perPageOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default Pagination
