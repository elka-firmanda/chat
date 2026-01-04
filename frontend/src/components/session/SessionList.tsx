import { useState, useEffect, useCallback } from 'react'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { sessionsApi } from '../../services/api'
import { MessageSquare, Archive, Search, ChevronDown, ChevronRight, Download, MoreHorizontal, X, Clock } from 'lucide-react'
import ExampleCards from '../chat/ExampleCards'
import MessageList from '../chat/MessageList'
import InputBox from '../chat/InputBox'
import { useChat } from '../../hooks/useChat'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'

// Debounce hook for search input
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
  const { sessions, activeSessionId, isLoading, searchResults, searchSessions, clearSearch } = useSessions()
  const { setActiveSession, isDeepSearchEnabled, toggleDeepSearch } = useChatStore()
  const { general } = useSettingsStore()
  const { loadSession } = useSessions()
  const { sendMessage } = useChat()
  
  const [showArchived, setShowArchived] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState<'all' | 'sessions' | 'messages'>('all')
  
  // Debounce search query (300ms delay)
  const debouncedSearchQuery = useDebounce(searchQuery, 300)
  
  // Trigger search when debounced query changes
  useEffect(() => {
    if (debouncedSearchQuery.trim().length >= 2) {
      searchSessions(debouncedSearchQuery, 20, searchType)
    } else {
      clearSearch()
    }
  }, [debouncedSearchQuery, searchType, searchSessions, clearSearch])
  
  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
    // Clear search when selecting a session
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
      
      // Create blob and download
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Get session title for filename
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
  
  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)
  
  // Show search results when search is active
  const showSearchResults = showSearch && (searchResults?.results || searchQuery.trim().length >= 2)
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Sidebar with search */}
        <aside className="w-64 bg-secondary flex flex-col transition-all duration-300">
          {/* Header with New Chat and Search */}
          <div className="p-4 border-b">
            {/* New Chat Button */}
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors mb-3"
            >
              <MessageSquare size={18} />
              <span>New Chat</span>
            </button>
            
            {/* Search Input */}
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
            
            {/* Search Type Tabs */}
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

          {/* Search Results or Session List */}
          <div className="flex-1 overflow-auto p-2">
            {showSearchResults && searchResults ? (
              // Search Results
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
              // Regular Session List
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
                            className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left ${
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
                              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md outline-none hover:bg-accent cursor-pointer text-destructive"
                              onSelect={() => {
                                // Handle delete/archival
                              }}
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

          {/* Bottom Actions */}
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
                  <button
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors text-left text-muted-foreground"
                  >
                    <MessageSquare size={16} />
                    <span className="truncate flex-1">{session.title || 'New Chat'}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
