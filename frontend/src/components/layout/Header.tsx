import { Sun, Moon, Monitor, Settings, Keyboard } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { useState } from 'react'
import SettingsModal from '../settings/SettingsModal'
import { useSettingsStore } from '../../stores/settingsStore'
import KeyboardShortcutsHelp from '../ui/KeyboardShortcutsHelp'

export default function Header() {
  const { theme, toggleTheme, resolvedTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { shortcutsOpen, setShortcutsOpen } = useSettingsStore()

  const getThemeIcon = () => {
    if (theme === 'system') return <Monitor size={18} />
    return resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />
  }

  const getThemeTitle = () => {
    if (theme === 'light') return 'Switch to dark mode'
    if (theme === 'dark') return 'Switch to system preference'
    return 'Switch to light mode'
  }

  return (
    <>
      <button
        onClick={toggleTheme}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title={getThemeTitle()}
      >
        {getThemeIcon()}
      </button>

      <button
        onClick={() => setShortcutsOpen(true)}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors relative"
        title="Keyboard shortcuts (?)"
      >
        <Keyboard size={18} />
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary text-primary-foreground text-[10px] font-bold rounded-full flex items-center justify-center">
          ?
        </span>
      </button>

      <button
        onClick={() => setSettingsOpen(true)}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title="Settings"
      >
        <Settings size={18} />
      </button>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
      <KeyboardShortcutsHelp isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </>
  )
}
