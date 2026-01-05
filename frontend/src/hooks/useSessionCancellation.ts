import { useCallback, useEffect, useRef } from 'react'
import { chatApi } from '../services/api'

export function useSessionCancellation(activeSessionId: string | null) {
  const previousSessionIdRef = useRef<string | null>(null)
  const isUnloadingRef = useRef(false)

  useEffect(() => {
    const handleBeforeUnload = () => {
      isUnloadingRef.current = true
      if (activeSessionId) {
        const cancelEndpoint = `/api/v1/chat/cancel/${activeSessionId}`
        navigator.sendBeacon(cancelEndpoint)
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [activeSessionId])

  const cancelPreviousSession = useCallback(async () => {
    if (previousSessionIdRef.current && previousSessionIdRef.current !== activeSessionId) {
      try {
        await chatApi.cancel(previousSessionIdRef.current)
        console.log(`Cancelled previous session: ${previousSessionIdRef.current}`)
      } catch (error) {
        console.error(`Failed to cancel previous session: ${previousSessionIdRef.current}`, error)
      }
    }
    previousSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  useEffect(() => {
    cancelPreviousSession()
  }, [activeSessionId, cancelPreviousSession])

  const cancelCurrentSession = useCallback(async () => {
    if (activeSessionId) {
      try {
        await chatApi.cancel(activeSessionId)
      } catch (error) {
        console.error(`Failed to cancel session: ${activeSessionId}`, error)
      }
    }
  }, [activeSessionId])

  return {
    cancelCurrentSession,
    cancelPreviousSession,
    isUnloading: isUnloadingRef.current,
  }
}
