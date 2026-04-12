import { useState, useEffect } from 'react'

const Header = () => {
  const [greeting, setGreeting] = useState('')
  const [timeIcon, setTimeIcon] = useState('🌅')

  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) {
      setGreeting('Good morning')
      setTimeIcon('🌅')
    } else if (hour < 18) {
      setGreeting('Good afternoon')
      setTimeIcon('☀️')
    } else {
      setGreeting('Good evening')
      setTimeIcon('🌙')
    }
  }, [])

  return (
    <header className="h-16 border-b border-warm-gray px-6 flex items-center justify-between bg-white">
      <div className="flex items-center gap-3">
        <span className="text-2xl" role="img" aria-label="time">
          {timeIcon}
        </span>
        <h1 className="text-lg font-semibold text-warm-black">{greeting}</h1>
      </div>
      <div className="text-sm text-warm-muted">
        Mastery: <span className="font-medium text-primary">0%</span>
      </div>
    </header>
  )
}

export default Header

