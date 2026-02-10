import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders the Welcome page at root route', () => {
    render(<App />)
    expect(screen.getByText('Welcome to the classroom')).toBeInTheDocument()
  })
})
