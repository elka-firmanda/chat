import { useState } from 'react'
import { Message as MessageType } from '../../stores/chatStore'
import ThinkingBlock from './ThinkingBlock'
import { Copy, Check } from 'lucide-react'

interface MessageProps {
  message: MessageType
}

export default function MessageComponent({ message }: MessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} px-2 md:px-0`}>
      <div className={`max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 md:px-5 ${
        isUser 
          ? 'bg-primary text-primary-foreground rounded-br-md' 
          : 'bg-muted rounded-bl-md'
      }`}>
        {/* Agent thinking block for assistant messages */}
        {!isUser && message.agent_type && (
          <ThinkingBlock 
            agent={message.agent_type as any} 
            content="Agent processing..."
            defaultCollapsed={true}
          />
        )}
        
        {/* Message content */}
        <div className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
          {message.content}
        </div>
        
        {/* Actions bar */}
        {!isUser && (
          <div className="flex items-center gap-1 mt-2 pt-2 border-t border-current/10">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-current/10 rounded transition-colors"
              title="Copy message"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        )}
        
        {/* Timestamp */}
        <div className={`text-[10px] md:text-xs mt-2 ${
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
