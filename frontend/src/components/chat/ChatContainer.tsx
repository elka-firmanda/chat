import { useChatStore } from '../../stores/chatStore'
import Message from './Message'
import ExampleCards from './ExampleCards'
import { useChat } from '../../hooks/useChat'
import { useSessions } from '../../hooks/useSessions'
import { MessageSquare } from 'lucide-react'

export default function ChatContainer() {
  const { activeSessionId, messages, isDeepSearchEnabled } = useChatStore()
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  const { sendMessage } = useChat()
  const { loadSession } = useSessions()
  
  const handleSelectExample = async (question: string) => {
    await sendMessage(question, isDeepSearchEnabled)
  }
  
  const handleNewChat = () => {
    useChatStore.getState().setActiveSession(null)
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
  
  // Show messages with input at bottom
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-auto p-3 md:p-4 space-y-3 md:space-y-4">
        {sessionMessages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
      </div>
      
      {/* Input box */}
      <InputBox />
    </div>
  )
}

// Import InputBox locally to avoid circular dependency
import InputBox from './InputBox'
