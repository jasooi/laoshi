import { Fragment } from 'react'

/**
 * Simple markdown renderer for session summary text.
 * Supports:
 * - **bold text** → <strong>bold text</strong>
 * - Bullet points (lines starting with -)
 * - Line breaks
 */
export function renderMarkdown(text: string): JSX.Element {
  if (!text) return <></>

  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  let bulletItems: JSX.Element[] = []

  const flushBulletList = () => {
    if (bulletItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc pl-5 space-y-1">
          {bulletItems}
        </ul>
      )
      bulletItems = []
    }
  }

  lines.forEach((line, lineIdx) => {
    const trimmedLine = line.trim()

    // Skip empty lines
    if (!trimmedLine) {
      flushBulletList()
      return
    }

    // Check if line is a bullet point
    const bulletMatch = trimmedLine.match(/^[-*]\s+(.+)$/)
    if (bulletMatch) {
      const bulletText = bulletMatch[1]
      bulletItems.push(
        <li key={`bullet-${lineIdx}`}>
          {renderInlineMarkdown(bulletText)}
        </li>
      )
      return
    }

    // Regular paragraph line
    flushBulletList()
    elements.push(
      <p key={`p-${lineIdx}`} className="mb-2 last:mb-0">
        {renderInlineMarkdown(trimmedLine)}
      </p>
    )
  })

  // Flush any remaining bullet items
  flushBulletList()

  return <>{elements}</>
}

/**
 * Renders inline markdown formatting (bold text).
 * Converts **text** to <strong>text</strong>
 */
function renderInlineMarkdown(text: string): JSX.Element {
  const parts: (string | JSX.Element)[] = []
  let key = 0

  // Match **bold text**
  const boldRegex = /\*\*(.+?)\*\*/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = boldRegex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    // Add bold text
    parts.push(
      <strong key={`bold-${key++}`} className="font-semibold">
        {match[1]}
      </strong>
    )

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return (
    <>
      {parts.map((part, idx) =>
        typeof part === 'string' ? <Fragment key={`frag-${idx}`}>{part}</Fragment> : part
      )}
    </>
  )
}
