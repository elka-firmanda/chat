import { useCallback, useEffect, useState } from 'react'
import { sessionsApi, SearchResponse } from '../services/api'
import { useChatStore } from '../stores/chatStore'

export function useSessions() {
  const { 
    sessions, 
    archivedSessions,
    setSessions,
    setArchivedSessions,
    addSession, 
    setActiveSession,
    activeSessionId,
    removeSession
  } = useChatStore()
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
  
  const loadSessions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await sessionsApi.list(false)
      setSessions(response.data.sessions)
    } catch (err) {
      setError('Failed to load sessions')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [setSessions])

  const loadArchivedSessions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await sessionsApi.list(true)
      setArchivedSessions(response.data.sessions)
    } catch (err) {
      setError('Failed to load archived sessions')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [setArchivedSessions])
  
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
      
      setActiveSession(sessionId)
      useChatStore.getState().setMessages(sessionId, response.data.messages)
      
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
      // Move session from sessions to archivedSessions
      const session = sessions.find(s => s.id === sessionId)
      if (session) {
        removeSession(sessionId)
        setArchivedSessions([...archivedSessions, { ...session, archived: true }])
      }
      await loadSessions()
      await loadArchivedSessions()
    } catch (err) {
      setError('Failed to archive session')
      console.error(err)
      throw err
    }
  }, [sessions, archivedSessions, removeSession, setArchivedSessions, loadSessions, loadArchivedSessions])
  
  const unarchiveSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.unarchive(sessionId)
      // Move session from archivedSessions to sessions
      const session = archivedSessions.find(s => s.id === sessionId)
      if (session) {
        removeSession(sessionId)
        setSessions([{ ...session, archived: false }, ...sessions])
      }
      await loadSessions()
      await loadArchivedSessions()
    } catch (err) {
      setError('Failed to unarchive session')
      console.error(err)
      throw err
    }
  }, [sessions, archivedSessions, removeSession, setSessions, loadSessions, loadArchivedSessions])
  
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsApi.delete(sessionId)
      removeSession(sessionId)
    } catch (err) {
      setError('Failed to delete session')
      console.error(err)
      throw err
    }
  }, [removeSession])
  
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
    archivedSessions,
    activeSessionId,
    isLoading,
    error,
    searchResults,
    loadSessions,
    loadArchivedSessions,
    createSession,
    loadSession,
    archiveSession,
    unarchiveSession,
    deleteSession,
    searchSessions,
    clearSearch
  }
}
