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
  total: number
  has_more: boolean
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
    api.get<{ sessions: Session[]; total: number; limit: number; offset: number }>('/sessions', { params: { archived, limit, offset } }),
  
  get: (sessionId: string, limit = 30, offset = 0) =>
    api.get<SessionDetail>(`/sessions/${sessionId}`, { params: { limit, offset } }),
  
  create: (title?: string) =>
    api.post<Session>('/sessions', { title }),
  
  update: (sessionId: string, data: { title?: string; archived?: boolean }) =>
    api.patch<Session & { archived: boolean }>(`/sessions/${sessionId}`, data),
  
  archive: (sessionId: string) =>
    sessionsApi.update(sessionId, { archived: true }),
  
  unarchive: (sessionId: string) =>
    sessionsApi.update(sessionId, { archived: false }),
  
  delete: (sessionId: string) =>
    api.delete(`/sessions/${sessionId}`),
  
  search: (query: string, limit = 20, searchType: 'all' | 'sessions' | 'messages' = 'all') =>
    api.get<SearchResponse>('/sessions/search', { params: { q: query, limit, search_type: searchType } }),

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
  
  stream: (sessionId: string, lastEventId?: string) => {
    const url = lastEventId
      ? `${API_URL}/v1/chat/stream/${sessionId}?lastEventId=${encodeURIComponent(lastEventId)}`
      : `${API_URL}/v1/chat/stream/${sessionId}`
    return new EventSource(url)
  },
  
  cancel: (sessionId: string) =>
    api.post(`/chat/cancel/${sessionId}`),
  
  fork: (messageId: string) =>
    api.post<{ new_session_id: string }>(`/chat/fork/${messageId}`),
  
  // Intervention APIs
  intervene: (sessionId: string, action: 'retry' | 'skip' | 'abort') =>
    api.post<{ status: string; message: string; session_id: string; action: string }>(
      `/chat/intervene/${sessionId}`,
      { action }
    ),
  
  getInterventionStatus: (sessionId: string) =>
    api.get<{
      session_id: string
      awaiting_response: boolean
      pending_error: Record<string, unknown> | null
      available_actions: string[]
    }>(`/chat/intervention/${sessionId}`)
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

// Custom Tools APIs
export interface CustomTool {
  id: string
  name: string
  description: string | null
  code: string
  enabled: boolean
  created_at: string | null
}

export interface ToolValidateResponse {
  valid: boolean
  error: string | null
}

export interface ToolExecuteResponse {
  success: boolean
  result: Record<string, unknown> | null
  output: string | null
  execution_time: number
  error: string | null
}

export const toolsApi = {
  list: (includeDisabled = false) =>
    api.get<CustomTool[]>('/tools/custom', { params: { include_disabled: includeDisabled } }),
  
  get: (toolId: string) =>
    api.get<CustomTool>(`/tools/custom/${toolId}`),
  
  create: (name: string, code: string, description?: string) =>
    api.post<CustomTool>('/tools/custom', { name, code, description }),
  
  update: (toolId: string, data: { name?: string; code?: string; description?: string; enabled?: boolean }) =>
    api.patch<CustomTool>(`/tools/custom/${toolId}`, data),
  
  delete: (toolId: string) =>
    api.delete(`/tools/custom/${toolId}`),
  
  execute: (toolId: string, args: Record<string, unknown>) =>
    api.post<ToolExecuteResponse>(`/tools/custom/${toolId}/execute`, { arguments: args }),
  
  validate: (code: string) =>
    api.post<ToolValidateResponse>('/tools/validate', { code }),
  
  getTemplate: () =>
    api.get<{ template: string }>('/tools/template')
}

export default api
