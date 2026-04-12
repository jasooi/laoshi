import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import OnboardingWizard from './onboarding/OnboardingWizard'

const Welcome = () => {
  const { user } = useAuth()

  // Existing users who completed onboarding go straight to home
  if (user?.onboarding_complete) {
    return <Navigate to="/home" replace />
  }

  // New users see the onboarding wizard
  return <OnboardingWizard />
}

export default Welcome
