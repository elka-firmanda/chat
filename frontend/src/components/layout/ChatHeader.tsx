import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Star, Pencil, Trash2, Archive, ArchiveRestore } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'

export default function ChatHeader() {
  const {
    activeSessionId,
    sessions,
    archivedSessions,
    messages,
    sidebarOpen,
    deleteSession,
    renameSession,
    unarchiveSession
  } = useChatStore()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const currentSession = activeSessionId 
    ? sessions.find(s => s.id === activeSessionId) || archivedSessions.find(s => s.id === activeSessionId)
    : null

  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const isArchived = currentSession?.archived || false

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isRenaming])

  const handleRename = () => {
    setRenameValue(currentSession?.title || 'New Chat')
    setIsRenaming(true)
    setDropdownOpen(false)
  }

  const submitRename = async () => {
    if (activeSessionId && renameValue.trim()) {
      await renameSession(activeSessionId, renameValue.trim())
    }
    setIsRenaming(false)
  }

  const handleDelete = async () => {
    if (activeSessionId && window.confirm('Delete this conversation?')) {
      await deleteSession(activeSessionId)
    }
    setDropdownOpen(false)
  }

  const handleUnarchive = async () => {
    if (activeSessionId) {
      await unarchiveSession(activeSessionId)
    }
    setDropdownOpen(false)
  }

  if (sessionMessages.length === 0) return null

  const title = currentSession?.title || 'New Chat'

  return (
    <div
      className={`hidden md:flex items-center gap-3 bg-secondary/30 px-4 py-3 pr-28 transition-[padding] duration-300 ease-in-out ${
        !sidebarOpen ? 'pl-16' : ''
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="relative" ref={dropdownRef}>
          {isRenaming ? (
            <input
              ref={inputRef}
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={submitRename}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submitRename()
                if (e.key === 'Escape') setIsRenaming(false)
              }}
              className="px-3 py-1 text-lg font-semibold bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          ) : (
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg hover:bg-muted transition-colors"
            >
              <span className="text-lg font-semibold truncate max-w-md">
                {title}
              </span>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </button>
          )}

          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-2 w-48 bg-popover border border-border rounded-lg shadow-lg z-50">
              <div className="py-1">
                <button
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-muted transition-colors"
                >
                  <Star className="w-4 h-4" />
                  Star
                </button>
                <button
                  onClick={handleRename}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-muted transition-colors"
                >
                  <Pencil className="w-4 h-4" />
                  Rename
                </button>
                <button
                  onClick={handleDelete}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-destructive hover:bg-muted transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>

        {isArchived && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-gray-500 text-white rounded-full">
              <Archive className="w-3 h-3" />
              Archived
            </span>
            <button
              onClick={handleUnarchive}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 rounded-full transition-colors"
            >
              <ArchiveRestore className="w-3 h-3" />
              Restore
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
