import { Sun, Moon, Monitor, Settings, Zap, Search, ChevronDown, Keyboard, Loader2, AlertCircle } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { useState, useEffect, useRef } from 'react'
import SettingsModal from '../settings/SettingsModal'
import { useSettingsStore } from '../../stores/settingsStore'
import KeyboardShortcutsHelp from '../ui/KeyboardShortcutsHelp'

const PROFILE_INFO = {
  fast: { label: 'Fast', icon: Zap, color: 'text-green-600', bg: 'bg-green-100' },
  deep: { label: 'Deep', icon: Search, color: 'text-purple-600', bg: 'bg-purple-100' },
}

export default function Header() {
  const { theme, toggleTheme, resolvedTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [switchingProfile, setSwitchingProfile] = useState<string | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const { currentProfile, loadProfiles, applyProfile, shortcutsOpen, setShortcutsOpen } = useSettingsStore()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadProfiles()
  }, [loadProfiles])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleProfileSwitch = async (profile: string) => {
    setSwitchingProfile(profile)
    setProfileError(null)
    try {
      await applyProfile(profile)
      setProfileMenuOpen(false)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to switch profile'
      setProfileError(errorMessage)
    } finally {
      setSwitchingProfile(null)
    }
  }

  const currentProfileInfo = currentProfile ? PROFILE_INFO[currentProfile as keyof typeof PROFILE_INFO] : null

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
      {currentProfileInfo && (
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            className={`min-h-[44px] min-w-[44px] flex items-center gap-1.5 px-2 rounded-lg hover:bg-accent transition-colors ${currentProfileInfo.bg}`}
            title="Profile settings"
          >
            <currentProfileInfo.icon size={16} className={currentProfileInfo.color} />
            <span className={`text-xs font-medium ${currentProfileInfo.color}`}>
              {currentProfileInfo.label}
            </span>
            <ChevronDown size={12} className="text-muted-foreground" />
          </button>

          {profileMenuOpen && (
            <div className="absolute right-0 top-full mt-1 bg-background border rounded-lg shadow-lg py-1 min-w-[160px] z-50">
              <button
                onClick={() => handleProfileSwitch('fast')}
                disabled={switchingProfile !== null}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                  currentProfile === 'fast' 
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                    : 'hover:bg-accent'
                } ${switchingProfile !== null ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {switchingProfile === 'fast' ? (
                  <Loader2 size={14} className="animate-spin text-green-600 dark:text-green-400" />
                ) : (
                  <Zap size={14} className="text-green-600 dark:text-green-400" />
                )}
                <span>Fast Mode</span>
                {currentProfile === 'fast' && switchingProfile !== 'fast' && (
                  <span className="ml-auto text-xs text-green-600 dark:text-green-400">Active</span>
                )}
              </button>
              <button
                onClick={() => handleProfileSwitch('deep')}
                disabled={switchingProfile !== null}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                  currentProfile === 'deep' 
                    ? 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' 
                    : 'hover:bg-accent'
                } ${switchingProfile !== null ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {switchingProfile === 'deep' ? (
                  <Loader2 size={14} className="animate-spin text-purple-600 dark:text-purple-400" />
                ) : (
                  <Search size={14} className="text-purple-600 dark:text-purple-400" />
                )}
                <span>Deep Mode</span>
                {currentProfile === 'deep' && switchingProfile !== 'deep' && (
                  <span className="ml-auto text-xs text-purple-600 dark:text-purple-400">Active</span>
                )}
              </button>
              {profileError && (
                <div className="flex items-center gap-1.5 px-3 py-2 text-xs text-red-600 dark:text-red-400 border-t mt-1">
                  <AlertCircle size={12} />
                  <span>{profileError}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <button
        onClick={toggleTheme}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title={getThemeTitle()}
      >
        {getThemeIcon()}
      </button>

      <button
        onClick={() => setShortcutsOpen(true)}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
        title="Keyboard shortcuts"
      >
        <Keyboard size={18} />
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
