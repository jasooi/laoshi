import { useEffect, useState, useRef } from 'react'
import laoshiLogo from '../../assets/laoshi-logo.png'

const MESSAGES = [
  'Digging up the scrolls...',
  'Preparing the tea...',
  'Lighting the candles...',
  'Setting the mood...',
]

const MESSAGE_DURATION = 1200

interface LoadingRitualProps {
  onReady: () => void
}

export default function LoadingRitual({ onReady }: LoadingRitualProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const [visible, setVisible] = useState(true)
  const onReadyRef = useRef(onReady)
  onReadyRef.current = onReady

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex(prev => {
        const next = prev + 1
        if (next >= MESSAGES.length) {
          clearInterval(interval)
          setTimeout(() => {
            setVisible(false)
            setTimeout(() => onReadyRef.current(), 300)
          }, MESSAGE_DURATION)
          return prev
        }
        return next
      })
    }, MESSAGE_DURATION)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      className={`h-full flex flex-col items-center justify-center bg-warm-offwhite transition-opacity duration-300 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {/* Pulsing Laoshi logo */}
      <div className="w-32 h-32 rounded-2xl shadow-lg bg-white flex items-center justify-center mb-8 animate-pulse-scale">
        <img src={laoshiLogo} alt="Laoshi" className="w-24 h-24 object-contain" />
      </div>

      {/* Rotating message */}
      <div className="h-8 flex items-center justify-center">
        <p
          key={messageIndex}
          className="font-serif text-lg text-warm-black/60 animate-fade-in"
        >
          {MESSAGES[messageIndex]}
        </p>
      </div>
    </div>
  )
}
