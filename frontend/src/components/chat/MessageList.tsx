import { useChatStore } from '../../stores/chatStore'
import Message from './Message'

export default function MessageList() {
  const { activeSessionId, messages } = useChatStore()
  const sessionMessages = activeSessionId ? messages[activeSessionId] || [] : []
  
  if (sessionMessages.length === 0) {
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
    <div className="flex-1 overflow-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
      {sessionMessages.map((message) => (
        <Message key={message.id} message={message} />
      ))}
    </div>
  )
}
