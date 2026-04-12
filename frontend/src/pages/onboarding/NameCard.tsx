interface NameCardProps {
  name: string
  onNameChange: (name: string) => void
}

const NameCard = ({ name, onNameChange }: NameCardProps) => (
  <div className="text-center space-y-6">
    <h2 className="text-2xl font-bold text-warm-black">What should Laoshi call you?</h2>
    <div className="p-2">
      <input
        type="text"
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder="Your name"
        maxLength={80}
        autoFocus
        className="w-full text-center text-lg px-4 py-3 rounded-xl border border-warm-gray/30 focus:outline-none focus:ring-2 focus:ring-sage bg-warm-white text-warm-black placeholder:text-warm-muted/50"
      />
    </div>
  </div>
)

export default NameCard
