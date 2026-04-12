import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { practiceApi } from '../lib/api'
import { AlertTriangle } from 'lucide-react'
import ButtonSpinner from './ButtonSpinner'

const STORAGE_KEY = 'laoshi_active_session'

function getActiveSession(): { sessionId: number } | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return null
    return JSON.parse(saved)
  } catch {
    return null
  }
}

interface SidebarProps {
  currentPath: string
}

interface SidebarItem {
  path: string
  label: string
  icon: JSX.Element
}

const Sidebar = ({ currentPath }: SidebarProps) => {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [showEndModal, setShowEndModal] = useState(false)
  const [pendingPath, setPendingPath] = useState<string | null>(null)
  const [ending, setEnding] = useState(false)

  const handleNavClick = (e: React.MouseEvent, path: string) => {
    // If already on the target path and not in a session, let it through
    if (currentPath === path && !getActiveSession()) return

    const session = getActiveSession()
    if (session) {
      e.preventDefault()
      setPendingPath(path)
      setShowEndModal(true)
    }
    // If no session, the Link navigates normally
  }

  const handleConfirmEnd = async () => {
    const session = getActiveSession()
    setEnding(true)
    try {
      if (session) {
        await practiceApi.endSession(session.sessionId)
      }
    } catch (error) {
      console.error('Failed to end session:', error)
    } finally {
      localStorage.removeItem(STORAGE_KEY)
      window.dispatchEvent(new Event('laoshi_session_ended'))
      setEnding(false)
      setShowEndModal(false)
      if (pendingPath) {
        navigate(pendingPath)
        setPendingPath(null)
      }
    }
  }

  const handleCancelEnd = () => {
    setShowEndModal(false)
    setPendingPath(null)
  }

  const handleLogout = async () => {
    const session = getActiveSession()
    if (session) {
      setPendingPath('__logout__')
      setShowEndModal(true)
      return
    }
    await logout()
    navigate('/login')
  }

  const handleConfirmEndAndLogout = async () => {
    const session = getActiveSession()
    setEnding(true)
    try {
      if (session) {
        await practiceApi.endSession(session.sessionId)
      }
    } catch (error) {
      console.error('Failed to end session:', error)
    } finally {
      localStorage.removeItem(STORAGE_KEY)
      window.dispatchEvent(new Event('laoshi_session_ended'))
      setEnding(false)
      setShowEndModal(false)
      setPendingPath(null)
      await logout()
      navigate('/login')
    }
  }

  const sidebarItems: SidebarItem[] = [
    {
      path: '/home',
      label: 'Home',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      path: '/library',
      label: 'Library',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      ),
    },
    {
      path: '/progress',
      label: 'Report Card',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      path: '/settings',
      label: 'Settings',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
  ]

  return (
    <>
      <aside className="w-20 bg-white border-r border-warm-gray flex flex-col items-center py-6">
        {/* Navigation Items */}
        <div className="space-y-4">
          {sidebarItems.map((item) => {
            const isActive = currentPath === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={(e) => handleNavClick(e, item.path)}
                className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                  isActive
                    ? 'bg-sage-tint text-sage'
                    : 'text-warm-muted hover:text-warm-black hover:bg-warm-offwhite'
                }`}
                title={item.label}
              >
                {item.icon}
              </Link>
            )
          })}
        </div>

        {/* Logout Button -- pushed to bottom */}
        <button
          onClick={handleLogout}
          className="mt-auto w-12 h-12 rounded-xl flex items-center justify-center text-warm-muted hover:text-red-500 hover:bg-red-50 transition-all"
          title="Log out"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
        </button>
      </aside>

      {/* End Session Confirmation Modal */}
      {showEndModal && (
        <div className="fixed inset-0 z-[60] bg-warm-black/20 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-yellow-600" />
              </div>
              <h3 className="text-xl font-medium text-warm-black">End Current Session?</h3>
            </div>
            <p className="text-base text-warm-black/60 leading-relaxed mb-8">
              You have an active practice session. Ending it will save your progress so far. Are you sure you want to continue?
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={handleCancelEnd}
                disabled={ending}
                className="px-6 py-2.5 text-warm-black/60 hover:text-warm-black font-medium transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={pendingPath === '__logout__' ? handleConfirmEndAndLogout : handleConfirmEnd}
                disabled={ending}
                className="flex items-center gap-2 px-6 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl shadow-sm font-medium transition-colors disabled:opacity-50"
              >
                {ending && <ButtonSpinner />}
                {ending ? 'Ending...' : 'End Session'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default Sidebar
