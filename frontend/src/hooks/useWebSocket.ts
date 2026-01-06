import { useEffect, useState, useCallback, useRef } from 'react'

const WS_RECONNECT_DELAY = 3000
const WS_MAX_RECONNECT_ATTEMPTS = 5
const WS_HEARTBEAT_INTERVAL = 30000

export interface WebSocketMessage {
  type: string
  payload: Record<string, unknown>
  timestamp: string
}

export interface UseWebSocketOptions {
  onOpen?: () => void
  onClose?: () => void
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onReconnectAttempt?: (attempt: number) => void
  onReconnectSuccess?: (attempt: number) => void
  enabled?: boolean
}

export interface UseWebSocketReturn {
  isConnected: boolean
  error: string | null
  sendMessage: (type: string, payload: Record<string, unknown>) => void
  reconnect: () => void
  disconnect: () => void
  reconnectAttempts: number
  maxReconnectAttempts: number
}

export function useWebSocket(
  sessionId: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    onOpen,
    onClose,
    onMessage,
    onError,
    onReconnectAttempt,
    onReconnectSuccess,
    enabled = true
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const maxReconnectAttempts = WS_MAX_RECONNECT_ATTEMPTS

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((type: string, payload: Record<string, unknown>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        payload,
        timestamp: new Date().toISOString()
      }
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected, cannot send message')
    }
  }, [])

  const connect = useCallback(() => {
    if (!enabled || !sessionId) return

    // Don't connect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return
    }

    // Clean up any existing connection
    cleanup()

    try {
      // Determine WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/api/v1/ws/${sessionId}`

      console.log('[WebSocket] Connecting to:', wsUrl)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WebSocket] Connected')
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        setReconnectAttempts(0)
        onOpen?.()

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', payload: {}, timestamp: new Date().toISOString() }))
          }
        }, WS_HEARTBEAT_INTERVAL)
      }

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected')
        setIsConnected(false)
        onClose?.()

        // Attempt to reconnect if not intentionally disconnected
        if (enabled && sessionId && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const attempt = reconnectAttemptsRef.current + 1
          reconnectAttemptsRef.current = attempt
          setReconnectAttempts(attempt)
          onReconnectAttempt?.(attempt)

          console.log(`[WebSocket] Reconnecting in ${WS_RECONNECT_DELAY}ms (attempt ${attempt}/${maxReconnectAttempts})`)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
            onReconnectSuccess?.(attempt)
          }, WS_RECONNECT_DELAY)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached')
        }
      }

      ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err)
        setError('WebSocket connection error')
        onError?.(err)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          // Handle ping-pong
          if (message.type === 'pong') {
            return
          }

          console.log('[WebSocket] Received:', message.type)
          onMessage?.(message)
        } catch (parseError) {
          console.error('[WebSocket] Failed to parse message:', parseError)
        }
      }
    } catch (err) {
      console.error('[WebSocket] Failed to create connection:', err)
      setError('Failed to create WebSocket connection')
    }
  }, [sessionId, enabled, cleanup, onOpen, onClose, onMessage, onError, onReconnectAttempt, onReconnectSuccess, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    console.log('[WebSocket] Intentional disconnect')
    cleanup()
  }, [cleanup])

  const reconnect = useCallback(() => {
    console.log('[WebSocket] Manual reconnect')
    reconnectAttemptsRef.current = 0
    setReconnectAttempts(0)
    cleanup()
    connect()
  }, [cleanup, connect])

  useEffect(() => {
    if (enabled && sessionId) {
      connect()
    } else {
      cleanup()
    }

    return () => {
      cleanup()
    }
  }, [sessionId, enabled, connect, cleanup])

  return {
    isConnected,
    error,
    sendMessage,
    reconnect,
    disconnect,
    reconnectAttempts,
    maxReconnectAttempts
  }
}

// Intervention-specific WebSocket hook
export interface InterventionAction {
  type: 'retry' | 'skip' | 'abort'
  sessionId: string
  reason?: string
}

export interface InterventionState {
  awaitingResponse: boolean
  pendingError: Record<string, unknown> | null
  availableActions: string[]
}

export function useInterventionWebSocket(
  sessionId: string | null,
  options: {
    onIntervention?: (data: InterventionState) => void
    onActionConfirmation?: (action: string, success: boolean) => void
    enabled?: boolean
  } = {}
) {
  const { onIntervention, onActionConfirmation, enabled = true } = options

  const wsOptions: UseWebSocketOptions = {
    enabled: enabled && !!sessionId,
    onMessage: useCallback((message: WebSocketMessage) => {
      switch (message.type) {
        case 'intervention_state':
          onIntervention?.(message.payload as unknown as InterventionState)
          break
        case 'action_confirmation':
          const { action, success } = message.payload as { action: string; success: boolean }
          onActionConfirmation?.(action, success)
          break
        default:
          console.log('[InterventionWS] Unknown message type:', message.type)
      }
    }, [onIntervention, onActionConfirmation])
  }

  const ws = useWebSocket(sessionId, wsOptions)

  const sendInterventionAction = useCallback((action: InterventionAction['type'], reason?: string) => {
    ws.sendMessage('intervention_action', {
      action,
      sessionId,
      reason
    })
    console.log('[InterventionWS] Sent action:', action)
  }, [ws, sessionId])

  return {
    ...ws,
    sendInterventionAction
  }
}

// Session sync WebSocket hook for multi-tab support
export interface SessionSyncEvent {
  type: 'session_created' | 'session_deleted' | 'session_updated' | 'message_added'
  sessionId: string
  data?: Record<string, unknown>
}

export function useSessionSyncWebSocket(
  options: {
    onSessionEvent?: (event: SessionSyncEvent) => void
    enabled?: boolean
  } = {}
) {
  const { onSessionEvent, enabled = true } = options

  const wsOptions: UseWebSocketOptions = {
    enabled,
    onMessage: useCallback((message: WebSocketMessage) => {
      if (message.type.startsWith('session_')) {
        onSessionEvent?.(message.payload as unknown as SessionSyncEvent)
      }
    }, [onSessionEvent])
  }

  // Use null sessionId for global session events
  const ws = useWebSocket(null, wsOptions)

  return ws
}
