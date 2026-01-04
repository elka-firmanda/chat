import { useEffect } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
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

  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
    onClose()
  }

  const handleNewChat = () => {
    onNewChat()
    onClose()
  }

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in z-50 data-[state=closed]:animate-out data-[state=closed]:fade-out" />
        <Dialog.Content 
          className="fixed top-0 left-0 bottom-0 w-full max-w-xs sm:max-w-[85vw] bg-background p-0 animate-in slide-in-from-left duration-300 z-50 flex flex-col touch-manipulation outline-none"
        >
          <div className="flex items-center justify-between p-4 border-b shrink-0">
            <Dialog.Title className="font-semibold text-lg m-0 p-0 border-0 bg-transparent text-foreground">
              Chats
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="min-h-[44px] min-w-[44px] -mr-2 flex items-center justify-center rounded-lg hover:bg-accent transition-colors cursor-pointer"
                aria-label="Close menu"
              >
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          <div className="p-4 border-b shrink-0">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-3 min-h-[44px] bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium touch-manipulation cursor-pointer"
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
                    className={`w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm rounded-lg transition-colors text-left truncate touch-manipulation cursor-pointer ${
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

            {archivedSessions.length > 0 && (
              <div className="p-2 border-t">
                <button className="w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors touch-manipulation cursor-pointer">
                  <Archive size={16} />
                  <span>Archived ({archivedSessions.length})</span>
                </button>
              </div>
            )}
          </div>

          <div className="p-2 border-t shrink-0">
            <button className="w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm hover:bg-accent rounded-lg transition-colors touch-manipulation cursor-pointer">
              <Settings size={16} />
              <span>Settings</span>
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
