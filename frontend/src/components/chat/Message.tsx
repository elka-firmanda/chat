import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Message as MessageType } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'
import { useSessions } from '../../hooks/useSessions'
import { useChatStore } from '../../stores/chatStore'
import { useToastStore } from '../../hooks/useToast'
import ThinkingBlock from './ThinkingBlock'
import MarkdownRenderer from './MarkdownRenderer'
import { Copy, Check, GitFork, MoreHorizontal, ChevronDown, ChevronUp, RotateCcw, Edit3, Loader2 } from 'lucide-react'

interface MessageProps {
  message: MessageType
  onEdit?: (messageId: string, newContent: string) => void
}

const MAX_VISIBLE_LINES = 30

export default function MessageComponent({ message, onEdit }: MessageProps) {
  const [copied, setCopied] = useState(false)
  const [showContextMenu, setShowContextMenu] = useState(false)
  const [isForking, setIsForking] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const contextMenuRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const isUser = message.role === 'user'

  const { forkConversation, regenerateMessage } = useChat()
  const { loadSessions } = useSessions()
  const { setActiveSession, setMessages } = useChatStore()
  const { success } = useToastStore()

  const lines = useMemo(() => message.content.split('\n'), [message.content])
  const needsTruncation = lines.length > MAX_VISIBLE_LINES
  const displayContent = isExpanded || !needsTruncation
    ? message.content
    : lines.slice(0, MAX_VISIBLE_LINES).join('\n')

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }, [message.content, success])

  const handleFork = useCallback(async () => {
    setIsForking(true)
    setShowContextMenu(false)

    try {
      const newSessionId = await forkConversation(message.id)
      await loadSessions()

      const response = await import('../../services/api').then(api =>
        api.sessionsApi.get(newSessionId)
      )

      setActiveSession(newSessionId)
      const { messages } = response.data
      setMessages(newSessionId, messages)

    } catch (error) {
      console.error('Failed to fork conversation:', error)
    } finally {
      setIsForking(false)
    }
  }, [forkConversation, loadSessions, message.id, setActiveSession, setMessages])

  const handleRegenerate = useCallback(async () => {
    if (isRegenerating) return
    setIsRegenerating(true)
    setShowContextMenu(false)

    try {
      await regenerateMessage(message.id)
    } catch (error) {
      console.error('Failed to regenerate:', error)
    } finally {
      setIsRegenerating(false)
    }
  }, [regenerateMessage, message.id, isRegenerating])

  const handleEdit = useCallback(() => {
    if (onEdit) {
      onEdit(message.id, message.content)
    }
    setShowContextMenu(false)
  }, [onEdit, message.id, message.content])

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

  const thinkingContent = String(message.metadata?.thinking_content || "Processing...")

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} px-1 sm:px-2 md:px-0 group`}>
      <div className={`relative max-w-[90%] sm:max-w-[85%] md:max-w-[80%] rounded-2xl px-3 py-2.5 sm:px-4 sm:py-3 ${
        isUser
          ? 'bg-primary text-primary-foreground rounded-br-md'
          : 'bg-muted rounded-bl-md'
      }`}>
        {!isUser && (
          <div className="absolute right-1.5 top-1.5 sm:right-2 sm:top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setShowContextMenu(!showContextMenu)
              }}
              className="min-h-[36px] min-w-[36px] flex items-center justify-center hover:bg-current/10 rounded transition-colors"
              title="More options"
              aria-label="More options"
            >
              <MoreHorizontal size={16} />
            </button>
          </div>
        )}

        {isUser && (
          <div className="absolute left-1.5 top-1.5 sm:left-2 sm:top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setShowContextMenu(!showContextMenu)
              }}
              className="min-h-[36px] min-w-[36px] flex items-center justify-center hover:bg-current/10 rounded transition-colors"
              title="More options"
              aria-label="More options"
            >
              <MoreHorizontal size={16} />
            </button>
          </div>
        )}

        {showContextMenu && (
          <div
            ref={contextMenuRef}
            className={`absolute ${isUser ? 'left-0' : 'right-0'} top-8 bg-popover border rounded-lg shadow-lg py-1 z-50 min-w-[140px]`}
          >
            <button
              onClick={handleCopy}
              className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm hover:bg-accent transition-colors"
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            {!isUser && (
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm hover:bg-accent transition-colors disabled:opacity-50"
              >
                {isRegenerating ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
                {isRegenerating ? 'Regenerating...' : 'Regenerate'}
              </button>
            )}
            <button
              onClick={handleFork}
              disabled={isForking}
              className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm hover:bg-accent transition-colors disabled:opacity-50"
            >
              <GitFork size={16} />
              {isForking ? 'Forking...' : 'Fork'}
            </button>
            {isUser && onEdit && (
              <button
                onClick={handleEdit}
                className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm hover:bg-accent transition-colors"
              >
                <Edit3 size={16} />
                Edit
              </button>
            )}
          </div>
        )}

        {!isUser && message.agent_type && (
          <ThinkingBlock
            agent={message.agent_type as any}
            content={thinkingContent}
            defaultCollapsed={true}
          />
        )}

        <div ref={contentRef}>
          <MarkdownRenderer content={displayContent} />
        </div>

        {needsTruncation && !isExpanded && (
          <button
            onClick={() => setIsExpanded(true)}
            className="flex items-center gap-1 text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors mt-1"
          >
            <ChevronDown size={14} />
            Show more
          </button>
        )}

        {needsTruncation && isExpanded && (
          <button
            onClick={() => setIsExpanded(false)}
            className="flex items-center gap-1 text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors mt-1"
          >
            <ChevronUp size={14} />
            Show less
          </button>
        )}

        <div className={`flex items-center gap-1 mt-2 pt-2 border-t border-current/10 ${isUser ? 'border-primary-foreground/10' : ''}`}>
          <button
            onClick={handleCopy}
            className="min-h-[36px] min-w-[36px] flex items-center justify-center hover:bg-current/10 rounded transition-colors"
            title="Copy message"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
          {!isUser && (
            <button
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="min-h-[36px] min-w-[36px] flex items-center justify-center hover:bg-current/10 rounded transition-colors disabled:opacity-50"
              title="Regenerate response"
            >
              {isRegenerating ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
            </button>
          )}
          {isUser && onEdit && (
            <button
              onClick={handleEdit}
              className="min-h-[36px] min-w-[36px] flex items-center justify-center hover:bg-current/10 rounded transition-colors"
              title="Edit message"
            >
              <Edit3 size={16} />
            </button>
          )}
        </div>

        <div className={`text-[10px] sm:text-xs mt-2 ${
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
