/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./frontend/src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Force generate critical color classes that Tailwind JIT might miss
    'bg-sage',
    'text-sage',
    'border-sage',
    'ring-sage',
    'bg-sage-tint',
    'text-sage-tint',
    'border-sage-tint',
    'bg-amber',
    'text-amber',
    'border-amber',
    'bg-amber-tint',
    'text-amber-tint',
    'bg-coral',
    'text-coral',
    'border-coral',
    'bg-coral-tint',
    'text-coral-tint',
    'bg-neutral',
    'text-neutral',
    'border-neutral',
    'bg-neutral-tint',
    'text-neutral-tint',
    'bg-warm-offwhite',
    'text-warm-black',
    'text-warm-muted',
    'bg-warm-gray',
    'border-warm-gray',
    'bg-chat-bg',
  ],
  theme: {
    extend: {
      colors: {
        chat: {
          bg: '#F5F3EE',
        },
        warm: {
          offwhite: '#FAFAF8',
          black: '#2A2A28',
          gray: '#E8E5E0',
          muted: '#8A8A86',
        },
        sage: {
          DEFAULT: '#6B8F71',
          tint: '#EDF2EE',
        },
        amber: {
          DEFAULT: '#C4973B',
          tint: '#FBF5E8',
        },
        coral: {
          DEFAULT: '#D4715E',
          tint: '#FDF0ED',
        },
        neutral: {
          DEFAULT: '#A8A5A0',
          tint: '#F2F1EF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Lora', 'serif'],
      },
    },
  },
  plugins: [],
}
