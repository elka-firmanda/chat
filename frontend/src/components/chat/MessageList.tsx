import { useEffect, useRef, useCallback, useState } from 'react'
import { useChatStore } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'
import Message from './Message'
import { ChevronUp, Loader2, List, Layers } from 'lucide-react'
import { Virtuoso, VirtuosoHandle } from 'react-virtuoso'
import { SkeletonMessage } from '../ui/Skeleton'

export default function MessageList() {
  const { activeSessionId, messages, messageTotal } = useChatStore()
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const totalMessages = activeSessionId ? messageTotal[activeSessionId] || 0 : 0

  const { loadMessages, loadMoreMessages, isLoading } = useChat()
  const containerRef = useRef<HTMLDivElement>(null)
  const scrollHeightRef = useRef<number>(0)
  const hasLoadedInitial = useRef(false)
  const virtuosoRef = useRef<VirtuosoHandle>(null)

  const canLoadMore = sessionMessages.length < totalMessages

  const [paginationMode, setPaginationMode] = useState<'button' | 'infinite' | 'virtual'>('button')

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

  const handleStartReached = useCallback(async () => {
    if (!activeSessionId || isLoading || !canLoadMore) return
    await loadMoreMessages()
  }, [activeSessionId, isLoading, canLoadMore, loadMoreMessages])

  const scrollToBottom = useCallback(() => {
    if (virtuosoRef.current) {
      virtuosoRef.current.scrollToIndex({
        index: sessionMessages.length - 1,
        align: 'end',
        behavior: 'smooth'
      })
    }
  }, [sessionMessages.length])

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

  const renderMessage = (index: number, message: typeof sessionMessages[0]) => {
    const isFirst = index === 0
    const isLast = index === sessionMessages.length - 1
    return (
      <div className={isFirst ? 'pt-4' : ''}>
        <Message key={message.id} message={message} />
        {isLast && <div className="pb-4" />}
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="text-xs text-muted-foreground">
          {totalMessages > 0 && (
            <span>{sessionMessages.length} of {totalMessages} messages</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPaginationMode('button')}
            className={`p-1.5 rounded transition-colors ${
              paginationMode === 'button'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            title="Button pagination"
          >
            <List size={14} />
          </button>
          <button
            onClick={() => setPaginationMode('infinite')}
            className={`p-1.5 rounded transition-colors ${
              paginationMode === 'infinite'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            title="Infinite scroll"
          >
            <Layers size={14} />
          </button>
          <button
            onClick={() => setPaginationMode('virtual')}
            className={`p-1.5 rounded transition-colors ${
              paginationMode === 'virtual'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            title="Virtual scrolling"
          >
            <Layers size={14} />
          </button>
        </div>
      </div>

      {paginationMode === 'virtual' ? (
        <div className="flex-1 overflow-hidden" ref={containerRef}>
          <Virtuoso
            ref={virtuosoRef}
            data={sessionMessages}
            itemContent={(index, message) => renderMessage(index, message)}
            startReached={handleStartReached}
            atTopStateChange={(atTop) => {
              if (atTop && canLoadMore && !isLoading) {
                handleStartReached()
              }
            }}
            alignToBottom
            className="h-full"
          />
        </div>
      ) : (
        <div
          ref={containerRef}
          className="flex-1 overflow-auto p-3 sm:p-4 space-y-3 sm:space-y-4"
        >
          {(paginationMode === 'infinite' || canLoadMore) && (
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
            <div className="space-y-4">
              <SkeletonMessage />
              <SkeletonMessage />
              <SkeletonMessage />
            </div>
          )}
        </div>
      )}

      {sessionMessages.length > 10 && paginationMode !== 'virtual' && (
        <div className="absolute bottom-20 right-4">
          <button
            onClick={scrollToBottom}
            className="p-2 rounded-full bg-accent text-accent-foreground shadow-lg hover:opacity-90 transition-opacity"
            title="Scroll to bottom"
          >
            <ChevronUp size={16} className="transform rotate-180" />
          </button>
        </div>
      )}
    </div>
  )
}
