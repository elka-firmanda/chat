import { useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { chatApi, sessionsApi } from '../services/api'

export function useChat() {
  const {
    activeSessionId,
    addMessage,
    updateMessage,
    setMessages,
    prependMessages,
    setMessageTotal,
    setPlan,
    updatePlanStep,
    clearPlan,
    setStatusMessage,
    appendStreamingContent,
    setStreamingContent,
    appendToLastMessage,
    isLoading,
    setLoading
  } = useChatStore()

  const sendMessage = useCallback(async (
    content: string,
    deepSearch = false
  ) => {
    if (!content.trim() || isLoading) return

    setLoading(true)
    clearPlan()
    setStreamingContent('')

    try {
      const response = await chatApi.send(content, activeSessionId || undefined, deepSearch)
      const { session_id } = response.data

      if (!activeSessionId) {
        useChatStore.getState().setActiveSession(session_id)
      }

      const userMessageId = `user-${Date.now()}`
      addMessage(session_id, {
        id: userMessageId,
        role: 'user',
        content,
        created_at: new Date().toISOString()
      })

      const assistantMessageId = `assistant-${Date.now()}`
      addMessage(session_id, {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        agent_type: 'master',
        created_at: new Date().toISOString()
      })

      const eventSource = chatApi.stream(session_id)

      eventSource.addEventListener('token', (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.token) {
            appendStreamingContent(data.token)
            appendToLastMessage(session_id, data.token)
          }
        } catch (err) {
          console.error('Failed to parse token event:', err)
        }
      })

      eventSource.addEventListener('status', (e) => {
        try {
          const data = JSON.parse(e.data)
          setStatusMessage(data.message)
        } catch (err) {
          console.error('Failed to parse status event:', err)
        }
      })

      eventSource.addEventListener('plan', (e) => {
        try {
          const data = JSON.parse(e.data)
          setPlan(data.steps)
        } catch (err) {
          console.error('Failed to parse plan event:', err)
        }
      })

      eventSource.addEventListener('step_update', (e) => {
        try {
          const data = JSON.parse(e.data)
          updatePlanStep(data.step_index, {
            status: data.status,
            result: data.result,
            error: data.error
          })
        } catch (err) {
          console.error('Failed to parse step_update event:', err)
        }
      })

      eventSource.addEventListener('message', (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.message) {
            updateMessage(session_id, assistantMessageId, {
              content: data.message.content || useChatStore.getState().streamingContent,
              metadata: data.message.metadata
            })
          }
        } catch (err) {
          console.error('Failed to parse message event:', err)
        }
      })

      eventSource.addEventListener('done', () => {
        eventSource.close()
        setLoading(false)
        setStatusMessage(null)
      })

      eventSource.addEventListener('error', (e: Event) => {
        const event = e as MessageEvent
        try {
          if (event.data) {
            const data = JSON.parse(event.data)
            console.error('SSE error:', data.message)
          }
        } catch {
          console.error('SSE connection error')
        }
        eventSource.close()
        setLoading(false)
      })

      eventSource.onerror = () => {
        eventSource.close()
        setLoading(false)
      }

      return { session_id }
    } catch (error) {
      console.error('Failed to send message:', error)
      setLoading(false)
      throw error
    }
  }, [
    activeSessionId, 
    addMessage, 
    updateMessage,
    isLoading, 
    setLoading, 
    clearPlan,
    setPlan,
    updatePlanStep,
    setStatusMessage,
    setStreamingContent,
    appendStreamingContent,
    appendToLastMessage
  ])

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

  const regenerateMessage = useCallback(async (messageId: string) => {
    if (!activeSessionId || isLoading) return

    setLoading(true)
    clearPlan()
    setStreamingContent('')

    try {
      const response = await chatApi.regenerate(messageId)
      const { session_id } = response.data

      const eventSource = chatApi.stream(session_id)

      eventSource.addEventListener('token', (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.token) {
            appendStreamingContent(data.token)
          }
        } catch (err) {
          console.error('Failed to parse token event:', err)
        }
      })

      eventSource.addEventListener('done', () => {
        eventSource.close()
        setLoading(false)
      })

      eventSource.onerror = () => {
        eventSource.close()
        setLoading(false)
      }

      return { session_id }
    } catch (error) {
      console.error('Failed to regenerate message:', error)
      setLoading(false)
      throw error
    }
  }, [activeSessionId, isLoading, setLoading, clearPlan, setStreamingContent, appendStreamingContent])

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
