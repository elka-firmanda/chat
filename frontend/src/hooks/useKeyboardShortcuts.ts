import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../stores/chatStore'
import { useSettingsStore } from '../stores/settingsStore'

type KeyboardShortcutHandler = () => void

interface ShortcutConfig {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  handler: KeyboardShortcutHandler
  description: string
}

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { toggleDeepSearch, setActiveSession } = useChatStore()
  const { setShortcutsOpen } = useSettingsStore()

  const handleNewChat = useCallback(() => {
    setActiveSession(null)
    navigate('/')
  }, [setActiveSession, navigate])

  const handleOpenSettings = useCallback(() => {
    navigate('/settings')
  }, [navigate])

  const handleToggleDeepSearch = useCallback(() => {
    toggleDeepSearch()
  }, [toggleDeepSearch])

  const handleShowShortcuts = useCallback(() => {
    setShortcutsOpen(true)
  }, [setShortcutsOpen])

  const handleGoHome = useCallback(() => {
    navigate('/')
  }, [navigate])

  const shortcuts: ShortcutConfig[] = [
    {
      key: 'n',
      meta: true,
      handler: handleNewChat,
      description: 'New chat'
    },
    {
      key: 'n',
      ctrl: true,
      handler: handleNewChat,
      description: 'New chat'
    },
    {
      key: ',',
      meta: true,
      handler: handleOpenSettings,
      description: 'Open settings'
    },
    {
      key: ',',
      ctrl: true,
      handler: handleOpenSettings,
      description: 'Open settings'
    },
    {
      key: '/',
      meta: true,
      handler: handleToggleDeepSearch,
      description: 'Toggle deep search'
    },
    {
      key: '/',
      ctrl: true,
      handler: handleToggleDeepSearch,
      description: 'Toggle deep search'
    },
    {
      key: '?',
      meta: true,
      shift: true,
      handler: handleShowShortcuts,
      description: 'Show keyboard shortcuts'
    },
    {
      key: '?',
      ctrl: true,
      shift: true,
      handler: handleShowShortcuts,
      description: 'Show keyboard shortcuts'
    },
    {
      key: 'Escape',
      handler: handleGoHome,
      description: 'Go to home'
    }
  ]

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore keyboard events when typing in input fields
      const target = event.target as HTMLElement
      const isInputField = target.tagName === 'INPUT' || 
                          target.tagName === 'TEXTAREA' ||
                          target.isContentEditable

      // Allow Escape even in input fields for consistency
      if (isInputField && event.key !== 'Escape') {
        return
      }

      // Don't trigger shortcuts when user is composing text (e.g., IME)
      if (event.isComposing) {
        return
      }

      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey : !event.ctrlKey && !event.metaKey
        const metaMatch = shortcut.meta ? event.metaKey : true
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
        const altMatch = shortcut.alt ? event.altKey : !event.altKey
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()

        if (ctrlMatch && metaMatch && shiftMatch && altMatch && keyMatch) {
          event.preventDefault()
          shortcut.handler()
          return
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleNewChat, handleOpenSettings, handleToggleDeepSearch, handleGoHome, shortcuts])

  return shortcuts
}

export default useKeyboardShortcuts
