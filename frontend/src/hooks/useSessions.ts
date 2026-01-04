import { useCallback, useEffect, useState } from 'react'
import { sessionsApi } from '../services/api'
import { useChatStore } from '../stores/chatStore'

export function useSessions() {
  const { 
    sessions, 
    setSessions, 
    addSession, 
    setActiveSession,
    activeSessionId 
  } = useChatStore()
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const loadSessions = useCallback(async (includeArchived = false) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await sessionsApi.list(includeArchived)
      setSessions(response.data.sessions)
    } catch (err) {
      setError('Failed to load sessions')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [setSessions])
  
  const createSession = useCallback(async (title?: string) => {
    try {
      const response = await sessionsApi.create(title)
      addSession(response.data)
      setActiveSession(response.data.id)
      return response.data.id
    } catch (err) {
      setError('Failed to create session')
      console.error(err)
      throw err
    }
  }, [addSession, setActiveSession])
  
  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await sessionsApi.get(sessionId)
      const { messages, ...sessionData } = response.data
      
      setActiveSession(sessionId)
      useChatStore.getState().setMessages(sessionId, messages)
      
      return response.data
    } catch (err) {
      setError('Failed to load session')
      console.error(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [setActiveSession])
  
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.delete(sessionId)
      useChatStore.getState().updateSession(sessionId, { archived: true })
    } catch (err) {
      setError('Failed to delete session')
      console.error(err)
      throw err
    }
  }, [])
  
  useEffect(() => {
    loadSessions()
  }, [loadSessions])
  
  return {
    sessions,
    activeSessionId,
    isLoading,
    error,
    loadSessions,
    createSession,
    loadSession,
    deleteSession
  }
}
