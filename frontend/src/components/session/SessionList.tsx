import { useState } from 'react'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { MessageSquare, Archive, Search, ChevronDown, ChevronRight } from 'lucide-react'
import ExampleCards from '../chat/ExampleCards'
import MessageList from '../chat/MessageList'
import InputBox from '../chat/InputBox'
import { useChat } from '../../hooks/useChat'

export default function SessionList() {
  const { sessions, activeSessionId, isLoading } = useSessions()
  const { setActiveSession, isDeepSearchEnabled, toggleDeepSearch } = useChatStore()
  const { general } = useSettingsStore()
  const { loadSession } = useSessions()
  const { sendMessage } = useChat()
  
  const [showArchived, setShowArchived] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  
  const handleSelectSession = async (sessionId: string) => {
    await loadSession(sessionId)
  }
  
  const handleNewChat = () => {
    setActiveSession(null)
  }
  
  const handleSelectExample = async (question: string) => {
    await sendMessage(question, isDeepSearchEnabled)
  }
  
  const activeSessions = sessions.filter(s => !s.archived)
  const archivedSessions = sessions.filter(s => s.archived)
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Session list sidebar */}
        <aside className={`${showSearch ? 'w-64' : 'w-64'} bg-secondary flex flex-col transition-all duration-300`}>
          {/* New Chat Button */}
          <div className="p-4 border-b">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <MessageSquare size={18} />
              <span>New Chat</span>
            </button>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-auto p-2">
            {isLoading ? (
              <div className="p-4 text-center text-muted-foreground text-sm">
                Loading sessions...
              </div>
            ) : activeSessions.length > 0 ? (
              <div className="space-y-1">
                {activeSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left ${
                      activeSessionId === session.id
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-accent'
                    }`}
                  >
                    <MessageSquare size={16} />
                    <span className="truncate flex-1">{session.title || 'New Chat'}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-muted-foreground text-sm">
                No sessions yet
              </div>
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
