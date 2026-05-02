import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { renderMarkdown } from '../utils/markdown'

describe('renderMarkdown', () => {
  it('renders bold text correctly', () => {
    const { container } = render(
      <div>{renderMarkdown('This is **bold text** in a sentence')}</div>
    )
    const strong = container.querySelector('strong')
    expect(strong).toBeTruthy()
    expect(strong?.textContent).toBe('bold text')
  })

  it('renders multiple bold texts', () => {
    const { container } = render(
      <div>{renderMarkdown('**First** and **Second** bold')}</div>
    )
    const strongs = container.querySelectorAll('strong')
    expect(strongs).toHaveLength(2)
    expect(strongs[0].textContent).toBe('First')
    expect(strongs[1].textContent).toBe('Second')
  })

  it('renders bullet points as list items', () => {
    const text = `- First item
- Second item
- Third item`
    const { container } = render(<div>{renderMarkdown(text)}</div>)
    const ul = container.querySelector('ul')
    const lis = container.querySelectorAll('li')
    expect(ul).toBeTruthy()
    expect(lis).toHaveLength(3)
    expect(lis[0].textContent).toBe('First item')
    expect(lis[1].textContent).toBe('Second item')
    expect(lis[2].textContent).toBe('Third item')
  })

  it('renders bullet points with bold text', () => {
    const text = `- First **bold** item
- Second **bold** item`
    const { container } = render(<div>{renderMarkdown(text)}</div>)
    const lis = container.querySelectorAll('li')
    const strongs = container.querySelectorAll('strong')
    expect(lis).toHaveLength(2)
    expect(strongs).toHaveLength(2)
    expect(strongs[0].textContent).toBe('bold')
    expect(strongs[1].textContent).toBe('bold')
  })

  it('renders mixed paragraphs and bullet points', () => {
    const text = `This is a paragraph with **bold**.

- Bullet one
- Bullet two

Another paragraph.`
    const { container } = render(<div>{renderMarkdown(text)}</div>)
    const ps = container.querySelectorAll('p')
    const ul = container.querySelector('ul')
    const lis = container.querySelectorAll('li')

    expect(ps.length).toBeGreaterThanOrEqual(2)
    expect(ul).toBeTruthy()
    expect(lis).toHaveLength(2)
  })

  it('handles empty text', () => {
    const { container } = render(<div>{renderMarkdown('')}</div>)
    expect(container.firstChild?.childNodes.length).toBe(0)
  })

  it('handles plain text without markdown', () => {
    const { container } = render(<div>{renderMarkdown('Plain text')}</div>)
    const p = container.querySelector('p')
    expect(p).toBeTruthy()
    expect(p?.textContent).toBe('Plain text')
  })
})
