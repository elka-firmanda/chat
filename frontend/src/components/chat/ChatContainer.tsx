import { useEffect, useRef } from 'react'
import { MessageSquare, Bot } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'
import Message from './Message'
import ExampleCards from './ExampleCards'
import InputBox from './InputBox'
import { useChat } from '../../hooks/useChat'
import { useSessions } from '../../hooks/useSessions'
import { useSSE } from '../../hooks/useSSE'

export default function ChatContainer() {
  const { 
    activeSessionId, 
    messages, 
    isDeepSearchEnabled,
    addMessage,
    updateAgentStep,
    setAgentSteps
  } = useChatStore()
  
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const { sendMessage } = useChat()
  const { loadSession } = useSessions()
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
      // Add thinking block to the last assistant message
      console.log('Thought:', data)
    },
    onStepUpdate: (data) => {
      // Update progress step
      if (activeSessionId) {
        updateAgentStep(activeSessionId, data.step_id, {
          status: data.status,
          logs: data.logs
        })
      }
    },
    onMessageChunk: (data) => {
      // Stream assistant response
      if (activeSessionId) {
        const sessionMessages = useChatStore.getState().messages[activeSessionId] || []
        const lastMessage = sessionMessages[sessionMessages.length - 1]
        
        if (lastMessage && lastMessage.role === 'assistant') {
          // Update existing message with new chunk
          lastMessage.content += data.content
          useChatStore.getState().addMessage(activeSessionId, lastMessage)
        } else {
          // Create new assistant message
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
    },
    onComplete: (data) => {
      // Finalize message
      console.log('Complete:', data)
    }
  })

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
  
  // Show messages with input at bottom
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
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
