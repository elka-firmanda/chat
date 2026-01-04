import { X, MessageSquare, Archive, Settings } from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'

interface SidebarDrawerProps {
  isOpen: boolean
  onClose: () => void
  onNewChat: () => void
}

export default function SidebarDrawer({ isOpen, onClose, onNewChat }: SidebarDrawerProps) {
  const { sessions, activeSessionId, loadSession, isLoading } = useSessions()
  const { setActiveSession } = useChatStore()

  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
    onClose()
  }

  const handleNewChat = () => {
    onNewChat()
    onClose()
  }

  if (!isOpen) return null

  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 lg:hidden"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="relative w-80 max-w-[85vw] h-full bg-background flex flex-col animate-in slide-in-from-left duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Chats</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-lg lg:hidden"
          >
            <X size={20} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-4 border-b">
          <button 
            onClick={handleNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
          >
            <MessageSquare size={18} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Session List */}
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
                  className={`w-full flex items-center gap-2 px-3 py-2.5 text-sm rounded-lg transition-colors text-left truncate ${
                    activeSessionId === session.id
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'hover:bg-accent'
                  }`}
                >
                  <MessageSquare size={16} />
                  <span className="truncate">{session.title || 'New Chat'}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-muted-foreground text-sm">
              No chats yet
            </div>
          )}

          {/* Archived Section */}
          {archivedSessions.length > 0 && (
            <div className="p-2 border-t">
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors">
                <Archive size={16} />
                <span>Archived ({archivedSessions.length})</span>
              </button>
            </div>
          )}
        </div>

        {/* Bottom Actions */}
        <div className="p-2 border-t">
          <button className="w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-accent rounded-lg transition-colors">
            <Settings size={16} />
            <span>Settings</span>
          </button>
        </div>
      </div>
    </div>
  )
}
