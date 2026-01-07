import { useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { chatApi, sessionsApi } from '../services/api'

export function useChat() {
  const {
    activeSessionId,
    addMessage,
    addThought,
    setMessages,
    prependMessages,
    setMessageTotal,
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
      const response = await chatApi.send(content, activeSessionId || undefined, deepSearch)
      const { message_id: assistantMessageId, session_id, created_at } = response.data

      // Set active session FIRST so UI is ready to display messages
      if (!activeSessionId) {
        useChatStore.getState().setActiveSession(session_id)
      }

      // Add user message with generated ID
      const userMessageId = `user-${Date.now()}`
      addMessage(session_id, {
        id: userMessageId,
        role: 'user',
        content,
        created_at: new Date().toISOString()
      })

      // Add assistant message with ID from backend (will be updated by SSE)
      addMessage(session_id, {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        agent_type: 'master',
        created_at: created_at || new Date().toISOString()
      })

      if (onStream) {
        const eventSource = chatApi.stream(session_id)

        eventSource.addEventListener('thought', (e) => {
          try {
            const data = JSON.parse(e.data)
            addThought(session_id, data.agent, data.content)
          } catch (err) {
            console.error('Failed to parse thought event:', err)
          }
        })

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
  }, [activeSessionId, addMessage, addThought, isLoading, setLoading])

  const regenerateMessage = useCallback(async (messageId: string, onStream?: (chunk: string) => void) => {
    if (!activeSessionId || isLoading) return

    setLoading(true)

    try {
      const response = await chatApi.regenerate(messageId)
      const { message_id, session_id } = response.data

      if (onStream) {
        const eventSource = chatApi.stream(session_id)

        eventSource.addEventListener('thought', (e) => {
          try {
            const data = JSON.parse(e.data)
            addThought(session_id, data.agent, data.content)
          } catch (err) {
            console.error('Failed to parse thought event:', err)
          }
        })

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
      console.error('Failed to regenerate message:', error)
      setLoading(false)
      throw error
    }
  }, [activeSessionId, isLoading, setLoading, addThought])

  const loadMessages = useCallback(async (sessionId: string, limit = 30, offset = 0) => {
    try {
      const response = await sessionsApi.get(sessionId, limit, offset)
      const { messages, total, has_more } = response.data

      if (offset === 0) {
        setMessages(sessionId, messages)
      } else {
        prependMessages(sessionId, messages)
      }
      setMessageTotal(sessionId, total)

      return { messages, total, has_more }
    } catch (error) {
      console.error('Failed to load messages:', error)
      throw error
    }
  }, [setMessages, prependMessages, setMessageTotal])

  const loadMoreMessages = useCallback(async () => {
    if (!activeSessionId || isLoading) return null

    const currentMessages = useChatStore.getState().messages[activeSessionId] || []
    const total = useChatStore.getState().messageTotal[activeSessionId] || 0

    if (currentMessages.length >= total) {
      return null
    }

    setLoading(true)
    try {
      const response = await sessionsApi.get(activeSessionId, 30, currentMessages.length)
      const { messages, has_more } = response.data

      prependMessages(activeSessionId, messages)

      return { messages, has_more }
    } catch (error) {
      console.error('Failed to load more messages:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }, [activeSessionId, isLoading, prependMessages, setLoading])

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
    regenerateMessage,
    loadMessages,
    loadMoreMessages,
    cancelExecution,
    forkConversation,
    isLoading
  }
}
