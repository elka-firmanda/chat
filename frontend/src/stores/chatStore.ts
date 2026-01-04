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
  // Sessions
  sessions: ChatSession[]
  activeSessionId: string | null
  
  // Messages
  messages: Record<string, Message[]>  // session_id -> messages
  
  // Agent steps (progress)
  agentSteps: Record<string, AgentStep[]>  // message_id -> steps
  
  // UI state
  isDeepSearchEnabled: boolean
  isLoading: boolean
  
  // Actions
  setSessions: (sessions: ChatSession[]) => void
  addSession: (session: ChatSession) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void
  setActiveSession: (sessionId: string | null) => void
  
  addMessage: (sessionId: string, message: Message) => void
  setMessages: (sessionId: string, messages: Message[]) => void
  
  setAgentSteps: (messageId: string, steps: AgentStep[]) => void
  updateAgentStep: (messageId: string, stepId: string, updates: Partial<AgentStep>) => void
  
  toggleDeepSearch: () => void
  setLoading: (loading: boolean) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      // Initial state
      sessions: [],
      activeSessionId: null,
      messages: {},
      agentSteps: {},
      isDeepSearchEnabled: false,
      isLoading: false,
      
      // Session actions
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
      
      // Message actions
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
      
      // Agent step actions
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
      
      // UI actions
      toggleDeepSearch: () => set((state) => ({
        isDeepSearchEnabled: !state.isDeepSearchEnabled
      })),
      
      setLoading: (loading) => set({ isLoading: loading })
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
