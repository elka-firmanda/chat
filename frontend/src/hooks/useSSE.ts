import { useEffect, useState, useCallback, useRef } from 'react'
import { chatApi } from '../services/api'

interface PlanStep {
  step_number: number
  description: string
  agent?: string
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'
}

interface UseSSEOptions {
  onToken?: (data: { token: string }) => void
  onStatus?: (data: { message: string }) => void
  onPlan?: (data: { steps: PlanStep[] }) => void
  onStepUpdate?: (data: { step_index: number; status: string; result?: string; error?: string }) => void
  onMessage?: (data: { session_id: string; message: Record<string, unknown> }) => void
  onDone?: () => void
  onError?: (data: { message: string }) => void
}

const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_RETRY_DELAY = 1000
const MAX_RETRY_DELAY = 30000

function calculateNextDelay(currentDelay: number): number {
  return Math.min(currentDelay * 2, MAX_RETRY_DELAY)
}

export function useSSE(sessionId: string | null, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const currentDelayRef = useRef(INITIAL_RETRY_DELAY)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const cleanupEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  const setupEventListeners = useCallback((es: EventSource) => {
    es.addEventListener('token', (e) => {
      const data = JSON.parse(e.data) as { token: string }
      optionsRef.current.onToken?.(data)
    })

    es.addEventListener('status', (e) => {
      const data = JSON.parse(e.data) as { message: string }
      optionsRef.current.onStatus?.(data)
    })

    es.addEventListener('plan', (e) => {
      const data = JSON.parse(e.data) as { steps: PlanStep[] }
      optionsRef.current.onPlan?.(data)
    })

    es.addEventListener('step_update', (e) => {
      const data = JSON.parse(e.data) as { step_index: number; status: string; result?: string; error?: string }
      optionsRef.current.onStepUpdate?.(data)
    })

    es.addEventListener('message', (e) => {
      const data = JSON.parse(e.data) as { session_id: string; message: Record<string, unknown> }
      optionsRef.current.onMessage?.(data)
    })

    es.addEventListener('done', () => {
      setIsConnected(false)
      cleanupEventSource()
      optionsRef.current.onDone?.()
    })

    es.addEventListener('error', (e: Event) => {
      const event = e as MessageEvent
      try {
        if (event.data) {
          const data = JSON.parse(event.data) as { message: string }
          setError(data.message)
          optionsRef.current.onError?.(data)
        }
      } catch {
        console.error('SSE error event:', event)
      }
    })
  }, [cleanupEventSource])

  const attemptReconnect = useCallback(() => {
    if (!sessionId) return

    const retryCount = reconnectAttemptsRef.current + 1

    if (retryCount > MAX_RECONNECT_ATTEMPTS) {
      setError('Max reconnection attempts reached. Please refresh the page.')
      return
    }

    reconnectAttemptsRef.current = retryCount
    const delay = currentDelayRef.current
    currentDelayRef.current = calculateNextDelay(currentDelayRef.current)

    reconnectTimeoutRef.current = setTimeout(() => {
      const es = chatApi.stream(sessionId)
      eventSourceRef.current = es

      es.onopen = () => {
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        currentDelayRef.current = INITIAL_RETRY_DELAY
      }

      setupEventListeners(es)

      es.onerror = () => {
        cleanupEventSource()
        setIsConnected(false)
        attemptReconnect()
      }
    }, delay)
  }, [sessionId, cleanupEventSource, setupEventListeners])

  useEffect(() => {
    if (!sessionId) {
      setIsConnected(false)
      return
    }

    setError(null)
    cleanupEventSource()

    const es = chatApi.stream(sessionId)
    eventSourceRef.current = es

    es.onopen = () => {
      setIsConnected(true)
      setError(null)
      reconnectAttemptsRef.current = 0
      currentDelayRef.current = INITIAL_RETRY_DELAY
    }

    setupEventListeners(es)

    es.onerror = () => {
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
  }, [sessionId, cleanupEventSource, attemptReconnect, setupEventListeners])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    cleanupEventSource()
    setIsConnected(false)
    reconnectAttemptsRef.current = 0
    currentDelayRef.current = INITIAL_RETRY_DELAY
  }, [cleanupEventSource])

  return {
    isConnected,
    error,
    disconnect,
  }
}
