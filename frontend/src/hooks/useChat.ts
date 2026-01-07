import { useCallback } from 'react'
import { useChatStore, type PlanStep } from '../stores/chatStore'
import { chatApi, sessionsApi } from '../services/api'

// SSE event parser for fetch-based streaming
async function parseSSEResponse(
  reader: ReadableStreamDefaultReader,
  handlers: Record<string, (data: unknown) => void>
): Promise<void> {
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event:')) {
        const eventType = line.slice(7).trim()
        // Find the data line that follows
        const dataLineIndex = lines.findIndex((l, i) => 
          i > lines.indexOf(line) && l.startsWith('data:')
        )
        if (dataLineIndex !== -1) {
          const dataStr = lines[dataLineIndex].slice(6).trim()
          try {
            const data = JSON.parse(dataStr)
            handlers[eventType]?.(data)
          } catch {
            handlers[eventType]?.(dataStr)
          }
        }
      }
    }
  }
}

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

      // Use POST-based SSE streaming
      const reader = await chatApi.stream(session_id, content, deepSearch)

      const handlers: Record<string, (data: unknown) => void> = {
        token: (data: unknown) => {
          const d = data as { token?: string }
          if (d.token) {
            appendStreamingContent(d.token)
            appendToLastMessage(session_id, d.token)
          }
        },
        status: (data: unknown) => {
          const d = data as { message?: string }
          setStatusMessage(d.message || null)
        },
        plan: (data: unknown) => {
          const d = data as { steps?: PlanStep[] }
          setPlan(d.steps || [])
        },
        step_update: (data: unknown) => {
          const d = data as { step_index?: number; status?: 'pending' | 'in_progress' | 'completed' | 'failed'; result?: string; error?: string }
          if (typeof d.step_index === 'number') {
            updatePlanStep(d.step_index, {
              status: d.status,
              result: d.result,
              error: d.error
            })
          }
        },
        message: (data: unknown) => {
          const d = data as { message?: { content?: string; metadata?: Record<string, unknown> } }
          if (d.message) {
            updateMessage(session_id, assistantMessageId, {
              content: d.message.content || useChatStore.getState().streamingContent,
              metadata: d.message.metadata
            })
          }
        },
        done: () => {
          setLoading(false)
          setStatusMessage(null)
        },
        error: (data: unknown) => {
          const d = data as { message?: string }
          console.error('SSE error:', d.message)
          setLoading(false)
        }
      }

      // Start parsing SSE events
      if (reader) {
        parseSSEResponse(reader, handlers).catch((err) => {
          console.error('SSE parsing error:', err)
          setLoading(false)
        })
      } else {
        console.error('Failed to get SSE reader')
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

      // Get the original message to extract the content for streaming
      const messages = useChatStore.getState().messages[session_id] || []
      const originalMsg = messages.find((m: { id: string }) => m.id === messageId)
      const messageContent = originalMsg?.content || ''

      // Use POST-based SSE streaming
      const reader = await chatApi.stream(session_id, messageContent, false)

      const handlers: Record<string, (data: unknown) => void> = {
        token: (data: unknown) => {
          const d = data as { token?: string }
          if (d.token) {
            appendStreamingContent(d.token)
          }
        },
        done: () => {
          setLoading(false)
        },
        error: () => {
          setLoading(false)
        }
      }

      if (reader) {
        parseSSEResponse(reader, handlers).catch((err) => {
          console.error('SSE parsing error:', err)
          setLoading(false)
        })
      } else {
        console.error('Failed to get SSE reader for regenerate')
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
