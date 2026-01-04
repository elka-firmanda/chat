import { Sun, Moon, Settings } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { useState } from 'react'
import SettingsModal from '../settings/SettingsModal'

export default function Header() {
  const { theme, toggleTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <button 
        onClick={toggleTheme}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      >
        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
      </button>
      
      <button 
        onClick={() => setSettingsOpen(true)}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title="Settings"
      >
        <Settings size={18} />
      </button>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  )
}
