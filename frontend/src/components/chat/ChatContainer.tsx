import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useChatStore } from '../../stores/chatStore'
import { useChatErrorStore, PendingError } from '../../stores/errorStore'
import { chatApi } from '../../services/api'
import Message from './Message'
import ExampleCards from './ExampleCards'
import InputBox from './InputBox'
import ProgressSteps from './ProgressSteps'
import WorkingMemoryVisualization from './WorkingMemoryVisualization'
import ErrorModal from './ErrorModal'
import ToastContainer from '../ui/Toast'
import { useChat } from '../../hooks/useChat'
import { useSSE } from '../../hooks/useSSE'
import { useSessionCancellation } from '../../hooks/useSessionCancellation'
import { SkeletonChatContainer } from '../ui/Skeleton'

export default function ChatContainer() {
  const {
    activeSessionId,
    messages,
    isDeepSearchEnabled,
    agentSteps,
    workingMemory,
    addMessage,
    updateMessage,
    updateAgentStep,
    setWorkingMemory,
    updateNode,
    addTimelineEntry,
    setActiveNode,
    addThought
  } = useChatStore()

  const {
    pendingError,
    setPendingError,
    clearErrorState
  } = useChatErrorStore()

  const [isIntervening, setIsIntervening] = useState(false)
  const [editingMessage, setEditingMessage] = useState<{id: string, content: string} | null>(null)

  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const currentSteps = activeSessionId ? agentSteps[activeSessionId] || [] : []
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

  // Memoize SSE handlers to prevent infinite re-render loops
  // These must be stable references so useSSE doesn't re-run on every render
  const sseHandlers = useMemo(() => ({
    onThought: (data: { agent: string; content: string }) => {
      if (activeSessionId) {
        addThought(activeSessionId, data.agent, data.content)
      }
    },
    onStepUpdate: (data: { step_id: string; status: string; description: string; logs?: string }) => {
      if (activeSessionId) {
        updateAgentStep(activeSessionId, data.step_id, {
          status: data.status as 'pending' | 'running' | 'completed' | 'failed',
          logs: data.logs
        })
      }
    },
    onMemoryUpdate: (data: { memory_tree: any; timeline: any; index: any; stats: any }) => {
      if (activeSessionId) {
        setWorkingMemory(activeSessionId, {
          memory_tree: data.memory_tree,
          timeline: data.timeline,
          index: data.index,
          stats: data.stats
        })
      }
    },
    onNodeAdded: (data: { node_id: string; agent: string; node_type: string; description: string; parent_id?: string; timestamp: string }) => {
      if (activeSessionId) {
        setActiveNode(activeSessionId, data.node_id)
        addTimelineEntry(activeSessionId, {
          node_id: data.node_id,
          agent: data.agent,
          node_type: data.node_type,
          description: data.description,
          status: 'running',
          timestamp: data.timestamp,
          parent_id: data.parent_id
        })
      }
    },
    onNodeUpdated: (data: { node_id: string; status?: string; content?: Record<string, unknown>; completed: boolean; timestamp: string }) => {
      if (activeSessionId) {
        updateNode(activeSessionId, data.node_id, {
          status: data.status as 'pending' | 'running' | 'completed' | 'failed' | undefined,
          content: data.content
        })
      }
    },
    onTimelineUpdate: (data: { node_id: string; agent: string; node_type: string; description: string; status: string; parent_id?: string; timestamp: string }) => {
      if (activeSessionId) {
        addTimelineEntry(activeSessionId, {
          node_id: data.node_id,
          agent: data.agent,
          node_type: data.node_type,
          description: data.description,
          status: data.status as 'pending' | 'running' | 'completed' | 'failed',
          timestamp: data.timestamp,
          parent_id: data.parent_id
        })
      }
    },
    onMessageChunk: (data: { content: string }) => {
      if (activeSessionId) {
        const currentMessages = messages[activeSessionId] || []
        const lastMessage = currentMessages[currentMessages.length - 1]

        if (lastMessage && lastMessage.role === 'assistant') {
          updateMessage(activeSessionId, lastMessage.id, {
            content: lastMessage.content + data.content
          })
        } else {
          addMessage(activeSessionId, {
            id: `temp-${Date.now()}`,
            role: 'assistant',
            content: data.content,
            agent_type: 'master',
            created_at: new Date().toISOString()
          })
        }
      }
    },
    onError: (data: {
      error: { error_type: string; message: string; timestamp: string; retry_count: number; max_retries: number; can_retry: boolean }
      step_info?: { type: string; description: string; step_number: number }
      intervention_options: { retry: boolean; skip: boolean; abort: boolean }
      user_friendly?: { title: string; description: string; suggestion: string; severity: string }
      suggested_actions?: string[]
    }) => {
      console.error('SSE Error:', data)

      // Set pending error for the modal
      const pendingErrorData: PendingError = {
        error: data.error,
        step_info: data.step_info,
        intervention_options: data.intervention_options,
        timestamp: new Date().toISOString(),
      }
      setPendingError(pendingErrorData)
      setIsIntervening(true)
    },
    onRetry: (data: { retry_count: number; max_retries: number; delay: number }) => {
      console.log('Retry attempt:', data)
    },
    onIntervention: (data: { action: string; error: Record<string, unknown> | null }) => {
      console.log('User intervention:', data)
      setIsIntervening(false)
      clearErrorState()
    },
    onComplete: (data: { message_id: string }) => {
      console.log('Complete:', data)
      setIsIntervening(false)
      clearErrorState()
    }
  }), [activeSessionId, addThought, updateAgentStep, setWorkingMemory, setActiveNode, addTimelineEntry, updateNode, messages, updateMessage, addMessage, setPendingError, clearErrorState])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages])

  // SSE integration for real-time updates - use memoized handlers to prevent infinite loops
  useSSE(activeSessionId, sseHandlers)

  // Handle user intervention actions
  const handleRetry = async () => {
    if (!activeSessionId) return
    
    try {
      await chatApi.intervene(activeSessionId, 'retry')
    } catch (error) {
      console.error('Failed to send retry action:', error)
    }
  }

  const handleSkip = async () => {
    if (!activeSessionId) return
    
    try {
      await chatApi.intervene(activeSessionId, 'skip')
    } catch (error) {
      console.error('Failed to send skip action:', error)
    }
  }

  const handleAbort = async () => {
    if (!activeSessionId) return
    
    try {
      await chatApi.intervene(activeSessionId, 'abort')
    } catch (error) {
      console.error('Failed to send abort action:', error)
    }
  }

  const handleCloseErrorModal = () => {
    setIsIntervening(false)
    clearErrorState()
  }

  // Show skeleton loading state when no messages and loading
  if (sessionMessages.length === 0 && isChatLoading) {
    return (
      <SkeletonChatContainer />
    )
  }

  // Show empty state when no messages
  if (sessionMessages.length === 0) {
    return (
      <div className="flex-1 flex flex-col">
        <ToastContainer />
        <ExampleCards onSelect={handleSelectExample} />
        <InputBox />
      </div>
    )
  }

  // Show messages with progress steps and input at bottom
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ToastContainer />
      {/* Error Modal */}
      <ErrorModal
        isOpen={isIntervening && pendingError !== null}
        onClose={handleCloseErrorModal}
        error={pendingError?.error || null}
        interventionOptions={pendingError?.intervention_options || { retry: true, skip: true, abort: true }}
        onRetry={handleRetry}
        onSkip={handleSkip}
        onAbort={handleAbort}
      />

      {/* Working memory visualization */}
      {activeSessionId && workingMemory[activeSessionId] && (
        <WorkingMemoryVisualization
          memory={workingMemory[activeSessionId]}
        />
      )}

      {/* Progress steps - shows when there are active steps */}
      <ProgressSteps steps={currentSteps} />
      
      {/* Messages area - scrollable */}
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
      
      {/* Input box */}
      <InputBox
        initialValue={editingMessage?.content || ''}
        onSubmit={handleSubmitEditedMessage}
        onCancel={handleCancelEdit}
      />
    </div>
  )
}
