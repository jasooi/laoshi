import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../contexts/AuthContext'
import { settingsApi } from '../../lib/api'
import NameCard from './NameCard'
import MeetLaoshiCard from './MeetLaoshiCard'
import DecksCard from './DecksCard'
import PracticeCard from './PracticeCard'
import ReadyCard from './ReadyCard'
import ButtonSpinner from '../../components/ButtonSpinner'
import StepIndicator from './StepIndicator'

const TOTAL_STEPS = 5

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
}

const OnboardingWizard = () => {
  const navigate = useNavigate()
  const { updateUser } = useAuth()
  const [currentStep, setCurrentStep] = useState(0)
  const [preferredName, setPreferredName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [direction, setDirection] = useState(1)

  const handleNext = async () => {
    if (currentStep === 0) {
      // Save preferred name
      const trimmed = preferredName.trim()
      if (!trimmed) return
      setIsSaving(true)
      try {
        await settingsApi.updateSettings({ preferred_name: trimmed })
        updateUser({ preferred_name: trimmed })
      } catch {
        // Continue even if save fails — name can be set later in Settings
      } finally {
        setIsSaving(false)
      }
    }

    if (currentStep === TOTAL_STEPS - 1) {
      // Final card — mark onboarding complete
      setIsSaving(true)
      try {
        await settingsApi.updateSettings({ onboarding_complete: true })
        updateUser({ onboarding_complete: true })
        navigate('/home', { replace: true })
      } catch {
        // If save fails, still navigate — worst case user sees onboarding again
        navigate('/home', { replace: true })
      } finally {
        setIsSaving(false)
      }
      return
    }

    setDirection(1)
    setCurrentStep((s) => s + 1)
  }

  const handleBack = () => {
    setDirection(-1)
    setCurrentStep((s) => s - 1)
  }

  const isNextDisabled = currentStep === 0 && !preferredName.trim()

  const cards = [
    <NameCard key="name" name={preferredName} onNameChange={setPreferredName} />,
    <MeetLaoshiCard key="laoshi" name={preferredName.trim()} />,
    <DecksCard key="decks" />,
    <PracticeCard key="practice" />,
    <ReadyCard key="ready" />,
  ]

  const isLastStep = currentStep === TOTAL_STEPS - 1

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sage-tint via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg py-14 px-4 max-w-lg w-full overflow-hidden">
        {/* Content row: [back arrow] [card] [next arrow] */}
        <div className="flex items-center">
          {/* Back arrow */}
          <div className="flex-shrink-0 w-10">
            {currentStep > 0 && (
              <button
                onClick={handleBack}
                className="w-10 h-10 flex items-center justify-center text-warm-muted hover:text-warm-black transition-colors"
              >
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
          </div>

          {/* Card area */}
          <div className="flex-1 min-w-0 relative overflow-hidden">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={currentStep}
                custom={direction}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: 'easeInOut' }}
                className="w-full px-4 py-2"
              >
                {cards[currentStep]}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Next arrow */}
          <div className="flex-shrink-0 w-10">
            {!isLastStep && (
              <button
                onClick={handleNext}
                disabled={isNextDisabled || isSaving}
                className="w-10 h-10 flex items-center justify-center text-sage hover:text-sage/70 transition-colors disabled:opacity-50"
              >
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Get Started button (last step only) */}
        {isLastStep && (
          <div className="flex justify-center mt-6">
            <button
              onClick={handleNext}
              disabled={isSaving}
              className="bg-sage text-white rounded-full px-8 py-3 text-sm font-semibold hover:bg-sage/80 transition-colors disabled:opacity-50"
            >
              <span className="flex items-center justify-center gap-2">
                {isSaving && <ButtonSpinner />}
                {isSaving ? 'Saving...' : 'Get Started'}
              </span>
            </button>
          </div>
        )}

        {/* Step indicator */}
        <div className="mt-6">
          <StepIndicator currentStep={currentStep} totalSteps={TOTAL_STEPS} />
        </div>
      </div>
    </div>
  )
}

export default OnboardingWizard
