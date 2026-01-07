import { useEffect, useRef, useState, useCallback } from 'react'
import { useChatStore } from '../../stores/chatStore'
import Message from './Message'
import ExampleCards from './ExampleCards'
import InputBox from './InputBox'
import ProgressSteps from './ProgressSteps'
import ToastContainer from '../ui/Toast'
import { useChat } from '../../hooks/useChat'
import { useSessionCancellation } from '../../hooks/useSessionCancellation'
import { SkeletonChatContainer } from '../ui/Skeleton'

export default function ChatContainer() {
  const {
    activeSessionId,
    messages,
    isDeepSearchEnabled,
    currentPlan,
    statusMessage,
  } = useChatStore()

  const [editingMessage, setEditingMessage] = useState<{id: string, content: string} | null>(null)

  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const { sendMessage, isLoading: isChatLoading } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useSessionCancellation(activeSessionId)

  const handleSelectExample = async (question: string, requiresDeepSearch?: boolean) => {
    await sendMessage(question, requiresDeepSearch ?? isDeepSearchEnabled)
  }

  const handleEditMessage = useCallback((messageId: string, newContent: string) => {
    setEditingMessage({ id: messageId, content: newContent })
  }, [])

  const handleSubmitEditedMessage = useCallback(async (content: string) => {
    if (!editingMessage) return
    await sendMessage(content, isDeepSearchEnabled)
    setEditingMessage(null)
  }, [editingMessage, sendMessage, isDeepSearchEnabled])

  const handleCancelEdit = useCallback(() => {
    setEditingMessage(null)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages])

  if (sessionMessages.length === 0 && isChatLoading) {
    return <SkeletonChatContainer />
  }

  if (sessionMessages.length === 0) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <ToastContainer />
        <ExampleCards onSelect={handleSelectExample} />
        <div className="mt-auto">
          <InputBox />
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ToastContainer />

      {statusMessage && (
        <div className="px-4 py-2 text-sm text-muted-foreground bg-muted/50 border-b border-border flex items-center gap-2">
          <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          {statusMessage}
        </div>
      )}

      <ProgressSteps steps={currentPlan} />
      
      <div className="flex-1 overflow-auto p-3 md:p-4 pb-0 space-y-2">
        {sessionMessages.map((message) => (
          <Message key={message.id} message={message} onEdit={handleEditMessage} />
        ))}
        {isChatLoading && sessionMessages.length > 0 && sessionMessages[sessionMessages.length - 1]?.role === 'user' && (
          <div className="flex gap-3 p-3">
            <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-24 bg-muted rounded animate-pulse" />
              <div className="space-y-1">
                <div className="h-3 w-full bg-muted rounded animate-pulse" />
                <div className="h-3 w-5/6 bg-muted rounded animate-pulse" />
                <div className="h-3 w-4/6 bg-muted rounded animate-pulse" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <InputBox
        initialValue={editingMessage?.content || ''}
        onSubmit={handleSubmitEditedMessage}
        onCancel={handleCancelEdit}
      />
    </div>
  )
}
