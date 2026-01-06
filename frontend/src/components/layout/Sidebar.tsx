import { useEffect, useState, useRef } from 'react'
import {
  MessageSquare,
  Plus,
  Trash2,
  Archive,
  ArchiveRestore,
  PanelLeftClose,
  PanelLeft,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import { cn, truncate, formatDate } from '../../utils'
import { useChatStore, ChatSession } from '../../stores/chatStore'
import { useSessions } from '../../hooks/useSessions'

interface SwipeableSessionItemProps {
  session: ChatSession
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onArchive: () => void
  isArchived?: boolean
  onUnarchive?: () => void
}

function SwipeableSessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
  onArchive,
  isArchived,
  onUnarchive
}: SwipeableSessionItemProps) {
  const [swipeX, setSwipeX] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const startX = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const SWIPE_THRESHOLD = 80

  const handleTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX
    setIsDragging(true)
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return
    const currentX = e.touches[0].clientX
    const diff = currentX - startX.current
    const clampedDiff = Math.max(-120, Math.min(120, diff))
    setSwipeX(clampedDiff)
  }

  const handleTouchEnd = () => {
    setIsDragging(false)
    if (swipeX < -SWIPE_THRESHOLD) {
      onDelete()
    } else if (swipeX > SWIPE_THRESHOLD) {
      if (isArchived && onUnarchive) {
        onUnarchive()
      } else {
        onArchive()
      }
    }
    setSwipeX(0)
  }

  return (
    <div ref={containerRef} className="relative overflow-hidden">
      <div className="absolute inset-y-0 left-0 w-1/2 flex items-center justify-start pl-4 bg-orange-500">
        {isArchived ? (
          <ArchiveRestore className="w-5 h-5 text-white" />
        ) : (
          <Archive className="w-5 h-5 text-white" />
        )}
      </div>

      <div className="absolute inset-y-0 right-0 w-1/2 flex items-center justify-end pr-4 bg-red-600">
        <Trash2 className="w-5 h-5 text-white" />
      </div>

      <div
        className={cn(
          'relative group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors',
          'bg-slate-100 dark:bg-slate-800',
          isActive && 'bg-slate-200 dark:bg-slate-700'
        )}
        style={{
          transform: `translateX(${swipeX}px)`,
          transition: isDragging ? 'none' : 'transform 0.2s ease-out'
        }}
        onClick={onSelect}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <MessageSquare className="w-4 h-4 shrink-0 text-muted-foreground" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {truncate(session.title || 'New Chat', 30)}
          </p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {formatDate(session.updated_at)}
            </span>
            {isArchived && (
              <span className="text-[10px] px-1.5 py-0.5 bg-amber-500 text-white rounded">
                Archived
              </span>
            )}
          </div>
        </div>

        <div className="hidden md:flex opacity-0 group-hover:opacity-100 items-center gap-1 transition-all">
          {isArchived ? (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onUnarchive?.()
              }}
              className="p-1.5 rounded hover:bg-amber-500/10 hover:text-amber-500 transition-all"
              aria-label="Unarchive chat"
            >
              <ArchiveRestore className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onArchive()
              }}
              className="p-1.5 rounded hover:bg-amber-500/10 hover:text-amber-500 transition-all"
              aria-label="Archive chat"
            >
              <Archive className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="p-1.5 rounded hover:bg-red-500/10 hover:text-red-500 transition-all"
            aria-label="Delete chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar
  } = useChatStore()

  const {
    sessions,
    archivedSessions,
    activeSessionId,
    loadSessions,
    loadArchivedSessions,
    loadSession,
    deleteSession,
    archiveSession,
    unarchiveSession,
    createSession
  } = useSessions()

  const [archivedExpanded, setArchivedExpanded] = useState(false)

  useEffect(() => {
    loadSessions()
    loadArchivedSessions()
  }, [loadSessions, loadArchivedSessions])

  const handleNewChat = async () => {
    await createSession()
  }

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={toggleSidebar}
        />
      )}

      {!sidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="fixed left-4 top-4 z-50 p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
          aria-label="Open sidebar"
        >
          <PanelLeft className="w-5 h-5" />
        </button>
      )}

      <aside
        className={cn(
          'fixed z-50 h-full w-72 flex flex-col transition-transform duration-300 ease-in-out',
          'bg-slate-100 dark:bg-slate-800',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="p-4 flex items-center justify-between">
          <h1 className="font-semibold text-lg">Agentic Chat</h1>
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
            aria-label="Close sidebar"
          >
            <PanelLeftClose className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity font-medium"
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          {archivedSessions.length > 0 && (
            <div className="mb-2">
              <button
                onClick={() => setArchivedExpanded(!archivedExpanded)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {archivedExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
                <Archive className="w-4 h-4" />
                <span>Archived ({archivedSessions.length})</span>
              </button>

              {archivedExpanded && (
                <div className="mt-1">
                  {archivedSessions.map((session) => (
                    <SwipeableSessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === activeSessionId}
                      onSelect={() => loadSession(session.id)}
                      onDelete={() => deleteSession(session.id)}
                      onArchive={() => {}}
                      isArchived
                      onUnarchive={() => unarchiveSession(session.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          <div>
            {sessions.map((session) => (
              <SwipeableSessionItem
                key={session.id}
                session={session}
                isActive={session.id === activeSessionId}
                onSelect={() => loadSession(session.id)}
                onDelete={() => deleteSession(session.id)}
                onArchive={() => archiveSession(session.id)}
              />
            ))}

            {sessions.length === 0 && archivedSessions.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                No chat history yet
              </p>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
