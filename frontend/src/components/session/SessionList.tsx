import { useState, useEffect, useCallback } from 'react'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { sessionsApi } from '../../services/api'
import { MessageSquare, Archive, Search, ChevronDown, ChevronRight, Download, MoreHorizontal, X, Clock, Unarchive, Trash2 } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as Dialog from '@radix-ui/react-dialog'

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)
    
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])
  
  return debouncedValue
}

export default function SessionList() {
  const { sessions, activeSessionId, isLoading, searchResults, searchSessions, clearSearch, archiveSession, unarchiveSession, deleteSession } = useSessions()
  const { setActiveSession, isDeepSearchEnabled, toggleDeepSearch } = useChatStore()
  const { general } = useSettingsStore()
  const { loadSession } = useSessions()
  const { sendMessage } = useChat()
  
  const [showArchived, setShowArchived] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState<'all' | 'sessions' | 'messages'>('all')
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  
  const debouncedSearchQuery = useDebounce(searchQuery, 300)
  
  useEffect(() => {
    if (debouncedSearchQuery.trim().length >= 2) {
      searchSessions(debouncedSearchQuery, 20, searchType)
    } else {
      clearSearch()
    }
  }, [debouncedSearchQuery, searchType, searchSessions, clearSearch])
  
  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
    setSearchQuery('')
    setShowSearch(false)
  }
  
  const handleNewChat = () => {
    setActiveSession(null)
    setSearchQuery('')
    setShowSearch(false)
  }
  
  const handleSelectExample = async (question: string) => {
    await sendMessage(question, isDeepSearchEnabled)
  }
  
  const handleExportSession = async (sessionId: string, e: Event) => {
    e.stopPropagation()
    if (isExporting) return
    
    setIsExporting(true)
    try {
      const response = await sessionsApi.export(sessionId)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      const session = sessions.find(s => s.id === sessionId)
      const filename = session?.title 
        ? `${session.title.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`
        : `session_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export session:', error)
      alert('Failed to export session. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }
  
  const handleClearSearch = () => {
    setSearchQuery('')
    clearSearch()
  }
  
  const handleSearchTypeChange = (type: 'all' | 'sessions' | 'messages') => {
    setSearchType(type)
    if (searchQuery.trim().length >= 2) {
      searchSessions(searchQuery, 20, type)
    }
  }
  
  const handleArchive = async (sessionId: string, e: Event) => {
    e.stopPropagation()
    await archiveSession(sessionId)
  }
  
  const handleUnarchive = async (sessionId: string, e: Event) => {
    e.stopPropagation()
    await unarchiveSession(sessionId)
  }
  
  const handleDeleteClick = (sessionId: string, e: Event) => {
    e.stopPropagation()
    setSessionToDelete(sessionId)
    setDeleteModalOpen(true)
  }
  
  const handleConfirmDelete = async () => {
    if (sessionToDelete) {
      setIsDeleting(true)
      try {
        await deleteSession(sessionToDelete)
        setDeleteModalOpen(false)
        setSessionToDelete(null)
      } catch (error) {
        console.error('Failed to delete session:', error)
        alert('Failed to delete session. Please try again.')
      } finally {
        setIsDeleting(false)
      }
    }
  }
  
  const activeSessions = sessions.filter(s => !s.archived).slice(0, 50)
  const archivedSessions = sessions.filter(s => s.archived)
  
  const showSearchResults = showSearch && (searchResults?.results || searchQuery.trim().length >= 2)
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <aside className="w-64 bg-secondary flex flex-col transition-all duration-300">
          <div className="p-4 border-b">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors mb-3"
            >
              <MessageSquare size={18} />
              <span>New Chat</span>
            </button>
            
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowSearch(true)}
                className="w-full pl-9 pr-8 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={handleClearSearch}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X size={14} />
                </button>
              )}
            </div>
            
            {showSearch && (
              <div className="flex gap-1 mt-2">
                <button
                  onClick={() => handleSearchTypeChange('all')}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    searchType === 'all' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => handleSearchTypeChange('sessions')}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    searchType === 'sessions' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  Titles
                </button>
                <button
                  onClick={() => handleSearchTypeChange('messages')}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    searchType === 'messages' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  Messages
                </button>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-auto p-2">
            {showSearchResults && searchResults ? (
              <div className="space-y-2">
                {searchResults.results.length > 0 ? (
                  <>
                    <div className="px-2 py-1 text-xs text-muted-foreground flex items-center justify-between">
                      <span>{searchResults.total} results in {searchResults.time_ms}ms</span>
                    </div>
                    {searchResults.results.map((result) => (
                      <button
                        key={result.session_id}
                        onClick={() => handleSelectSession(result.session_id)}
                        className="w-full flex items-start gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors text-left"
                      >
                        <MessageSquare size={16} className="mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">
                            {result.session_title || 'New Chat'}
                          </div>
                          {result.highlighted_content && (
                            <div 
                              className="text-xs text-muted-foreground mt-1 line-clamp-2"
                              dangerouslySetInnerHTML={{ 
                                __html: result.highlighted_content 
                              }}
                            />
                          )}
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            {result.type === 'message' && result.role && (
                              <span className={`px-1 py-0.5 rounded ${
                                result.role === 'user' 
                                  ? 'bg-blue-100 dark:bg-blue-900' 
                                  : 'bg-green-100 dark:bg-green-900'
                              }`}>
                                {result.role}
                              </span>
                            )}
                            {result.created_at && (
                              <span className="flex items-center gap-1">
                                <Clock size={10} />
                                {new Date(result.created_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </>
                ) : (
                  <div className="p-4 text-center text-muted-foreground text-sm">
                    No results found for "{searchResults.query}"
                  </div>
                )}
              </div>
            ) : (
              <>
                {isLoading ? (
                  <div className="p-4 text-center text-muted-foreground text-sm">
                    Loading sessions...
                  </div>
                ) : activeSessions.length > 0 ? (
                  <div className="space-y-1">
                    {activeSessions.map((session) => (
                      <DropdownMenu.Root key={session.id}>
                        <DropdownMenu.Trigger asChild>
                          <button
                            className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left group ${
                              activeSessionId === session.id
                                ? 'bg-primary/10 text-primary'
                                : 'hover:bg-accent'
                            }`}
                          >
                            <MessageSquare size={16} />
                            <span className="truncate flex-1">{session.title || 'New Chat'}</span>
                            <MoreHorizontal size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100" />
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
                              onSelect={(e: Event) => handleExportSession(session.id, e)}
                              disabled={isExporting}
                            >
                              <Download size={14} />
                              <span>{isExporting ? 'Exporting...' : 'Export PDF'}</span>
                            </DropdownMenu.Item>
                            
                            <DropdownMenu.Separator className="h-px bg-border my-1" />
                            
                            <DropdownMenu.Item 
                              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer"
                              onSelect={(e: Event) => handleArchive(session.id, e)}
                            >
                              <Archive size={14} />
                              <span>Archive</span>
                            </DropdownMenu.Item>
                          </DropdownMenu.Content>
                        </DropdownMenu.Portal>
                      </DropdownMenu.Root>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center text-muted-foreground text-sm">
                    No sessions yet
                  </div>
                )}
              </>
            )}
          </div>

          <div className="p-2 border-t">
            <button 
              onClick={() => setShowArchived(!showArchived)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors"
            >
              {showArchived ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <Archive size={16} />
              <span>Archived</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {archivedSessions.length}
              </span>
            </button>
            
            {showArchived && archivedSessions.length > 0 && (
              <div className="mt-2 space-y-1 pl-4">
                {archivedSessions.map((session) => (
                  <DropdownMenu.Root key={session.id}>
                    <DropdownMenu.Trigger asChild>
                      <button
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors text-left group text-muted-foreground"
                      >
                        <MessageSquare size={16} />
                        <span className="truncate flex-1">{session.title || 'New Chat'}</span>
                        <MoreHorizontal size={14} className="opacity-0 group-hover:opacity-100" />
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
                          onSelect={(e: Event) => handleUnarchive(session.id, e)}
                        >
                          <Unarchive size={14} />
                          <span>Unarchive</span>
                        </DropdownMenu.Item>
                        
                        <DropdownMenu.Separator className="h-px bg-border my-1" />
                        
                        <DropdownMenu.Item 
                          className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer text-destructive"
                          onSelect={(e: Event) => handleDeleteClick(session.id, e)}
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
        </aside>
      </div>

      <Dialog.Root open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-background border rounded-lg shadow-lg p-6 z-50 w-[90vw] max-w-[400px]">
            <Dialog.Title className="text-lg font-semibold mb-2">Delete Session</Dialog.Title>
            <Dialog.Description className="text-muted-foreground mb-4">
              Are you sure you want to delete this session? This action cannot be undone.
            </Dialog.Description>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteModalOpen(false)}
                className="px-4 py-2 text-sm rounded-lg hover:bg-accent transition-colors"
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
