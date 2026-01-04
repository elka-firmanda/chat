/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Agent-specific colors for thinking blocks
        agent: {
          master: '#8b5cf6',     // Purple
          planner: '#3b82f6',    // Blue
          researcher: '#22c55e', // Green
          tools: '#f97316',      // Orange
          database: '#ec4899',   // Pink
        }
      }
    },
  },
  plugins: [],
}
