/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        page: '#0D1117',
        panel: '#161B22',
        border: '#21262D',
        text: '#E6EDF3',
        secondary: '#8B949E',
        brand: '#8B5CF6',
        critical: '#F85149',
        high: '#FF8C42',
        medium: '#E3B341',
        low: '#58A6FF',
        safe: '#3FB950',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
