interface StepIndicatorProps {
  currentStep: number
  totalSteps: number
}

const StepIndicator = ({ currentStep, totalSteps }: StepIndicatorProps) => (
  <div className="flex justify-center gap-2">
    {Array.from({ length: totalSteps }, (_, i) => (
      <div
        key={i}
        className={`h-2 rounded-full transition-all duration-300 ${
          i === currentStep ? 'w-6 bg-sage' : 'w-2 bg-warm-gray'
        }`}
      />
    ))}
  </div>
)

export default StepIndicator
