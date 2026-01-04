import { Sun, Moon, Settings } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

export default function Header() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="h-14 border-b flex items-center justify-end px-4 gap-2">
      <button 
        onClick={toggleTheme}
        className="p-2 rounded-lg hover:bg-accent transition-colors"
        title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      >
        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
      </button>
      
      <button 
        className="p-2 rounded-lg hover:bg-accent transition-colors"
        title="Settings"
      >
        <Settings size={18} />
      </button>
    </header>
  )
}
