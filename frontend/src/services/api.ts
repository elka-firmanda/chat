import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

export interface ChatMessage {
  content: string
  deep_search?: boolean
}

export interface MessageResponse {
  message_id: string
  session_id: string
  created_at: string
}

export interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
  archived: boolean
}

export interface SessionDetail extends Session {
  messages: Message[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  agent_type?: string
  created_at: string
  metadata?: Record<string, unknown>
}

const api = axios.create({
  baseURL: `${API_URL}/v1`,
  headers: {
    'Content-Type': 'application/json'
  }
})

export interface SearchResult {
  session_id: string
  session_title: string
  message_content: string | null
  created_at: string | null
  highlighted_content: string | null
  message_id?: string
  role?: string
  agent_type?: string
  type: 'session' | 'message'
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
  time_ms: number
  search_type: string
  message?: string
}

export interface SessionExportResponse {
  filename: string
  data: Blob
}

// Session APIs
export const sessionsApi = {
  list: (archived = false, limit = 50, offset = 0) =>
    api.get<{ sessions: Session[] }>('/sessions', { params: { archived, limit, offset } }),
  
  get: (sessionId: string, limit = 30, offset = 0) =>
    api.get<SessionDetail>(`/sessions/${sessionId}`, { params: { limit, offset } }),
  
  create: (title?: string) =>
    api.post<Session>('/sessions', { title }),
  
  update: (sessionId: string, title?: string) =>
    api.patch<Session>(`/sessions/${sessionId}`, { title }),
  
  delete: (sessionId: string) =>
    api.delete(`/sessions/${sessionId}`),
  
  search: (query: string, limit = 20, type: 'all' | 'sessions' | 'messages' = 'all') =>
    api.get<SearchResponse>('/sessions/search', { params: { q: query, limit, type } }),

  export: (sessionId: string) =>
    api.get(`/sessions/${sessionId}/export`, {
      responseType: 'blob'
    })
}

// Chat APIs
export const chatApi = {
  send: (content: string, sessionId?: string, deepSearch = false) =>
    api.post<MessageResponse>('/chat/message', { content, deep_search: deepSearch }, {
      params: { session_id: sessionId }
    }),
  
  stream: (sessionId: string) => {
    const eventSource = new EventSource(`${API_URL}/v1/chat/stream/${sessionId}`)
    return eventSource
  },
  
  cancel: (sessionId: string) =>
    api.post(`/chat/cancel/${sessionId}`),
  
  fork: (messageId: string) =>
    api.post<{ new_session_id: string }>(`/chat/fork/${messageId}`)
}

// Config APIs
export const configApi = {
  get: () => api.get('/config'),
  
  update: (config: Record<string, unknown>) =>
    api.post('/config', config),
  
  validateKey: (provider: string, apiKey: string) =>
    api.post<{ valid: boolean }>('/config/validate-api-key', null, {
      params: { provider, api_key: apiKey }
    }),
  
  getProfiles: () =>
    api.get('/config/profiles'),
  
  applyProfile: (profileName: string) =>
    api.post(`/config/profiles/${profileName}`),
  
  validate: () =>
    api.get<{ valid: boolean; message?: string }>('/config/validate')
}

// Health APIs
export const healthApi = {
  check: () => api.get('/health'),
  ready: () => api.get('/health/ready'),
  live: () => api.get('/health/live')
}

export default api
