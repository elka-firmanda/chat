import { useEffect, useRef, useCallback } from 'react'
import { useChatStore } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'
import Message from './Message'
import { ChevronUp, Loader2 } from 'lucide-react'

export default function MessageList() {
  const { activeSessionId, messages, messageTotal } = useChatStore()
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const totalMessages = activeSessionId ? messageTotal[activeSessionId] || 0 : 0

  const { loadMessages, loadMoreMessages, isLoading } = useChat()
  const containerRef = useRef<HTMLDivElement>(null)
  const scrollHeightRef = useRef<number>(0)
  const hasLoadedInitial = useRef(false)

  const canLoadMore = sessionMessages.length < totalMessages

  useEffect(() => {
    if (activeSessionId && !hasLoadedInitial.current) {
      hasLoadedInitial.current = true
      loadMessages(activeSessionId, 30, 0)
    }
  }, [activeSessionId, loadMessages])

  useEffect(() => {
    if (!activeSessionId) {
      hasLoadedInitial.current = false
    }
  }, [activeSessionId])

  const handleLoadMore = useCallback(async () => {
    if (!activeSessionId || isLoading || !canLoadMore) return

    const container = containerRef.current
    if (!container) return

    scrollHeightRef.current = container.scrollHeight
    await loadMoreMessages()
  }, [activeSessionId, isLoading, canLoadMore, loadMoreMessages])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleScroll = () => {
      if (container.scrollTop <= 50 && canLoadMore && !isLoading) {
        handleLoadMore()
      }
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => container.removeEventListener('scroll', handleScroll)
  }, [canLoadMore, isLoading, handleLoadMore])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const newScrollHeight = container.scrollHeight
    const oldScrollHeight = scrollHeightRef.current

    if (oldScrollHeight > 0 && newScrollHeight > oldScrollHeight) {
      const scrollDifference = newScrollHeight - oldScrollHeight
      container.scrollTop = scrollDifference
    }
  }, [sessionMessages])

  if (sessionMessages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="text-center text-muted-foreground">
          <p className="text-base sm:text-lg mb-2">Start a conversation</p>
          <p className="text-xs sm:text-sm">Send a message to begin chatting</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-auto p-3 sm:p-4 space-y-3 sm:space-y-4"
    >
      {canLoadMore && (
        <div className="flex justify-center pb-2">
          <button
            onClick={handleLoadMore}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ChevronUp size={16} />
            )}
            {isLoading ? 'Loading...' : `Show more (${totalMessages - sessionMessages.length} remaining)`}
          </button>
        </div>
      )}

      {sessionMessages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {sessionMessages.length === 0 && isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={24} className="animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  )
}
