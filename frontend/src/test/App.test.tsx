import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import App from '../App'

// Mock the AuthContext to simulate authenticated user
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../contexts/AuthContext')
  return {
    ...actual,
    useAuth: () => ({
      login: vi.fn(),
      logout: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, username: 'testuser', preferred_name: null },
      token: 'test-token',
    }),
  }
})

describe('App', () => {
  it('renders the Welcome page at root route when authenticated', () => {
    render(<App />)
    expect(screen.getByText('Welcome to the classroom')).toBeInTheDocument()
  })
})
