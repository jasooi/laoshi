import laoshiLogo from '../../assets/laoshi-logo.png'
import { useHome } from './HomeContext'

export default function EmptyDeckPlaceholder() {
  const { deckCount } = useHome()

  return (
    <div className="h-full flex items-center justify-center bg-warm-offwhite p-8">
      <div className="flex flex-col items-center text-center">
        {/* Laoshi logo */}
        <img
          src={laoshiLogo}
          alt="Laoshi"
          className="w-40 h-40 rounded-full object-cover mb-8"
        />

        {/* Conditional title */}
        <h2 className="text-2xl font-bold text-warm-black mb-2">
          {deckCount === 0 ? '\u{1F448} Add a deck to begin' : '\u{1F448} Select a deck to begin'}
        </h2>

        {/* Subtitle */}
        <p className="text-lg text-warm-muted">
          Laoshi is waiting for you in the classroom.
        </p>
      </div>
    </div>
  )
}
