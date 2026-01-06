import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import Sidebar from './Sidebar'
import SidebarDrawer from './SidebarDrawer'
import Header from './Header'
import SettingsModal from '../settings/SettingsModal'
import { useChatStore } from '../../stores/chatStore'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { useSessions } from '../../hooks/useSessions'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { sessions, activeSessionId, loadSession, isLoading } = useSessions()

  useKeyboardShortcuts()

  const handleNewChat = () => {
    useChatStore.getState().setActiveSession(null)
  }

  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
  }

  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="hidden xl:block">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          isLoading={isLoading}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onSettingsClick={() => setSettingsOpen(true)}
        />
      </aside>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />

      <SidebarDrawer
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={() => {
          useChatStore.getState().setActiveSession(null)
        }}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="xl:hidden h-14 border-b flex items-center px-3 sm:px-4 gap-2 bg-background shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="min-h-[44px] min-w-[44px] -ml-2 flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <div className="flex-1" />
          <Header />
        </header>

        <header className="hidden xl:flex h-14 border-b items-center justify-end px-4 gap-2 bg-background shrink-0">
          <Header />
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
