import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, MessageSquare, Archive, Settings } from 'lucide-react'
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

  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)

  const handleNewChat = () => {
    useChatStore.getState().setActiveSession(null)
  }

  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
  }

  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="hidden xl:flex w-64 bg-secondary/50 flex-col border-r shrink-0">
        <div className="flex-1 flex flex-col">
          <div className="p-4 border-b shrink-0">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium cursor-pointer"
            >
              <MessageSquare size={18} />
              <span>New Chat</span>
            </button>
          </div>

          <div className="flex-1 overflow-auto">
            {isLoading ? (
              <div className="p-4 text-center text-muted-foreground text-sm">
                Loading...
              </div>
            ) : activeSessions.length > 0 ? (
              <div className="p-2 space-y-1">
                {activeSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2.5 text-sm rounded-lg transition-colors text-left truncate cursor-pointer ${
                      activeSessionId === session.id
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'hover:bg-accent'
                    }`}
                  >
                    <MessageSquare size={16} className="shrink-0" />
                    <span className="truncate">{session.title || 'New Chat'}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-muted-foreground text-sm">
                No chats yet
              </div>
            )}

            {archivedSessions.length > 0 && (
              <div className="p-2 border-t">
                <button className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors cursor-pointer">
                  <Archive size={16} />
                  <span>Archived ({archivedSessions.length})</span>
                </button>
              </div>
            )}
          </div>

          <div className="p-2 border-t shrink-0">
            <button 
              onClick={() => setSettingsOpen(true)}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-accent rounded-lg transition-colors cursor-pointer"
            >
              <Settings size={16} />
              <span>Settings</span>
            </button>
          </div>
        </div>
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
