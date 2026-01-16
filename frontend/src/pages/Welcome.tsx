import { useNavigate } from 'react-router-dom'

const Welcome = () => {
  const navigate = useNavigate()

  const handleGetStarted = () => {
    navigate('/vocabulary')
  }

  const handleSkipClick = () => {
    navigate('/home')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 via-pink-50 to-blue-100 p-4">
      <div className="bg-white rounded-3xl shadow-lg p-12 max-w-md w-full text-center">
        {/* Rocket Icon */}
        <div className="mb-8 relative inline-block">
          <div className="text-6xl">
            <svg
              className="w-24 h-24 mx-auto"
              viewBox="0 0 100 100"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Rocket body */}
              <path
                d="M50 10 L60 40 L60 70 L50 80 L40 70 L40 40 Z"
                fill="#9333EA"
                stroke="#9333EA"
                strokeWidth="2"
              />
              {/* Rocket window */}
              <circle cx="50" cy="35" r="6" fill="#E9D5FF" />
              {/* Rocket fins */}
              <path d="M40 50 L30 60 L40 65 Z" fill="#A855F7" />
              <path d="M60 50 L70 60 L60 65 Z" fill="#A855F7" />
              {/* Rocket flame */}
              <path d="M45 80 L50 90 L55 80" fill="#F59E0B" />
            </svg>
          </div>

          {/* Sparkles */}
          <div className="absolute top-2 right-0 text-purple-500 text-2xl animate-pulse">✨</div>
          <div className="absolute top-8 right-12 text-purple-500 text-xl animate-pulse delay-75">✨</div>
          <div className="absolute bottom-4 left-2 text-purple-400 text-lg animate-pulse delay-150">✨</div>
        </div>

        {/* Heading */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to the classroom
        </h1>

        {/* Subheading */}
        <p className="text-gray-600 mb-8 text-lg">
          Let's start by adding some words you'd like to learn
        </p>

        {/* Get Started Button */}
        <button
          onClick={handleGetStarted}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 px-8 rounded-full mb-4 transition-colors shadow-md"
        >
          Get started
        </button>

        {/* Skip Link */}
        <button
          onClick={handleSkipClick}
          className="text-gray-500 hover:text-gray-700 font-medium transition-colors"
        >
          Skip for now
        </button>
      </div>
    </div>
  )
}

export default Welcome
