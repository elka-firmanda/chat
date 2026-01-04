import { useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { chatApi } from '../services/api'

export function useChat() {
  const { 
    activeSessionId,
    addMessage,
    setMessages,
    isLoading,
    setLoading
  } = useChatStore()
  
  const sendMessage = useCallback(async (
    content: string,
    deepSearch = false,
    onStream?: (chunk: string) => void
  ) => {
    if (!content.trim() || isLoading) return
    
    setLoading(true)
    
    try {
      // Send message
      const response = await chatApi.send(content, activeSessionId || undefined, deepSearch)
      const { message_id, session_id } = response.data
      
      // Add user message to store
      addMessage(session_id, {
        id: message_id,
        role: 'user',
        content,
        created_at: new Date().toISOString()
      })
      
      // Set as active session if not already
      if (!activeSessionId) {
        useChatStore.getState().setActiveSession(session_id)
      }
      
      // Handle streaming response
      if (onStream) {
        const eventSource = chatApi.stream(session_id)
        
        eventSource.addEventListener('message_chunk', (e) => {
          const data = JSON.parse(e.data)
          if (data.content) {
            onStream(data.content)
          }
        })
        
        eventSource.addEventListener('complete', () => {
          eventSource.close()
          setLoading(false)
        })
        
        eventSource.onerror = () => {
          eventSource.close()
          setLoading(false)
        }
      } else {
        setLoading(false)
      }
      
      return { message_id, session_id }
    } catch (error) {
      console.error('Failed to send message:', error)
      setLoading(false)
      throw error
    }
  }, [activeSessionId, addMessage, isLoading, setLoading])
  
  const cancelExecution = useCallback(async () => {
    if (!activeSessionId) return
    
    try {
      await chatApi.cancel(activeSessionId)
    } catch (error) {
      console.error('Failed to cancel execution:', error)
    }
  }, [activeSessionId])
  
  const forkConversation = useCallback(async (messageId: string) => {
    try {
      const response = await chatApi.fork(messageId)
      return response.data.new_session_id
    } catch (error) {
      console.error('Failed to fork conversation:', error)
      throw error
    }
  }, [])
  
  return {
    sendMessage,
    cancelExecution,
    forkConversation,
    isLoading
  }
}
