import { useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { X, MessageSquare, Archive, Settings, ChevronDown, ChevronRight, MoreHorizontal, ArchiveRestore, Trash2 } from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'

interface SidebarDrawerProps {
  isOpen: boolean
  onClose: () => void
  onNewChat: () => void
  onSettingsClick?: () => void
}

export default function SidebarDrawer({ isOpen, onClose, onNewChat, onSettingsClick }: SidebarDrawerProps) {
  const { sessions, activeSessionId, loadSession, isLoading, archiveSession, unarchiveSession, deleteSession } = useSessions()

  const [showArchived, setShowArchived] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)

  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
    onClose()
  }

  const handleNewChat = () => {
    onNewChat()
    onClose()
  }

  const handleUnarchive = async (sessionId: string) => {
    await unarchiveSession(sessionId)
  }

  const handleDeleteClick = (sessionId: string) => {
    setSessionToDelete(sessionId)
    setDeleteModalOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (sessionToDelete) {
      await deleteSession(sessionToDelete)
      setDeleteModalOpen(false)
      setSessionToDelete(null)
    }
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
                <button 
                  onClick={() => setShowArchived(!showArchived)}
                  className="w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors touch-manipulation cursor-pointer"
                >
                  {showArchived ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <Archive size={16} />
                  <span>Archived ({archivedSessions.length})</span>
                </button>
                
                {showArchived && (
                  <div className="mt-2 space-y-1 pl-4">
                    {archivedSessions.map((session) => (
                      <DropdownMenu.Root key={session.id}>
                        <DropdownMenu.Trigger asChild>
                          <button
                            className="w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors text-left text-muted-foreground touch-manipulation cursor-pointer"
                          >
                            <MessageSquare size={16} />
                            <span className="truncate flex-1">{session.title || 'New Chat'}</span>
                            <MoreHorizontal size={14} />
                          </button>
                        </DropdownMenu.Trigger>
                        
                        <DropdownMenu.Portal>
                          <DropdownMenu.Content 
                            className="min-w-[150px] bg-popover border rounded-lg shadow-lg p-1 z-50"
                            sideOffset={5}
                            align="end"
                          >
                            <DropdownMenu.Item 
                              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer"
                              onSelect={() => handleSelectSession(session.id)}
                            >
                              <MessageSquare size={14} />
                              <span>Load</span>
                            </DropdownMenu.Item>
                            
                            <DropdownMenu.Item 
                              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer"
                              onSelect={() => handleUnarchive(session.id)}
                            >
                              <ArchiveRestore size={14} />
                              <span>Unarchive</span>
                            </DropdownMenu.Item>
                            
                            <DropdownMenu.Separator className="h-px bg-border my-1" />
                            
                            <DropdownMenu.Item 
                              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer text-destructive"
                              onSelect={() => handleDeleteClick(session.id)}
                            >
                              <Trash2 size={14} />
                              <span>Delete</span>
                            </DropdownMenu.Item>
                          </DropdownMenu.Content>
                        </DropdownMenu.Portal>
                      </DropdownMenu.Root>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="p-2 border-t shrink-0">
            <button 
              onClick={() => {
                onClose()
                onSettingsClick?.()
              }}
              className="w-full flex items-center gap-2 px-3 py-3 min-h-[44px] text-sm hover:bg-accent rounded-lg transition-colors touch-manipulation cursor-pointer"
            >
              <Settings size={16} />
              <span>Settings</span>
            </button>
          </div>

          <Dialog.Root open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
              <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-background border rounded-lg shadow-lg p-6 z-50 w-[90vw] max-w-[400px]">
                <Dialog.Title className="text-lg font-semibold mb-2">Delete Session</Dialog.Title>
                <Dialog.Description className="text-muted-foreground mb-4">
                  Are you sure you want to delete this session? This action cannot be undone.
                </Dialog.Description>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setDeleteModalOpen(false)}
                    className="px-4 py-2 text-sm rounded-lg hover:bg-accent transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmDelete}
                    className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
