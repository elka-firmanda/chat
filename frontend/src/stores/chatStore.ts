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

export interface TimelineEntry {
  node_id: string
  agent: string
  node_type: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  timestamp: string
  parent_id?: string
}

export interface WorkingMemoryNode {
  id: string
  agent: string
  node_type: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  parent_id?: string
  content?: Record<string, unknown>
  children?: WorkingMemoryNode[]
  timestamp: string
}

export interface WorkingMemory {
  memory_tree: WorkingMemoryNode | null
  timeline: TimelineEntry[]
  index: Record<string, WorkingMemoryNode>
  stats: {
    total_nodes: number
    timeline_length: number
  }
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
  // Auth state
  chatAuthRequired: boolean | null
  isChatAuthenticated: boolean
  
  sessions: ChatSession[]
  archivedSessions: ChatSession[]
  activeSessionId: string | null
  sidebarOpen: boolean
  messages: Record<string, Message[]>
  messageTotal: Record<string, number>
  agentSteps: Record<string, AgentStep[]>
  workingMemory: Record<string, WorkingMemory>
  activeNodeId: string | null
  isDeepSearchEnabled: boolean
  isLoading: boolean
  
  // Auth methods
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
  setAgentSteps: (messageId: string, steps: AgentStep[]) => void
  updateAgentStep: (messageId: string, stepId: string, updates: Partial<AgentStep>) => void
  setWorkingMemory: (sessionId: string, memory: WorkingMemory) => void
  updateNode: (sessionId: string, nodeId: string, updates: Partial<WorkingMemoryNode>) => void
  addTimelineEntry: (sessionId: string, entry: TimelineEntry) => void
  setActiveNode: (sessionId: string | null, nodeId: string | null) => void
  toggleDeepSearch: () => void
  setLoading: (loading: boolean) => void
  addThought: (sessionId: string, agent: string, content: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      // Auth state - default to not required (auth not yet implemented)
      chatAuthRequired: false,
      isChatAuthenticated: true,
      
      sessions: [],
      archivedSessions: [],
      activeSessionId: null,
      sidebarOpen: true,
      messages: {},
      messageTotal: {},
      agentSteps: {},
      workingMemory: {},
      activeNodeId: null,
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
      setWorkingMemory: (sessionId, memory) => set((state) => ({
        workingMemory: {
          ...state.workingMemory,
          [sessionId]: memory
        }
      })),
      updateNode: (sessionId, nodeId, updates) => set((state) => {
        const currentMemory = state.workingMemory[sessionId]
        if (!currentMemory) return state

        const updateNodeInTree = (node: WorkingMemoryNode): WorkingMemoryNode => {
          if (node.id === nodeId) {
            return { ...node, ...updates }
          }
          if (node.children) {
            return { ...node, children: node.children.map(updateNodeInTree) }
          }
          return node
        }

        return {
          workingMemory: {
            ...state.workingMemory,
            [sessionId]: {
              ...currentMemory,
              memory_tree: currentMemory.memory_tree ? updateNodeInTree(currentMemory.memory_tree) : null,
              index: {
                ...currentMemory.index,
                [nodeId]: { ...currentMemory.index[nodeId], ...updates }
              }
            }
          }
        }
      }),
      addTimelineEntry: (sessionId, entry) => set((state) => {
        const currentMemory = state.workingMemory[sessionId]
        if (!currentMemory) return state

        return {
          workingMemory: {
            ...state.workingMemory,
            [sessionId]: {
              ...currentMemory,
              timeline: [...currentMemory.timeline, entry],
              stats: {
                ...currentMemory.stats,
                timeline_length: currentMemory.timeline.length + 1
              }
            }
          }
        }
      }),
      setActiveNode: (sessionId, nodeId) => set((_state) => {
        if (sessionId === null) {
          return { activeNodeId: null }
        }
        return {
          activeNodeId: nodeId
        }
      }),
      toggleDeepSearch: () => set((state) => ({
        isDeepSearchEnabled: !state.isDeepSearchEnabled
      })),
      setLoading: (loading) => set({ isLoading: loading }),
      addThought: (sessionId, agent, content) => set((state) => {
        const sessionMessages = state.messages[sessionId] || []
        const lastMessage = sessionMessages[sessionMessages.length - 1]
        
        if (lastMessage && lastMessage.role === 'assistant') {
          const updatedLastMessage = {
            ...lastMessage,
            metadata: {
              ...lastMessage.metadata,
              thoughts: [
                ...(lastMessage.metadata?.thoughts || []),
                { agent, content }
              ]
            }
          }
          return {
            messages: {
              ...state.messages,
              [sessionId]: [...sessionMessages.slice(0, -1), updatedLastMessage]
            }
          }
        }
        return state
      }),
      
      // Auth methods
      checkChatAuth: async () => {
        try {
          const { data } = await authApi.status()
          set({ 
            chatAuthRequired: data.auth_required, 
            isChatAuthenticated: !data.auth_required 
          })
        } catch {
          // If endpoint doesn't exist or fails, assume auth not required
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
