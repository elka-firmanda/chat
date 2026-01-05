import { Sun, Moon, Settings, Zap, Search, ChevronDown } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { useState, useEffect, useRef } from 'react'
import SettingsModal from '../settings/SettingsModal'
import { useSettingsStore } from '../../stores/settingsStore'

const PROFILE_INFO = {
  fast: { label: 'Fast', icon: Zap, color: 'text-green-600', bg: 'bg-green-100' },
  deep: { label: 'Deep', icon: Search, color: 'text-purple-600', bg: 'bg-purple-100' },
}

export default function Header() {
  const { theme, toggleTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const { currentProfile, profiles, loadProfiles, applyProfile } = useSettingsStore()
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
    await applyProfile(profile)
    setProfileMenuOpen(false)
  }

  const currentProfileInfo = currentProfile ? PROFILE_INFO[currentProfile as keyof typeof PROFILE_INFO] : null

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
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors ${
                  currentProfile === 'fast' ? 'bg-green-50 text-green-700' : ''
                }`}
              >
                <Zap size={14} className="text-green-600" />
                <span>Fast Mode</span>
                {currentProfile === 'fast' && (
                  <span className="ml-auto text-xs text-green-600">Active</span>
                )}
              </button>
              <button
                onClick={() => handleProfileSwitch('deep')}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors ${
                  currentProfile === 'deep' ? 'bg-purple-50 text-purple-700' : ''
                }`}
              >
                <Search size={14} className="text-purple-600" />
                <span>Deep Mode</span>
                {currentProfile === 'deep' && (
                  <span className="ml-auto text-xs text-purple-600">Active</span>
                )}
              </button>
              <div className="border-t my-1" />
              <button
                onClick={() => {
                  setProfileMenuOpen(false)
                  setSettingsOpen(true)
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors text-muted-foreground"
              >
                <Settings size={14} />
                <span>All Settings</span>
              </button>
            </div>
          )}
        </div>
      )}

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
