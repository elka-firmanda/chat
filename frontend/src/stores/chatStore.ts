import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  agent_type?: string
  created_at: string
  metadata?: Record<string, unknown> & {
    thinking_content?: string
    thoughts?: Array<{ agent: string; content: string }>
  }
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  archived: boolean
}

export interface AgentStep {
  id: string
  step_number: number
  agent_type?: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  logs?: string
}

interface ChatState {
  sessions: ChatSession[]
  activeSessionId: string | null
  messages: Record<string, Message[]>
  messageTotal: Record<string, number>
  agentSteps: Record<string, AgentStep[]>
  isDeepSearchEnabled: boolean
  isLoading: boolean
  setSessions: (sessions: ChatSession[]) => void
  addSession: (session: ChatSession) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void
  setActiveSession: (sessionId: string | null) => void
  addMessage: (sessionId: string, message: Message) => void
  setMessages: (sessionId: string, messages: Message[]) => void
  prependMessages: (sessionId: string, messages: Message[]) => void
  setMessageTotal: (sessionId: string, total: number) => void
  setAgentSteps: (messageId: string, steps: AgentStep[]) => void
  updateAgentStep: (messageId: string, stepId: string, updates: Partial<AgentStep>) => void
  toggleDeepSearch: () => void
  setLoading: (loading: boolean) => void
  addThought: (sessionId: string, agent: string, content: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessions: [],
      activeSessionId: null,
      messages: {},
      messageTotal: {},
      agentSteps: {},
      isDeepSearchEnabled: false,
      isLoading: false,
      setSessions: (sessions) => set({ sessions }),
      addSession: (session) => set((state) => ({
        sessions: [session, ...state.sessions]
      })),
      updateSession: (sessionId, updates) => set((state) => ({
        sessions: state.sessions.map(s =>
          s.id === sessionId ? { ...s, ...updates } : s
        )
      })),
      setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),
      addMessage: (sessionId, message) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
          messages: {
            ...state.messages,
            [sessionId]: [...sessionMessages, message]
          }
        }
      }),
      setMessages: (sessionId, messages) => set((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: messages
        }
      })),
      prependMessages: (sessionId, messages) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        const existingIds = new Set(sessionMessages.map(m => m.id))
        const newMessages = messages.filter(m => !existingIds.has(m.id))
        return {
          messages: {
            ...state.messages,
            [sessionId]: [...newMessages, ...sessionMessages]
          }
        }
      }),
      setMessageTotal: (sessionId, total) => set((state) => ({
        messageTotal: {
          ...state.messageTotal,
          [sessionId]: total
        }
      })),
      setAgentSteps: (messageId, steps) => set((state) => ({
        agentSteps: {
          ...state.agentSteps,
          [messageId]: steps
        }
      })),
      updateAgentStep: (messageId, stepId, updates) => set((state) => {
        const steps = state.agentSteps[messageId] || []
        return {
          agentSteps: {
            ...state.agentSteps,
            [messageId]: steps.map(s =>
              s.id === stepId ? { ...s, ...updates } : s
            )
          }
        }
      }),
      toggleDeepSearch: () => set((state) => ({
        isDeepSearchEnabled: !state.isDeepSearchEnabled
      })),
      setLoading: (loading) => set({ isLoading: loading }),
      addThought: (sessionId, agent, content) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        if (sessionMessages.length === 0) return state

        const lastMessage = sessionMessages[sessionMessages.length - 1]
        if (lastMessage.role !== 'assistant') return state

        const thoughts = lastMessage.metadata?.thoughts || []
        const newThought = { agent, content }
        const updatedThoughts = [...thoughts, newThought]
        const thinkingContent = updatedThoughts
          .map(t => `[${t.agent}] ${t.content}`)
          .join('\n\n')

        const updatedLastMessage = {
          ...lastMessage,
          metadata: {
            ...lastMessage.metadata,
            thoughts: updatedThoughts,
            thinking_content: thinkingContent
          }
        }

        return {
          messages: {
            ...state.messages,
            [sessionId]: [...sessionMessages.slice(0, -1), updatedLastMessage]
          }
        }
      })
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        isDeepSearchEnabled: state.isDeepSearchEnabled
      })
    }
  )
)
