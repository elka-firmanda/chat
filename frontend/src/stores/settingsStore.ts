import { create } from 'zustand'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

interface AgentSettings {
  provider: string
  model: string
  max_tokens: number
  temperature: number
  system_prompt: string
}

interface GeneralSettings {
  timezone: string
  theme: 'light' | 'dark'
  example_questions: string[]
  pagination: {
    mode: 'button' | 'infinite' | 'virtual'
    page_size: number
    virtual_threshold: number
  }
}

interface DatabaseSettings {
  type: 'sqlite' | 'postgresql'
  sqlite_path: string
  postgresql_connection?: string
  pool_size: number
}

interface ConfigState {
  general: GeneralSettings
  database: DatabaseSettings
  agents: {
    master: AgentSettings
    planner: AgentSettings
    researcher: AgentSettings
    tools: AgentSettings
    database: AgentSettings
  }
  api_keys: Record<string, string>
  
  currentProfile: string | null
  profiles: {
    fast: { description: string; settings: Record<string, unknown> }
    deep: { description: string; settings: Record<string, unknown> }
  } | null
  
  isLoading: boolean
  error: string | null
  
  // Actions
  loadConfig: () => Promise<void>
  updateConfig: (updates: Partial<ConfigState>) => Promise<void>
  validateApiKey: (provider: string, apiKey: string) => Promise<boolean>
  validateDatabase: (dbType: string, connectionString: string, poolSize: number) => Promise<{ valid: boolean; message: string }>
  switchDatabase: (dbType: string, connectionString: string, poolSize: number) => Promise<{ success: boolean; message: string }>
  migrateDatabase: (sqlitePath: string, postgresqlConnection: string) => Promise<{ success: boolean; message: string }>
  applyProfile: (profileName: string) => Promise<void>
  loadProfiles: () => Promise<void>
}

export const useSettingsStore = create<ConfigState>()((set, get) => ({
  general: {
    timezone: 'auto',
    theme: 'light',
    example_questions: [
      'What are the latest AI breakthroughs?',
      'Analyze my sales data for Q4',
      'How does quantum computing work?',
      'Generate a chart of user growth'
    ],
    pagination: {
      mode: 'button',
      page_size: 30,
      virtual_threshold: 100
    }
  },
  database: {
    type: 'sqlite',
    sqlite_path: './data/chatbot.db',
    pool_size: 5
  },
  agents: {
    master: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      temperature: 0.7,
      system_prompt: ''
    },
    planner: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      temperature: 0.7,
      system_prompt: ''
    },
    researcher: {
      provider: 'openai',
      model: 'gpt-4-turbo',
      max_tokens: 4096,
      temperature: 0.7,
      system_prompt: ''
    },
    tools: {
      provider: 'openai',
      model: 'gpt-4-turbo',
      max_tokens: 2048,
      temperature: 0.7,
      system_prompt: ''
    },
    database: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      temperature: 0.7,
      system_prompt: ''
    }
  },
  api_keys: {},
  
  currentProfile: null,
  profiles: null,
  
  isLoading: false,
  error: null,
  
  loadConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get(`${API_URL}/v1/config`)
      const data = response.data
      
      set({
        general: data.general || get().general,
        database: data.database || get().database,
        agents: data.agents || get().agents,
        api_keys: data.api_keys || {},
        currentProfile: data.current_profile || null,
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: 'Failed to load configuration'
      })
    }
  },
  
  updateConfig: async (updates) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_URL}/v1/config`, updates)
      const data = response.data
      
      set({
        general: data.general || get().general,
        database: data.database || get().database,
        agents: data.agents || get().agents,
        api_keys: data.api_keys || {},
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: 'Failed to save configuration'
      })
    }
  },
  
  validateApiKey: async (provider, apiKey) => {
    try {
      const response = await axios.post(`${API_URL}/v1/config/validate-api-key`, null, {
        params: { provider, api_key: apiKey }
      })
      return response.data.valid
    } catch {
      return false
    }
  },
  
  validateDatabase: async (dbType, connectionString, poolSize) => {
    try {
      const response = await axios.post(`${API_URL}/v1/config/database/validate`, {
        type: dbType,
        sqlite_path: dbType === 'sqlite' ? connectionString : './data/chatbot.db',
        postgresql_connection: dbType === 'postgresql' ? connectionString : '',
        pool_size: poolSize
      })
      return { valid: response.data.valid, message: response.data.message }
    } catch (error) {
      const message = error.response?.data?.message || 'Validation failed'
      return { valid: false, message }
    }
  },
  
  switchDatabase: async (dbType, connectionString, poolSize) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_URL}/v1/config/database/switch`, {
        type: dbType,
        sqlite_path: dbType === 'sqlite' ? connectionString : './data/chatbot.db',
        postgresql_connection: dbType === 'postgresql' ? connectionString : '',
        pool_size: poolSize
      })
      set({ isLoading: false })
      return { success: true, message: response.data.message }
    } catch (error) {
      const message = error.response?.data?.message || 'Failed to switch database'
      set({ isLoading: false, error: message })
      return { success: false, message }
    }
  },
  
  migrateDatabase: async (sqlitePath, postgresqlConnection) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_URL}/v1/config/database/migrate`, {
        sqlite_path: sqlitePath,
        postgresql_connection: postgresqlConnection
      })
      set({ isLoading: false })
      return response.data
    } catch (error) {
      const message = error.response?.data?.message || 'Migration failed'
      set({ isLoading: false, error: message })
      return { success: false, message }
    }
  },
  
  applyProfile: async (profileName) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_URL}/v1/config/profiles/${profileName}`)
      const data = response.data
      
      set({
        agents: data.config.agents || get().agents,
        currentProfile: profileName,
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: `Failed to apply profile: ${profileName}`
      })
    }
  },
  
  loadProfiles: async () => {
    try {
      const response = await axios.get(`${API_URL}/v1/config/profiles`)
      const data = response.data
      
      set({
        profiles: data.profiles,
        currentProfile: data.current_profile
      })
    } catch (error) {
      console.error('Failed to load profiles:', error)
    }
  }
}))
