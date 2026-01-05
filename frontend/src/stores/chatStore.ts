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
  sessions: ChatSession[]
  activeSessionId: string | null
  messages: Record<string, Message[]>
  messageTotal: Record<string, number>
  agentSteps: Record<string, AgentStep[]>
  workingMemory: Record<string, WorkingMemory>
  activeNodeId: string | null
  isDeepSearchEnabled: boolean
  isLoading: boolean
  setSessions: (sessions: ChatSession[]) => void
  addSession: (session: ChatSession) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void
  setActiveSession: (sessionId: string | null) => void
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
      sessions: [],
      activeSessionId: null,
      messages: {},
      messageTotal: {},
      agentSteps: {},
      workingMemory: {},
      activeNodeId: null,
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
