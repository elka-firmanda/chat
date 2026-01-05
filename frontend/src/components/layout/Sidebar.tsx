import { useState, useEffect } from 'react'
import { MessageSquare, Plus, Archive, Settings, ChevronLeft, ChevronRight } from 'lucide-react'

interface Session {
  id: string
  title: string | null
  archived: boolean
  created_at: string
  updated_at: string
}

interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  isLoading: boolean
  onNewChat: () => void
  onSelectSession: (sessionId: string) => void
  onSettingsClick: () => void
}

export default function Sidebar({ sessions, activeSessionId, isLoading, onNewChat, onSelectSession, onSettingsClick }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed')
    return saved ? JSON.parse(saved) : false
  })

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(isCollapsed))
  }, [isCollapsed])

  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)

  const toggleCollapse = () => setIsCollapsed(!isCollapsed)

  return (
    <aside className={`${isCollapsed ? 'w-16' : 'w-64'} bg-secondary/50 flex flex-col border-r transition-all duration-300 h-full relative`}>
      <div className="p-3 sm:p-4 border-b shrink-0">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center sm:justify-start gap-2 px-3 py-2.5 min-h-[44px] bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium touch-manipulation"
          title={isCollapsed ? 'New Chat' : undefined}
        >
          <Plus size={18} />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      <div className="flex-1 overflow-auto p-2">
        {isLoading ? (
          <div className="p-4 text-center text-muted-foreground text-sm">
            Loading...
          </div>
        ) : activeSessions.length > 0 ? (
          <div className="space-y-1">
            {activeSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg transition-colors text-left touch-manipulation cursor-pointer ${
                  activeSessionId === session.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-accent'
                }`}
                title={isCollapsed ? session.title || 'New Chat' : undefined}
              >
                <MessageSquare size={16} className="shrink-0" />
                {!isCollapsed && <span className="truncate">{session.title || 'New Chat'}</span>}
              </button>
            ))}
          </div>
        ) : (
          <div className="p-4 text-center text-muted-foreground text-sm">
            No chats yet
          </div>
        )}

        {archivedSessions.length > 0 && !isCollapsed && (
          <div className="p-2 border-t mt-2">
            <button className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors touch-manipulation cursor-pointer">
              <Archive size={16} />
              <span>Archived ({archivedSessions.length})</span>
            </button>
          </div>
        )}
      </div>

      <div className="p-2 border-t shrink-0">
        <button
          onClick={onSettingsClick}
          className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors touch-manipulation cursor-pointer"
          title={isCollapsed ? 'Settings' : undefined}
        >
          <Settings size={16} />
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>

      <button
        onClick={toggleCollapse}
        className="hidden xl:flex absolute top-1/2 right-0 translate-x-1/2 -translate-y-1/2 min-h-[32px] min-w-[32px] items-center justify-center bg-background border rounded-full shadow-md hover:bg-accent transition-colors z-10 cursor-pointer"
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  )
}
