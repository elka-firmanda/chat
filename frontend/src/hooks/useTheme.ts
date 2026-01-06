import { useState, useEffect, useCallback } from 'react'

export type Theme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'theme'

function applyThemeToDocument(theme: Theme) {
  const root = document.documentElement

  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }

  root.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>('light')
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null

    if (storedTheme && ['light', 'dark'].includes(storedTheme)) {
      setTheme(storedTheme)
      setResolvedTheme(storedTheme)
      applyThemeToDocument(storedTheme)
    } else {
      setResolvedTheme('light')
      applyThemeToDocument('light')
    }

    setIsInitialized(true)
  }, [])

  useEffect(() => {
    if (!isInitialized) return

    applyThemeToDocument(theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)
    setResolvedTheme(theme)
  }, [theme, isInitialized])

  const setThemeMode = useCallback((newTheme: Theme) => {
    setTheme(newTheme)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light')
  }, [])

  return {
    theme,
    setTheme: setThemeMode,
    toggleTheme,
    resolvedTheme,
    isInitialized
  }
}

export function getStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null
  const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null
  if (stored && ['light', 'dark'].includes(stored)) {
    return stored
  }
  return null
}
