import { useEffect, useRef, useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'
import { useChatErrorStore, PendingError } from '../../stores/errorStore'
import { chatApi } from '../../services/api'
import Message from './Message'
import ExampleCards from './ExampleCards'
import InputBox from './InputBox'
import ProgressSteps from './ProgressSteps'
import WorkingMemoryVisualization from './WorkingMemoryVisualization'
import ErrorModal from './ErrorModal'
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
  
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const currentSteps = activeSessionId ? agentSteps[activeSessionId] || [] : []
  const { sendMessage, isLoading: isChatLoading } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useSessionCancellation(activeSessionId)

  const handleSelectExample = async (question: string) => {
    await sendMessage(question, isDeepSearchEnabled)
  }

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages])

  // SSE integration for real-time updates
  useSSE(activeSessionId, {
    onThought: (data) => {
      if (activeSessionId) {
        addThought(activeSessionId, data.agent, data.content)
      }
    },
    onStepUpdate: (data) => {
      if (activeSessionId) {
        updateAgentStep(activeSessionId, data.step_id, {
          status: data.status as 'pending' | 'running' | 'completed' | 'failed',
          logs: data.logs
        })
      }
    },
    onMemoryUpdate: (data) => {
      if (activeSessionId) {
        setWorkingMemory(activeSessionId, {
          memory_tree: data.memory_tree as any,
          timeline: data.timeline as any,
          index: data.index as any,
          stats: data.stats
        })
      }
    },
    onNodeAdded: (data) => {
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
    onNodeUpdated: (data) => {
      if (activeSessionId) {
        updateNode(activeSessionId, data.node_id, {
          status: data.status as 'pending' | 'running' | 'completed' | 'failed',
          content: data.content
        })
      }
    },
    onTimelineUpdate: (data) => {
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
    onMessageChunk: (data) => {
      if (activeSessionId) {
        const sessionMessages = messages[activeSessionId] || []
        const lastMessage = sessionMessages[sessionMessages.length - 1]

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
    onError: (data) => {
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
    onRetry: (data) => {
      console.log('Retry attempt:', data)
    },
    onIntervention: (data) => {
      console.log('User intervention:', data)
      setIsIntervening(false)
      clearErrorState()
    },
    onComplete: (data) => {
      console.log('Complete:', data)
      setIsIntervening(false)
      clearErrorState()
    }
  })

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
        {/* Welcome header */}
        <div className="flex-1 flex flex-col items-center justify-center p-4 md:p-8">
          <div className="w-16 h-16 md:w-20 md:h-20 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 md:mb-6">
            <MessageSquare size={32} className="md:size-40" />
          </div>
          <h1 className="text-xl md:text-2xl font-semibold text-center mb-2">
            How can I help you today?
          </h1>
          <p className="text-muted-foreground text-center text-sm md:text-base max-w-md">
            Ask me anything about research, data analysis, or general questions.
          </p>
        </div>
        
        {/* Example cards */}
        <div className="p-4 md:p-6 border-t bg-muted/30">
          <ExampleCards onSelect={handleSelectExample} />
        </div>
        
        {/* Input box */}
        <InputBox />
      </div>
    )
  }
  
  // Show messages with progress steps and input at bottom
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Error Modal */}
      <ErrorModal
        isOpen={isIntervening && pendingError !== null}
        onClose={handleCloseErrorModal}
        error={pendingError?.error || null}
        interventionOptions={pendingError?.intervention_options || { retry: true, skip: true, abort: true }}
        sessionId={activeSessionId || ''}
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
      <div className="flex-1 overflow-auto p-3 md:p-4 space-y-3 md:space-y-4">
        {sessionMessages.map((message) => (
          <Message key={message.id} message={message} />
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
      <InputBox />
    </div>
  )
}
