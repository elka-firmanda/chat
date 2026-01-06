import { useState, useEffect, useCallback } from 'react'

export type Theme = 'light' | 'dark' | 'system'

const THEME_STORAGE_KEY = 'theme'
const SYSTEM_THEME_STORAGE_KEY = 'system-theme'

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyThemeToDocument(theme: Theme) {
  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme
  const root = document.documentElement

  if (resolvedTheme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }

  root.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>('system')
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null

    if (storedTheme && ['light', 'dark', 'system'].includes(storedTheme)) {
      setTheme(storedTheme)
      const resolved = storedTheme === 'system' ? getSystemTheme() : storedTheme
      setResolvedTheme(resolved)
      applyThemeToDocument(storedTheme)
    } else {
      const systemTheme = getSystemTheme()
      setResolvedTheme(systemTheme)
      applyThemeToDocument('system')
    }

    setIsInitialized(true)
  }, [])

  useEffect(() => {
    if (!isInitialized) return

    applyThemeToDocument(theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)

    const resolved = theme === 'system' ? getSystemTheme() : theme
    setResolvedTheme(resolved)
    localStorage.setItem(SYSTEM_THEME_STORAGE_KEY, resolved)
  }, [theme, isInitialized])

  useEffect(() => {
    if (!isInitialized || theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const newSystemTheme = getSystemTheme()
      setResolvedTheme(newSystemTheme)
      applyThemeToDocument('system')
      localStorage.setItem(SYSTEM_THEME_STORAGE_KEY, newSystemTheme)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, isInitialized])

  const setThemeMode = useCallback((newTheme: Theme) => {
    setTheme(newTheme)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      if (prev === 'light') return 'dark'
      if (prev === 'dark') return 'system'
      return 'light'
    })
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
  if (stored && ['light', 'dark', 'system'].includes(stored)) {
    return stored
  }
  return null
}
