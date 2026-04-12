interface MeetLaoshiCardProps {
  name: string
}

const MeetLaoshiCard = ({ name }: MeetLaoshiCardProps) => (
  <div className="text-center space-y-6">
    <h2 className="text-2xl font-bold text-warm-black">
      你好, {name || 'friend'}! 👋
    </h2>
    <p className="text-warm-muted leading-relaxed">
      Laoshi is your Mandarin flashcard tutor in chat form. Here's how it works.
    </p>
  </div>
)

export default MeetLaoshiCard
