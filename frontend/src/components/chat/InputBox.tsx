import { useState, useRef, useEffect } from 'react'
import { Send, Search } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'

export default function InputBox() {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  const { isDeepSearchEnabled, toggleDeepSearch, isLoading } = useChatStore()
  const { sendMessage } = useChat()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isLoading) return
    
    const content = message.trim()
    setMessage('')
    
    try {
      await sendMessage(content, isDeepSearchEnabled)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }
  
  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [message])
  
  return (
    <div className="border-t bg-background">
      <form 
        onSubmit={handleSubmit} 
        className="flex items-end gap-2 p-3 md:p-4"
      >
        {/* Deep search toggle - larger touch target on mobile */}
        <button
          type="button"
          onClick={toggleDeepSearch}
          className={`p-2.5 md:p-3 rounded-lg transition-colors touch-manipulation ${
            isDeepSearchEnabled
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
          title={isDeepSearchEnabled ? 'Deep search enabled' : 'Deep search disabled'}
          aria-label="Toggle deep search"
        >
          <Search size={20} />
        </button>
        
        {/* Text input - grows to fill space */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            className="w-full resize-none min-h-[44px] max-h-[150px] md:max-h-[200px] p-3 pr-12 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary text-base md:text-sm"
            rows={1}
            disabled={isLoading}
            enterKeyHint="send"
          />
        </div>
        
        {/* Send button - larger touch target on mobile */}
        <button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="p-2.5 md:p-3 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-manipulation"
          aria-label="Send message"
        >
          <Send size={20} />
        </button>
      </form>
      
      {/* Deep search indicator */}
      {isDeepSearchEnabled && (
        <div className="px-4 pb-3 md:px-4 md:pb-4">
          <p className="text-xs text-muted-foreground text-center">
            Deep search enabled • Uses Tavily API and web scraping
          </p>
        </div>
      )}
    </div>
  )
}
