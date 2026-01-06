import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Search, Sparkles, Info, X } from 'lucide-react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { useChatStore } from '../../stores/chatStore'
import { useChat } from '../../hooks/useChat'

const MAX_MESSAGE_LENGTH = 10000
const WARNING_THRESHOLD = 8000

interface InputBoxProps {
  initialValue?: string
  onSubmit?: (content: string) => void
  onCancel?: () => void
}

export default function InputBox({ initialValue = '', onSubmit, onCancel }: InputBoxProps) {
  const [message, setMessage] = useState(initialValue)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const characterCount = message.length
  const isOverLimit = characterCount > MAX_MESSAGE_LENGTH
  const isNearLimit = characterCount >= WARNING_THRESHOLD && !isOverLimit
  const isEditing = initialValue !== ''

  const { isDeepSearchEnabled, toggleDeepSearch, isLoading } = useChatStore()
  const { sendMessage } = useChat()

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isLoading || isOverLimit) return

    const content = message.trim()
    setMessage('')

    if (onSubmit) {
      onSubmit(content)
    } else {
      try {
        await sendMessage(content, isDeepSearchEnabled)
      } catch (error) {
        console.error('Failed to send message:', error)
      }
    }
  }, [message, isLoading, isOverLimit, onSubmit, sendMessage, isDeepSearchEnabled])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [message])

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.setSelectionRange(textareaRef.current.value.length, textareaRef.current.value.length)
    }
  }, [isEditing])

  return (
    <div className="border-t bg-background">
      {isEditing && (
        <div className="px-4 py-2 bg-muted/50 border-b flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Editing message</span>
          <button
            onClick={onCancel}
            className="p-1 hover:bg-muted rounded transition-colors"
            title="Cancel editing"
          >
            <X size={16} />
          </button>
        </div>
      )}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 p-3 md:p-4"
      >
        {/* Deep search toggle with tooltip */}
        <Tooltip.Provider delayDuration={200}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button
                type="button"
                onClick={toggleDeepSearch}
                disabled={isLoading}
                className={`p-2.5 md:p-3 rounded-lg transition-all touch-manipulation ${
                  isDeepSearchEnabled
                    ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
                title={isDeepSearchEnabled ? 'Deep search enabled' : 'Deep search disabled'}
                aria-label="Toggle deep search"
              >
                {isDeepSearchEnabled ? (
                  <Sparkles size={20} className="animate-pulse" />
                ) : (
                  <Search size={20} />
                )}
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="z-50 px-3 py-2 bg-popover text-popover-foreground text-sm rounded-lg shadow-lg border max-w-xs animate-in fade-in zoom-in-95"
                sideOffset={5}
              >
                <div className="flex items-start gap-2">
                  <Info size={16} className="mt-0.5 shrink-0 text-violet-500" />
                  <div>
                    <p className="font-medium mb-0.5">Deep Search</p>
                    <p className="text-xs text-muted-foreground">
                      {isDeepSearchEnabled
                        ? 'Enabled • Uses Tavily API, web scraping, and parallel research for comprehensive answers.'
                        : 'Disabled • Click to enable deep research with Tavily API and intelligent web scraping.'}
                    </p>
                  </div>
                </div>
                <Tooltip.Arrow className="fill-popover" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>

        {/* Text input - grows to fill space */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isDeepSearchEnabled ? "Ask anything with deep research..." : "Message..."}
            className={`w-full resize-none min-h-[44px] max-h-[150px] md:max-h-[200px] p-3 pr-12 rounded-xl border focus:outline-none focus:ring-2 text-base md:text-sm transition-colors ${
              isDeepSearchEnabled
                ? 'border-violet-200 dark:border-violet-800 focus:ring-violet-500'
                : isOverLimit
                  ? 'border-red-300 dark:border-red-700 focus:ring-red-500'
                  : 'border-input focus:ring-primary'
            }`}
            rows={1}
            disabled={isLoading}
            enterKeyHint="send"
            maxLength={MAX_MESSAGE_LENGTH}
          />
          {/* Character count indicator */}
          <div className={`absolute right-3 bottom-1 translate-y-1/2 text-xs ${
            isOverLimit
              ? 'text-red-500 font-medium'
              : isNearLimit
                ? 'text-amber-500'
                : 'text-muted-foreground'
          }`}>
            {characterCount.toLocaleString()} / {MAX_MESSAGE_LENGTH.toLocaleString()}
          </div>
          {/* Deep search indicator inside input when enabled */}
          {isDeepSearchEnabled && !isLoading && (
            <div className="absolute right-10 top-1/2 -translate-y-1/2">
              <Sparkles size={14} className="text-violet-500 animate-pulse" />
            </div>
          )}
        </div>

        {/* Send button - larger touch target on mobile */}
        <button
          type="submit"
          disabled={!message.trim() || isLoading || isOverLimit}
          className={`p-2.5 md:p-3 rounded-xl transition-all touch-manipulation ${
            isDeepSearchEnabled && message.trim() && !isOverLimit
              ? 'bg-violet-600 hover:bg-violet-700 text-white'
              : 'bg-primary text-primary-foreground hover:bg-primary/90'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          aria-label={isEditing ? "Send edited message" : "Send message"}
        >
          <Send size={20} />
        </button>
      </form>

      {/* Deep search indicator */}
      {isDeepSearchEnabled && (
        <div className="px-4 pb-3 md:px-4 md:pb-4">
          <div className="flex items-center justify-center gap-2 text-xs text-violet-600 dark:text-violet-400">
            <Sparkles size={14} className="animate-pulse" />
            <span>Deep search enabled • Tavily API + intelligent web scraping</span>
          </div>
        </div>
      )}
    </div>
  )
}
