import { useCallback, useEffect, useState } from 'react'
import { sessionsApi, SearchResponse } from '../services/api'
import { useChatStore } from '../stores/chatStore'

export function useSessions() {
  const { 
    sessions, 
    setSessions, 
    addSession, 
    setActiveSession,
    activeSessionId,
    updateSession
  } = useChatStore()
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
  
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
  
  const archiveSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.archive(sessionId)
      updateSession(sessionId, { archived: true })
    } catch (err) {
      setError('Failed to archive session')
      console.error(err)
      throw err
    }
  }, [updateSession])
  
  const unarchiveSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.unarchive(sessionId)
      updateSession(sessionId, { archived: false })
    } catch (err) {
      setError('Failed to unarchive session')
      console.error(err)
      throw err
    }
  }, [updateSession])
  
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.delete(sessionId)
      updateSession(sessionId, { archived: true })
    } catch (err) {
      setError('Failed to delete session')
      console.error(err)
      throw err
    }
  }, [updateSession])
  
  const searchSessions = useCallback(async (
    query: string, 
    limit = 20, 
    type: 'all' | 'sessions' | 'messages' = 'all'
  ): Promise<SearchResponse | null> => {
    if (!query || query.trim().length < 2) {
      setSearchResults(null)
      return null
    }
    
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await sessionsApi.search(query.trim(), limit, type)
      setSearchResults(response.data)
      return response.data
    } catch (err) {
      setError('Search failed')
      console.error(err)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])
  
  const clearSearch = useCallback(() => {
    setSearchResults(null)
  }, [])
  
  useEffect(() => {
    loadSessions()
  }, [loadSessions])
  
  return {
    sessions,
    activeSessionId,
    isLoading,
    error,
    searchResults,
    loadSessions,
    createSession,
    loadSession,
    archiveSession,
    unarchiveSession,
    deleteSession,
    searchSessions,
    clearSearch
  }
}
