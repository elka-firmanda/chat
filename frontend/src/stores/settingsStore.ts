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
  
  isLoading: boolean
  error: string | null
  
  // Actions
  loadConfig: () => Promise<void>
  updateConfig: (updates: Partial<ConfigState>) => Promise<void>
  validateApiKey: (provider: string, apiKey: string) => Promise<boolean>
  applyProfile: (profileName: string) => Promise<void>
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
    ]
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
  
  applyProfile: async (profileName) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_URL}/v1/config/profiles/${profileName}`)
      const data = response.data
      
      set({
        agents: data.config.agents || get().agents,
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: `Failed to apply profile: ${profileName}`
      })
    }
  }
}))
