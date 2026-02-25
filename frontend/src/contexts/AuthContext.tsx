import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import api, { setAccessToken, setOnRefreshFailure } from '../lib/api'
import axios from 'axios'

interface User {
  id: number
  username: string
  preferred_name: string | null
}

interface AuthContextType {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Update the Axios module token whenever React state changes
  useEffect(() => {
    setAccessToken(token)
  }, [token])

  // Logout handler (also used as refresh failure callback)
  const handleLogout = useCallback(() => {
    setToken(null)
    setUser(null)
    setAccessToken(null)
  }, [])

  // Register the refresh failure callback with the Axios interceptor
  useEffect(() => {
    setOnRefreshFailure(handleLogout)
  }, [handleLogout])

  // Silent refresh on mount -- replaces the localStorage check
  useEffect(() => {
    const silentRefresh = async () => {
      try {
        const refreshResponse = await axios.post(
          '/api/token/refresh',
          {},
          { withCredentials: true }
        )
        const newAccessToken = refreshResponse.data.access_token
        setToken(newAccessToken)
        setAccessToken(newAccessToken)

        // Fetch user info
        const userResponse = await api.get('/api/me')
        setUser(userResponse.data)
      } catch {
        // No valid refresh cookie -- user is not logged in
        setToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    silentRefresh()
  }, [])

  const login = async (username: string, password: string) => {
    // POST /api/token with withCredentials so the refresh cookie is set
    const response = await api.post('/api/token', { username, password }, {
      withCredentials: true,
    })
    const accessToken = response.data.access_token
    setToken(accessToken)
    setAccessToken(accessToken)

    // Fetch user info
    const userResponse = await api.get('/api/me')
    setUser(userResponse.data)
  }

  const logout = async () => {
    try {
      await axios.post('/api/token/revoke', {}, { withCredentials: true })
    } catch {
      // Even if revoke fails, clear local state
    }
    handleLogout()
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
