/** @type {import('tailwindcss').Config} */
/*
 * Border Radius Scale (based on --radius = 0.5rem / 8px):
 * - sm: 4px (calc(var(--radius) - 4px))
 * - md: 6px (calc(var(--radius) - 2px))
 * - lg: 8px (var(--radius))
 *
 * Usage Guidelines:
 * - Buttons: rounded-lg (8px)
 * - Cards: rounded-xl (12px) or rounded-2xl (16px)
 * - Modals: rounded-xl (12px)
 * - Inputs: rounded-lg (8px)
 * - Avatars/Icons: rounded-full
 * - Small elements: rounded-md (6px)
 *
 * Direct Tailwind classes used: rounded-lg, rounded-xl, rounded-2xl, rounded-full
 * Custom classes available: rounded-lg, rounded-md, rounded-sm (from --radius)
 */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-fira-code)", "monospace"],
      },
      colors: {
        background: 'rgb(var(--background) / <alpha-value>)',
        foreground: 'rgb(var(--foreground) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--primary) / <alpha-value>)',
          foreground: 'rgb(var(--primary-foreground) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'rgb(var(--secondary) / <alpha-value>)',
          foreground: 'rgb(var(--secondary-foreground) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'rgb(var(--muted) / <alpha-value>)',
          foreground: 'rgb(var(--muted-foreground) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent) / <alpha-value>)',
          foreground: 'rgb(var(--accent-foreground) / <alpha-value>)',
        },
        border: 'rgb(var(--border) / <alpha-value>)',
        input: 'rgb(var(--input) / <alpha-value>)',
        ring: 'rgb(var(--ring) / <alpha-value>)',
        agent: {
          master: 'rgb(var(--agent-master) / <alpha-value>)',
          planner: 'rgb(var(--agent-planner) / <alpha-value>)',
          researcher: 'rgb(var(--agent-researcher) / <alpha-value>)',
          tools: 'rgb(var(--agent-tools) / <alpha-value>)',
          database: 'rgb(var(--agent-database) / <alpha-value>)',
        }
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      }
    },
  },
  plugins: [],
}
