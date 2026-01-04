import { useEffect, useState, useCallback } from 'react'
import { chatApi } from '../services/api'

interface SSEEvent {
  type: string
  data: Record<string, unknown>
}

interface MemoryUpdateEvent {
  update_type: 'full' | 'incremental' | 'node_add' | 'node_update'
  memory_tree: Record<string, unknown>
  timeline: Array<{
    node_id: string
    agent: string
    node_type: string
    description: string
    status: string
    timestamp: string
    parent_id?: string
  }>
  index: Record<string, unknown>
  stats: {
    total_nodes: number
    timeline_length: number
  }
}

interface NodeAddedEvent {
  node_id: string
  agent: string
  node_type: string
  description: string
  parent_id?: string
  content?: Record<string, unknown>
  timestamp: string
}

interface NodeUpdatedEvent {
  node_id: string
  status?: string
  content?: Record<string, unknown>
  completed: boolean
  timestamp: string
}

interface TimelineUpdateEvent {
  node_id: string
  agent: string
  node_type: string
  description: string
  status: string
  parent_id?: string
  timestamp: string
}

interface StepProgressEvent {
  step_id: string
  step_number: number
  total_steps: number
  agent: string
  status: string
  description: string
  logs?: string
  progress_percentage: number
}

interface UseSSEOptions {
  onThought?: (data: { agent: string; content: string }) => void
  onStepUpdate?: (data: { step_id: string; status: string; description: string; logs?: string }) => void
  onStepProgress?: (data: StepProgressEvent) => void
  onMemoryUpdate?: (data: MemoryUpdateEvent) => void
  onNodeAdded?: (data: NodeAddedEvent) => void
  onNodeUpdated?: (data: NodeUpdatedEvent) => void
  onTimelineUpdate?: (data: TimelineUpdateEvent) => void
  onMessageChunk?: (data: { content: string }) => void
  onError?: (data: {
    error: {
      error_type: string
      message: string
      timestamp: string
      retry_count: number
      max_retries: number
      can_retry: boolean
    }
    step_info?: {
      type: string
      description: string
      step_number: number
    }
    intervention_options: {
      retry: boolean
      skip: boolean
      abort: boolean
    }
  }) => void
  onRetry?: (data: {
    retry_count: number
    max_retries: number
    delay: number
  }) => void
  onIntervention?: (data: {
    action: string
    error: Record<string, unknown> | null
  }) => void
  onComplete?: (data: { message_id: string }) => void
}

export function useSSE(sessionId: string | null, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    if (!sessionId) {
      setIsConnected(false)
      return
    }
    
    setError(null)
    const eventSource = chatApi.stream(sessionId)
    
    eventSource.onopen = () => {
      setIsConnected(true)
      setError(null)
    }
    
    eventSource.addEventListener('thought', (e) => {
      const data = JSON.parse(e.data) as { agent: string; content: string }
      options.onThought?.(data)
    })
    
    eventSource.addEventListener('step_update', (e) => {
      const data = JSON.parse(e.data) as { step_id: string; status: string; description: string; logs?: string }
      options.onStepUpdate?.(data)
    })

    eventSource.addEventListener('step_progress', (e) => {
      const data = JSON.parse(e.data) as StepProgressEvent
      options.onStepProgress?.(data)
    })

    eventSource.addEventListener('memory_update', (e) => {
      const data = JSON.parse(e.data) as MemoryUpdateEvent
      options.onMemoryUpdate?.(data)
    })

    eventSource.addEventListener('node_added', (e) => {
      const data = JSON.parse(e.data) as NodeAddedEvent
      options.onNodeAdded?.(data)
    })

    eventSource.addEventListener('node_updated', (e) => {
      const data = JSON.parse(e.data) as NodeUpdatedEvent
      options.onNodeUpdated?.(data)
    })

    eventSource.addEventListener('timeline_update', (e) => {
      const data = JSON.parse(e.data) as TimelineUpdateEvent
      options.onTimelineUpdate?.(data)
    })
    
    eventSource.addEventListener('message_chunk', (e) => {
      const data = JSON.parse(e.data) as { content: string }
      options.onMessageChunk?.(data)
    })
    
    eventSource.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data) as {
          error: {
            error_type: string
            message: string
            timestamp: string
            retry_count: number
            max_retries: number
            can_retry: boolean
          }
          step_info?: {
            type: string
            description: string
            step_number: number
          }
          intervention_options: {
            retry: boolean
            skip: boolean
            abort: boolean
          }
        }
        setError(data.error.message)
        options.onError?.(data)
      } catch (parseError) {
        const legacyData = JSON.parse(e.data) as { message: string; retry_count: number }
        setError(legacyData.message)
        options.onError?.({
          error: {
            error_type: 'unknown_error',
            message: legacyData.message,
            timestamp: new Date().toISOString(),
            retry_count: legacyData.retry_count,
            max_retries: 3,
            can_retry: legacyData.retry_count < 3,
          },
          intervention_options: { retry: true, skip: true, abort: true },
        })
      }
    })
    
    eventSource.addEventListener('retry', (e) => {
      const data = JSON.parse(e.data) as {
        retry_count: number
        max_retries: number
        delay: number
      }
      options.onRetry?.(data)
    })
    
    eventSource.addEventListener('intervention', (e) => {
      const data = JSON.parse(e.data) as {
        action: string
        error: Record<string, unknown> | null
      }
      options.onIntervention?.(data)
    })
    
    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data) as { message_id: string }
      setIsConnected(false)
      options.onComplete?.(data)
    })
    
    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
      setIsConnected(false)
      setError('Connection lost')
    }
    
    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [sessionId, options])
  
  const disconnect = useCallback(() => {
    setIsConnected(false)
  }, [])
  
  return {
    isConnected,
    error,
    disconnect
  }
}
