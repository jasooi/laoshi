import { Link } from 'react-router-dom'

interface SidebarProps {
  currentPath: string
}

interface SidebarItem {
  path: string
  icon: string
  label: string
}

const sidebarItems: SidebarItem[] = [
  { path: '/', icon: '🏠', label: 'Home' },
  { path: '/progress', icon: '📊', label: 'Progress Dashboard' },
  { path: '/vocabulary', icon: '📚', label: 'Vocabulary' },
  { path: '/files', icon: '📁', label: 'Files' },
  { path: '/settings', icon: '⚙️', label: 'Settings' },
]

const Sidebar = ({ currentPath }: SidebarProps) => {
  return (
    <aside className="w-16 bg-white border-r border-gray-200 flex flex-col items-center py-4 space-y-2">
      {sidebarItems.map((item) => {
        const isActive = currentPath === item.path
        return (
          <Link
            key={item.path}
            to={item.path}
            className={`sidebar-icon ${isActive ? 'active' : ''}`}
            title={item.label}
          >
            <span className="text-xl" role="img" aria-label={item.label}>
              {item.icon}
            </span>
          </Link>
        )
      })}
    </aside>
  )
}

export default Sidebar

