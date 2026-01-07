import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { sessionsApi, authApi } from '../services/api'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  agent_type?: string
  created_at: string
  metadata?: Record<string, unknown> & {
    deep_search?: boolean
    plan?: PlanStep[]
  }
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  archived: boolean
}

export interface PlanStep {
  step_number: number
  description: string
  agent?: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  result?: string
  error?: string
}

interface ChatState {
  chatAuthRequired: boolean | null
  isChatAuthenticated: boolean
  
  sessions: ChatSession[]
  archivedSessions: ChatSession[]
  activeSessionId: string | null
  sidebarOpen: boolean
  messages: Record<string, Message[]>
  messageTotal: Record<string, number>
  
  currentPlan: PlanStep[]
  statusMessage: string | null
  streamingContent: string
  
  isDeepSearchEnabled: boolean
  isLoading: boolean
  
  checkChatAuth: () => Promise<void>
  chatLogin: (password: string) => Promise<boolean>
  
  setSessions: (sessions: ChatSession[]) => void
  setArchivedSessions: (sessions: ChatSession[]) => void
  addSession: (session: ChatSession) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void
  removeSession: (sessionId: string) => void
  setActiveSession: (sessionId: string | null) => void
  deleteSession: (sessionId: string) => Promise<void>
  renameSession: (sessionId: string, title: string) => Promise<void>
  archiveSession: (sessionId: string) => Promise<void>
  unarchiveSession: (sessionId: string) => Promise<void>
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  
  addMessage: (sessionId: string, message: Message) => void
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void
  setMessages: (sessionId: string, messages: Message[]) => void
  prependMessages: (sessionId: string, messages: Message[]) => void
  setMessageTotal: (sessionId: string, total: number) => void
  appendToLastMessage: (sessionId: string, content: string) => void
  
  setPlan: (steps: PlanStep[]) => void
  updatePlanStep: (stepIndex: number, updates: Partial<PlanStep>) => void
  clearPlan: () => void
  setStatusMessage: (message: string | null) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (token: string) => void
  
  toggleDeepSearch: () => void
  setLoading: (loading: boolean) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      chatAuthRequired: false,
      isChatAuthenticated: true,
      
      sessions: [],
      archivedSessions: [],
      activeSessionId: null,
      sidebarOpen: true,
      messages: {},
      messageTotal: {},
      
      currentPlan: [],
      statusMessage: null,
      streamingContent: '',
      
      isDeepSearchEnabled: false,
      isLoading: false,

      setSessions: (sessions) => set({ sessions }),
      setArchivedSessions: (sessions) => set({ archivedSessions: sessions }),
      
      addSession: (session) => set((state) => ({
        sessions: [session, ...state.sessions]
      })),
      
      updateSession: (sessionId, updates) => set((state) => ({
        sessions: state.sessions.map(s =>
          s.id === sessionId ? { ...s, ...updates } : s
        ),
        archivedSessions: state.archivedSessions.map(s =>
          s.id === sessionId ? { ...s, ...updates } : s
        )
      })),
      
      removeSession: (sessionId) => set((state) => ({
        sessions: state.sessions.filter(s => s.id !== sessionId),
        archivedSessions: state.archivedSessions.filter(s => s.id !== sessionId)
      })),
      
      setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),
      
      deleteSession: async (sessionId) => {
        await sessionsApi.delete(sessionId)
        set((state) => ({
          sessions: state.sessions.filter(s => s.id !== sessionId),
          archivedSessions: state.archivedSessions.filter(s => s.id !== sessionId),
          activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId
        }))
      },
      
      renameSession: async (sessionId, title) => {
        await sessionsApi.update(sessionId, { title })
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === sessionId ? { ...s, title } : s
          ),
          archivedSessions: state.archivedSessions.map(s =>
            s.id === sessionId ? { ...s, title } : s
          )
        }))
      },
      
      archiveSession: async (sessionId) => {
        await sessionsApi.archive(sessionId)
        set((state) => {
          const session = state.sessions.find(s => s.id === sessionId)
          if (!session) return state
          return {
            sessions: state.sessions.filter(s => s.id !== sessionId),
            archivedSessions: [...state.archivedSessions, { ...session, archived: true }]
          }
        })
      },
      
      unarchiveSession: async (sessionId) => {
        await sessionsApi.unarchive(sessionId)
        set((state) => {
          const session = state.archivedSessions.find(s => s.id === sessionId)
          if (!session) return state
          return {
            archivedSessions: state.archivedSessions.filter(s => s.id !== sessionId),
            sessions: [{ ...session, archived: false }, ...state.sessions]
          }
        })
      },
      
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      addMessage: (sessionId, message) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
          messages: {
            ...state.messages,
            [sessionId]: [...sessionMessages, message]
          }
        }
      }),
      
      updateMessage: (sessionId, messageId, updates) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
          messages: {
            ...state.messages,
            [sessionId]: sessionMessages.map(m =>
              m.id === messageId ? { ...m, ...updates } : m
            )
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
      
      appendToLastMessage: (sessionId, content) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        if (sessionMessages.length === 0) return state
        
        const lastMessage = sessionMessages[sessionMessages.length - 1]
        if (lastMessage.role !== 'assistant') return state
        
        return {
          messages: {
            ...state.messages,
            [sessionId]: [
              ...sessionMessages.slice(0, -1),
              { ...lastMessage, content: lastMessage.content + content }
            ]
          }
        }
      }),
      
      setPlan: (steps) => set({ 
        currentPlan: steps.map((s, i) => ({ 
          ...s, 
          step_number: s.step_number || i + 1,
          status: s.status || 'pending' 
        })) 
      }),
      
      updatePlanStep: (stepIndex, updates) => set((state) => ({
        currentPlan: state.currentPlan.map((step, i) =>
          i === stepIndex ? { ...step, ...updates } : step
        )
      })),
      
      clearPlan: () => set({ currentPlan: [], statusMessage: null, streamingContent: '' }),
      
      setStatusMessage: (message) => set({ statusMessage: message }),
      
      setStreamingContent: (content) => set({ streamingContent: content }),
      
      appendStreamingContent: (token) => set((state) => ({
        streamingContent: state.streamingContent + token
      })),
      
      toggleDeepSearch: () => set((state) => ({
        isDeepSearchEnabled: !state.isDeepSearchEnabled
      })),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      checkChatAuth: async () => {
        try {
          const { data } = await authApi.status()
          set({ 
            chatAuthRequired: data.auth_required, 
            isChatAuthenticated: !data.auth_required 
          })
        } catch {
          set({ chatAuthRequired: false, isChatAuthenticated: true })
        }
      },
      
      chatLogin: async (password: string) => {
        try {
          const { data } = await authApi.login(password)
          const authenticated = data.authenticated
          set({ isChatAuthenticated: authenticated })
          return authenticated
        } catch {
          return false
        }
      }
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        archivedSessions: state.archivedSessions,
        activeSessionId: state.activeSessionId,
        sidebarOpen: state.sidebarOpen,
        isDeepSearchEnabled: state.isDeepSearchEnabled
      })
    }
  )
)
