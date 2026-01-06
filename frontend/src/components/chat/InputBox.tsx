import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Zap } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'

interface InputBoxProps {
  initialValue?: string
  onSubmit?: (content: string) => void
  onCancel?: () => void
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export default function InputBox({ initialValue = '', onSubmit, onCancel }: InputBoxProps) {
  const [input, setInput] = useState(initialValue)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const isEditing = !!onSubmit
  const { isDeepSearchEnabled, toggleDeepSearch, isLoading } = useChatStore()
  const { sendMessage } = useChat()
  const charCount = input.length
  const maxChars = 10000

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [input])

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      if (isEditing && onSubmit) {
        onSubmit(input.trim())
      } else {
        sendMessage(input.trim(), isDeepSearchEnabled)
      }
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-border bg-background pb-2">
      <div className="max-w-3xl mx-auto px-4">
          <div className="flex items-end gap-3 bg-secondary border border-border rounded-2xl px-4 py-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isLoading}
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-foreground placeholder:text-muted-foreground min-h-[24px] max-h-[200px]"
          />

          <div className="flex items-center gap-2 shrink-0">
            {isEditing && onCancel && (
              <button
                onClick={onCancel}
                className="px-3 py-1.5 rounded-full text-sm font-medium transition-all border bg-background text-muted-foreground border-border hover:bg-muted"
              >
                Cancel
              </button>
            )}
            <button
              onClick={toggleDeepSearch}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all border",
                isDeepSearchEnabled
                  ? "bg-primary text-primary-foreground border-primary shadow-lg ring-2 ring-primary/30"
                  : "bg-background text-muted-foreground border-border hover:bg-muted hover:border-muted-foreground/30"
              )}
              title="Enable Deep Search for comprehensive research"
            >
              <Zap className={cn("w-4 h-4", isDeepSearchEnabled && "fill-current")} />
              <span className="hidden sm:inline">Deep Search</span>
            </button>

            <button
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading}
              className={cn(
                "p-2 rounded-full transition-all border",
                input.trim() && !isLoading
                  ? "bg-primary text-primary-foreground border-primary hover:opacity-90 active:scale-95 active:shadow-inner"
                  : "bg-background text-muted-foreground border-border cursor-not-allowed opacity-50"
              )}
              aria-label="Send message"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground text-center mt-1 flex items-center justify-center gap-2">
          <span>
            {isDeepSearchEnabled
              ? "Deep Search enabled - AI agents will research and verify information"
              : "Press Enter to send, Shift+Enter for new line"}
          </span>
          <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono hidden sm:inline">
            ⌘+/
          </kbd>
        </p>

        <div className="flex items-center justify-center gap-1 mt-0">
          <span
            className={cn(
              "text-xs font-medium",
              charCount >= maxChars
                ? "text-red-500"
                : charCount >= maxChars * 0.9
                  ? "text-yellow-500"
                  : charCount >= maxChars * 0.8
                    ? "text-yellow-500/80"
                    : "text-foreground"
            )}
          >
            {charCount.toLocaleString()}
          </span>
          <span className="text-xs text-muted-foreground">/ {maxChars.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}
