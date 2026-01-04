import { useEffect, useState, useCallback } from 'react'
import { chatApi } from '../services/api'

interface SSEEvent {
  type: string
  data: Record<string, unknown>
}

interface UseSSEOptions {
  onThought?: (data: { agent: string; content: string }) => void
  onStepUpdate?: (data: { step_id: string; status: string; description: string; logs?: string }) => void
  onMessageChunk?: (data: { content: string }) => void
  onError?: (data: { message: string; retry_count: number }) => void
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
    
    eventSource.addEventListener('message_chunk', (e) => {
      const data = JSON.parse(e.data) as { content: string }
      options.onMessageChunk?.(data)
    })
    
    eventSource.addEventListener('error', (e) => {
      const data = JSON.parse(e.data) as { message: string; retry_count: number }
      setError(data.message)
      options.onError?.(data)
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
