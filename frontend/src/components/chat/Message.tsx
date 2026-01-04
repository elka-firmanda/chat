import { useState, useRef, useEffect } from 'react'
import { Message as MessageType } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'
import ThinkingBlock from './ThinkingBlock'
import { Copy, Check, GitFork, MoreHorizontal } from 'lucide-react'

interface MessageProps {
  message: MessageType
}

export default function MessageComponent({ message }: MessageProps) {
  const [copied, setCopied] = useState(false)
  const [showContextMenu, setShowContextMenu] = useState(false)
  const [isForking, setIsForking] = useState(false)
  const contextMenuRef = useRef<HTMLDivElement>(null)
  const isUser = message.role === 'user'
  
  const { forkConversation } = useChat()
  const { loadSessions } = useSessions()
  const { setActiveSession, setMessages, activeSessionId } = useChatStore()
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  const handleFork = async () => {
    setIsForking(true)
    setShowContextMenu(false)
    
    try {
      const newSessionId = await forkConversation(message.id)
      await loadSessions()
      
      const response = await import('../../services/api').then(api => 
        api.sessionsApi.get(newSessionId)
      )
      
      setActiveSession(newSessionId)
      const { messages, ...sessionData } = response.data
      setMessages(newSessionId, messages)
      
    } catch (error) {
      console.error('Failed to fork conversation:', error)
    } finally {
      setIsForking(false)
    }
  }
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setShowContextMenu(false)
      }
    }
    
    if (showContextMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showContextMenu])
  
  const thinkingContent = message.metadata?.thinking_content || "Processing..."

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} px-2 md:px-0 group`}>
      <div className={`relative max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 md:px-5 ${
        isUser 
          ? 'bg-primary text-primary-foreground rounded-br-md' 
          : 'bg-muted rounded-bl-md'
      }`}>
        {!isUser && (
          <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setShowContextMenu(!showContextMenu)
              }}
              className="p-1 hover:bg-current/10 rounded transition-colors"
              title="More options"
            >
              <MoreHorizontal size={14} />
            </button>
          </div>
        )}
        
        {/* Context menu dropdown */}
        {showContextMenu && (
          <div 
            ref={contextMenuRef}
            className="absolute right-0 top-8 bg-popover border rounded-lg shadow-lg py-1 z-50 min-w-[120px]"
          >
            <button
              onClick={handleCopy}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={handleFork}
              disabled={isForking}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
            >
              <GitFork size={14} />
              {isForking ? 'Forking...' : 'Fork'}
            </button>
          </div>
        )}
        
        {!isUser && message.agent_type && (
          <ThinkingBlock 
            agent={message.agent_type as any} 
            content={thinkingContent}
            defaultCollapsed={true}
          />
        )}
        
        {/* Context menu dropdown */}
        {showContextMenu && (
          <div 
            ref={contextMenuRef}
            className="absolute right-0 top-8 bg-popover border rounded-lg shadow-lg py-1 z-50 min-w-[120px]"
          >
            <button
              onClick={handleCopy}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={handleFork}
              disabled={isForking}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
            >
              <GitFork size={14} />
              {isForking ? 'Forking...' : 'Fork'}
            </button>
          </div>
        )}
        
        {/* Agent thinking block */}
        {!isUser && message.agent_type && (
          <ThinkingBlock 
            agent={message.agent_type as any} 
            content={thinkingContent}
            defaultCollapsed={true}
          />
        )}
        
        {/* Message content */}
        <div className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
          {message.content}
        </div>
        
        {/* Actions bar */}
        {!isUser && (
          <div className="flex items-center gap-1 mt-2 pt-2 border-t border-current/10">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-current/10 rounded transition-colors"
              title="Copy message"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        )}
        
        {/* Timestamp */}
        <div className={`text-[10px] md:text-xs mt-2 ${
          isUser ? 'text-primary-foreground/60' : 'text-muted-foreground'
        }`}>
          {message.created_at && new Date(message.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  )
}
