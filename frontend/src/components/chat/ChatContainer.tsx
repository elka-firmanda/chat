import { useEffect, useRef, useState } from 'react'
import { MessageSquare, Bot } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'
import { useChatErrorStore, PendingError } from '../../stores/errorStore'
import { chatApi } from '../../services/api'
import Message from './Message'
import ExampleCards from './ExampleCards'
import InputBox from './InputBox'
import ProgressSteps from './ProgressSteps'
import ErrorModal from './ErrorModal'
import { useChat } from '../../hooks/useChat'
import { useSessions } from '../../hooks/useSessions'
import { useSSE } from '../../hooks/useSSE'

export default function ChatContainer() {
  const { 
    activeSessionId, 
    messages, 
    isDeepSearchEnabled,
    agentSteps,
    addMessage,
    updateAgentStep,
    setAgentSteps
  } = useChatStore()
  
  const { 
    pendingError, 
    setPendingError,
    clearErrorState 
  } = useChatErrorStore()
  
  const [isIntervening, setIsIntervening] = useState(false)
  
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const currentSteps = activeSessionId ? agentSteps[activeSessionId] || [] : []
  const { sendMessage } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const handleSelectExample = async (question: string) => {
    await sendMessage(question, isDeepSearchEnabled)
  }
  
  const handleNewChat = () => {
    useChatStore.getState().setActiveSession(null)
  }

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [sessionMessages])

  // SSE integration for real-time updates
  useSSE(activeSessionId, {
    onThought: (data) => {
      console.log('Thought:', data)
    },
    onStepUpdate: (data) => {
      if (activeSessionId) {
        updateAgentStep(activeSessionId, data.step_id, {
          status: data.status,
          logs: data.logs
        })
      }
    },
    onMessageChunk: (data) => {
      if (activeSessionId) {
        const sessionMessages = useChatStore.getState().messages[activeSessionId] || []
        const lastMessage = sessionMessages[sessionMessages.length - 1]
        
        if (lastMessage && lastMessage.role === 'assistant') {
          lastMessage.content += data.content
          useChatStore.getState().addMessage(activeSessionId, lastMessage)
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
      
      {/* Progress steps - shows when there are active steps */}
      <ProgressSteps steps={currentSteps} />
      
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-auto p-3 md:p-4 space-y-3 md:space-y-4">
        {sessionMessages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input box */}
      <InputBox />
    </div>
  )
}
