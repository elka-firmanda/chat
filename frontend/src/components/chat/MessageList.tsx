import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { User, Bot, Loader2, ChevronDown, ChevronRight, Check, Circle, XCircle } from 'lucide-react'
import { Message } from '../../stores/chatStore'
import { useChatStore } from '../../stores/chatStore'
import ChartDisplay from './ChartDisplay'
import ExportButton from './ExportButton'

interface MessageListProps {
  messages: Message[]
  isLoading?: boolean
  currentActivity?: string | null
  plan?: PlanStep[]
  streamingContent?: string
}

interface PlanStep {
  id: string
  step_number: number
  agent?: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  logs?: string
}

interface ExtractedChart {
  filename: string
  data: string
}

function extractChartsFromContent(content: string): { text: string; charts: ExtractedChart[] } {
  const chartRegex = /<!-- CHARTS:(\[[\s\S]*?\]):CHARTS -->/g
  const match = chartRegex.exec(content)

  if (!match) {
    return { text: content, charts: [] }
  }

  try {
    const charts = JSON.parse(match[1]) as ExtractedChart[]
    const text = content.replace(chartRegex, '').trim()
    return { text, charts }
  } catch {
    return { text: content, charts: [] }
  }
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MessageList({
  messages,
  isLoading,
  currentActivity,
  plan,
  streamingContent
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [planExpanded, setPlanExpanded] = useState(true)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, currentActivity, plan, streamingContent])

  if (messages.length === 0) {
    return null
  }

  const hasPlan = plan && plan.length > 0

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-medium">Assistant</span>
              </div>

              {streamingContent ? (
                <div className="bg-secondary rounded-2xl px-4 py-3 inline-block max-w-full text-left">
                  <div className="markdown-content prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                  </div>
                </div>
              ) : (
                <div className="bg-secondary rounded-2xl px-4 py-3 inline-block">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">
                      {currentActivity || 'Thinking...'}
                    </span>
                  </div>
                </div>
              )}

              {hasPlan && !streamingContent && (
                <div className="mt-3">
                  <button
                    onClick={() => setPlanExpanded(!planExpanded)}
                    className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {planExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <span>
                      Execution Plan ({plan.filter((s) => s.status === 'completed').length}/{plan.length} steps)
                    </span>
                  </button>

                  {planExpanded && (
                    <div className="mt-2 ml-1 space-y-2 border-l-2 border-border pl-4">
                      {plan.map((step, index) => (
                        <StepItem key={step.id} step={step} index={index} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function StepItem({ step, index }: { step: PlanStep; index: number }) {
  const getStatusIcon = () => {
    switch (step.status) {
      case 'completed':
        return (
          <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
            <Check className="w-3 h-3 text-white" />
          </div>
        )
      case 'running':
        return (
          <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
            <Loader2 className="w-3 h-3 text-white animate-spin" />
          </div>
        )
      case 'failed':
        return (
          <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
            <XCircle className="w-3 h-3 text-white" />
          </div>
        )
      default:
        return (
          <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30 flex items-center justify-center">
            <Circle className="w-2 h-2 text-muted-foreground/30" />
          </div>
        )
    }
  }

  const agentColors: Record<string, string> = {
    researcher: 'text-blue-600 dark:text-blue-400',
    tools: 'text-purple-600 dark:text-purple-400',
    master: 'text-green-600 dark:text-green-400',
    database: 'text-orange-600 dark:text-orange-400',
    python: 'text-yellow-600 dark:text-yellow-400'
  }

  const agent = step.agent || 'unknown'
  const agentColor = agentColors[agent] || 'text-gray-600'

  return (
    <div className={`flex items-start gap-2 transition-opacity ${step.status === 'pending' ? 'opacity-50' : ''}`}>
      <div className="shrink-0 mt-0.5">{getStatusIcon()}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${step.status === 'completed' ? 'line-through text-muted-foreground' : ''}`}>
            Step {index + 1}
          </span>
          <span className={`text-xs ${agentColor}`}>{agent}</span>
        </div>
        <p className={`text-xs mt-0.5 leading-relaxed ${step.status === 'completed' ? 'text-muted-foreground' : 'text-foreground'}`}>
          {step.description}
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const { text: displayContent, charts } = isUser
    ? { text: message.content, charts: [] }
    : extractChartsFromContent(message.content)

  const sessionId = useChatStore((state) => state.activeSessionId)
  const hasComparisonResults =
    !isUser && Boolean((message.metadata?.agent_results as Record<string, unknown> | undefined)?.comparison)

  return (
    <div className={`flex items-start gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? 'bg-secondary' : 'bg-primary/10'
        }`}
      >
        {isUser ? <User className="w-5 h-5 text-foreground" /> : <Bot className="w-5 h-5 text-primary" />}
      </div>

      <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : ''}`}>
        <div className={`flex items-center gap-2 mb-2 ${isUser ? 'justify-end' : ''}`}>
          <span className="font-medium">{isUser ? 'You' : 'Assistant'}</span>
          <span className="text-xs text-muted-foreground">{formatTime(message.created_at)}</span>
        </div>

        <div
          className={`rounded-2xl px-4 py-3 inline-block max-w-full text-left ${
            isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="markdown-content prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown>
            </div>
          )}
        </div>

        {charts.length > 0 && <ChartDisplay charts={charts} />}

        {message.metadata?.deep_search === true && (
          <div className="mt-2">
            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">Deep Search</span>
          </div>
        )}

        {hasComparisonResults && sessionId && (
          <div className="mt-3">
            <ExportButton sessionId={sessionId} />
          </div>
        )}
      </div>
    </div>
  )
}
