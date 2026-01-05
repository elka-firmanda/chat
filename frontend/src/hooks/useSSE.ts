import { useEffect, useState, useCallback, useRef } from 'react'
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

interface ReconnectState {
  isReconnecting: boolean
  retryCount: number
  maxRetries: number
  nextRetryDelay: number
  lastEventId: string | null
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
    user_friendly?: {
      title: string
      description: string
      suggestion: string
      severity: string
    }
    suggested_actions?: string[]
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
  onReconnectAttempt?: (data: { retryCount: number; delay: number }) => void
  onReconnectSuccess?: (data: { retryCount: number }) => void
  onHeartbeat?: () => void
}

const MAX_RETRY_DELAY = 30000
const INITIAL_RETRY_DELAY = 1000
const HEARTBEAT_INTERVAL = 30000
const MAX_RECONNECT_ATTEMPTS = 10

function calculateNextDelay(currentDelay: number): number {
  return Math.min(currentDelay * 2, MAX_RETRY_DELAY)
}

export function useSSE(sessionId: string | null, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reconnectState, setReconnectState] = useState<ReconnectState>({
    isReconnecting: false,
    retryCount: 0,
    maxRetries: MAX_RECONNECT_ATTEMPTS,
    nextRetryDelay: INITIAL_RETRY_DELAY,
    lastEventId: null,
  })

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const currentDelayRef = useRef(INITIAL_RETRY_DELAY)
  const lastEventIdRef = useRef<string | null>(null)
  const previousSessionIdRef = useRef<string | null>(null)

  const cleanupEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
      heartbeatTimeoutRef.current = null
    }
  }, [])

  const setupHeartbeat = useCallback((es: EventSource) => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      if (es.readyState === EventSource.OPEN) {
        options.onHeartbeat?.()
        setupHeartbeat(es)
      }
    }, HEARTBEAT_INTERVAL)
  }, [options])

  const handleSuccessfulConnection = useCallback((es: EventSource, retryCount: number) => {
    setIsConnected(true)
    setError(null)
    setReconnectState(prev => ({
      ...prev,
      isReconnecting: false,
      retryCount: 0,
      nextRetryDelay: INITIAL_RETRY_DELAY,
    }))
    reconnectAttemptsRef.current = 0
    currentDelayRef.current = INITIAL_RETRY_DELAY
    setupHeartbeat(es)
    options.onReconnectSuccess?.({ retryCount })
  }, [setupHeartbeat, options])

  const attemptReconnect = useCallback(() => {
    if (!sessionId) return

    const retryCount = reconnectAttemptsRef.current + 1
    const delay = currentDelayRef.current

    if (retryCount > MAX_RECONNECT_ATTEMPTS) {
      setError('Max reconnection attempts reached. Please refresh the page.')
      setReconnectState(prev => ({ ...prev, isReconnecting: false }))
      return
    }

    setReconnectState(prev => ({
      ...prev,
      isReconnecting: true,
      retryCount,
      nextRetryDelay: delay,
    }))

    reconnectAttemptsRef.current = retryCount
    currentDelayRef.current = calculateNextDelay(currentDelayRef.current)

    options.onReconnectAttempt?.({ retryCount, delay })

    reconnectTimeoutRef.current = setTimeout(() => {
      const es = chatApi.stream(sessionId, lastEventIdRef.current || undefined)
      eventSourceRef.current = es

      es.onopen = () => {
        handleSuccessfulConnection(es, retryCount)
      }

      es.onerror = (err) => {
        console.error('SSE reconnection error:', err)
        cleanupEventSource()
        attemptReconnect()
      }

      es.addEventListener('thought', (e) => {
        const data = JSON.parse(e.data) as { agent: string; content: string }
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onThought?.(data)
      })

      es.addEventListener('step_update', (e) => {
        const data = JSON.parse(e.data) as { step_id: string; status: string; description: string; logs?: string }
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onStepUpdate?.(data)
      })

      es.addEventListener('step_progress', (e) => {
        const data = JSON.parse(e.data) as StepProgressEvent
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onStepProgress?.(data)
      })

      es.addEventListener('memory_update', (e) => {
        const data = JSON.parse(e.data) as MemoryUpdateEvent
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onMemoryUpdate?.(data)
      })

      es.addEventListener('node_added', (e) => {
        const data = JSON.parse(e.data) as NodeAddedEvent
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onNodeAdded?.(data)
      })

      es.addEventListener('node_updated', (e) => {
        const data = JSON.parse(e.data) as NodeUpdatedEvent
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onNodeUpdated?.(data)
      })

      es.addEventListener('timeline_update', (e) => {
        const data = JSON.parse(e.data) as TimelineUpdateEvent
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onTimelineUpdate?.(data)
      })

      es.addEventListener('message_chunk', (e) => {
        const data = JSON.parse(e.data) as { content: string }
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        options.onMessageChunk?.(data)
      })

      es.addEventListener('error', (e) => {
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
            user_friendly?: {
              title: string
              description: string
              suggestion: string
              severity: string
            }
            suggested_actions?: string[]
          }
          setError(data.error.message)

          console.group('🚨 Error occurred (check for details)')
          console.error('Error Type:', data.error.error_type)
          console.error('Message:', data.error.message)
          console.error('Timestamp:', data.error.timestamp)
          console.error('Retry:', `${data.error.retry_count}/${data.error.max_retries}`)
          if (data.user_friendly) {
            console.log('User Friendly:', data.user_friendly)
          }
          if (data.suggested_actions) {
            console.log('Suggested Actions:', data.suggested_actions)
          }
          console.groupEnd()

          options.onError?.(data)
        } catch (parseError) {
          const legacyData = JSON.parse(e.data) as { message: string; retry_count: number }
          setError(legacyData.message)
          console.error('Error parsing SSE event:', parseError)
          console.error('Raw error data:', legacyData)
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

      es.addEventListener('retry', (e) => {
        const data = JSON.parse(e.data) as {
          retry_count: number
          max_retries: number
          delay: number
        }
        options.onRetry?.(data)
      })

      es.addEventListener('intervention', (e) => {
        const data = JSON.parse(e.data) as {
          action: string
          error: Record<string, unknown> | null
        }
        options.onIntervention?.(data)
      })

      es.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data) as { message_id: string }
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId
        }
        setIsConnected(false)
        cleanupEventSource()
        options.onComplete?.(data)
      })

      es.onerror = (err) => {
        console.error('SSE error:', err)
        cleanupEventSource()
        setIsConnected(false)
        setError('Connection lost')
        attemptReconnect()
      }
    }, delay)
  }, [sessionId, options, cleanupEventSource, handleSuccessfulConnection])

  const manualReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    reconnectAttemptsRef.current = 0
    currentDelayRef.current = INITIAL_RETRY_DELAY
    cleanupEventSource()
    attemptReconnect()
  }, [cleanupEventSource, attemptReconnect])

  useEffect(() => {
    if (!sessionId) {
      setIsConnected(false)
      setReconnectState(prev => ({ ...prev, isReconnecting: false, retryCount: 0 }))
      return
    }

    if (previousSessionIdRef.current && previousSessionIdRef.current !== sessionId) {
      chatApi.cancel(previousSessionIdRef.current).catch(console.error)
    }
    previousSessionIdRef.current = sessionId

    setError(null)
    cleanupEventSource()
    const es = chatApi.stream(sessionId)
    eventSourceRef.current = es

    es.onopen = () => {
      handleSuccessfulConnection(es, 0)
    }

    es.addEventListener('thought', (e) => {
      const data = JSON.parse(e.data) as { agent: string; content: string }
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onThought?.(data)
    })

    es.addEventListener('step_update', (e) => {
      const data = JSON.parse(e.data) as { step_id: string; status: string; description: string; logs?: string }
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onStepUpdate?.(data)
    })

    es.addEventListener('step_progress', (e) => {
      const data = JSON.parse(e.data) as StepProgressEvent
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onStepProgress?.(data)
    })

    es.addEventListener('memory_update', (e) => {
      const data = JSON.parse(e.data) as MemoryUpdateEvent
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onMemoryUpdate?.(data)
    })

    es.addEventListener('node_added', (e) => {
      const data = JSON.parse(e.data) as NodeAddedEvent
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onNodeAdded?.(data)
    })

    es.addEventListener('node_updated', (e) => {
      const data = JSON.parse(e.data) as NodeUpdatedEvent
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onNodeUpdated?.(data)
    })

    es.addEventListener('timeline_update', (e) => {
      const data = JSON.parse(e.data) as TimelineUpdateEvent
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onTimelineUpdate?.(data)
    })

    es.addEventListener('message_chunk', (e) => {
      const data = JSON.parse(e.data) as { content: string }
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
        setReconnectState(prev => ({ ...prev, lastEventId: e.lastEventId }))
      }
      options.onMessageChunk?.(data)
    })

      es.addEventListener('error', (e) => {
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
            user_friendly?: {
              title: string
              description: string
              suggestion: string
              severity: string
            }
            suggested_actions?: string[]
          }
          setError(data.error.message)

          console.group('🚨 Error occurred (check for details)')
          console.error('Error Type:', data.error.error_type)
          console.error('Message:', data.error.message)
          console.error('Timestamp:', data.error.timestamp)
          console.error('Retry:', `${data.error.retry_count}/${data.error.max_retries}`)
          if (data.user_friendly) {
            console.log('User Friendly:', data.user_friendly)
          }
          if (data.suggested_actions) {
            console.log('Suggested Actions:', data.suggested_actions)
          }
          console.groupEnd()

          options.onError?.(data)
        } catch (parseError) {
          const legacyData = JSON.parse(e.data) as { message: string; retry_count: number }
          setError(legacyData.message)
          console.error('Error parsing SSE event:', parseError)
          console.error('Raw error data:', legacyData)
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

    es.addEventListener('retry', (e) => {
      const data = JSON.parse(e.data) as {
        retry_count: number
        max_retries: number
        delay: number
      }
      options.onRetry?.(data)
    })

    es.addEventListener('intervention', (e) => {
      const data = JSON.parse(e.data) as {
        action: string
        error: Record<string, unknown> | null
      }
      options.onIntervention?.(data)
    })

    es.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data) as { message_id: string }
      if (e.lastEventId) {
        lastEventIdRef.current = e.lastEventId
      }
      setIsConnected(false)
      cleanupEventSource()
      options.onComplete?.(data)
    })

    es.onerror = (err) => {
      console.error('SSE error:', err)
      cleanupEventSource()
      setIsConnected(false)
      setError('Connection lost')
      attemptReconnect()
    }

    return () => {
      cleanupEventSource()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      setIsConnected(false)
    }
  }, [sessionId, options, cleanupEventSource, attemptReconnect, handleSuccessfulConnection])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    cleanupEventSource()
    setIsConnected(false)
    setReconnectState(prev => ({
      ...prev,
      isReconnecting: false,
      retryCount: 0,
      nextRetryDelay: INITIAL_RETRY_DELAY,
    }))
    reconnectAttemptsRef.current = 0
    currentDelayRef.current = INITIAL_RETRY_DELAY
  }, [cleanupEventSource])

  return {
    isConnected,
    error,
    disconnect,
    reconnectState,
    manualReconnect,
  }
}
