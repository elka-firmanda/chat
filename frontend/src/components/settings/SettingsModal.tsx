import { useState, useEffect, useCallback } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import * as Switch from '@radix-ui/react-switch'
import { X, Check, AlertCircle, Eye, EyeOff, Save, Loader2, Database, Cpu, Search, Hammer, Server, Globe, Settings as SettingsIcon } from 'lucide-react'

// Provider options
const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'openrouter', label: 'OpenRouter' },
]

// Model options per provider
const MODELS: Record<string, { value: string; label: string }[]> = {
  anthropic: [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  openai: [
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  ],
  openrouter: [
    { value: 'anthropic/claude-3.5-sonnet', label: 'Anthropic Claude 3.5 Sonnet' },
    { value: 'openai/gpt-4-turbo', label: 'OpenAI GPT-4 Turbo' },
    { value: 'google/gemini-pro', label: 'Google Gemini Pro' },
  ],
}

// Tool options
const TOOL_OPTIONS = [
  { value: 'code_executor', label: 'Code Executor' },
  { value: 'calculator', label: 'Calculator' },
  { value: 'chart_generator', label: 'Chart Generator' },
  { value: 'scraper', label: 'Web Scraper' },
]

// Profile options
const PROFILES = [
  { value: 'fast', label: 'Fast (Lightweight)' },
  { value: 'deep', label: 'Deep (Comprehensive)' },
  { value: 'custom', label: 'Custom' },
]

// Mask API key for display
function maskApiKey(key: string): string {
  if (!key) return ''
  if (key.length <= 4) return '*'.repeat(key.length)
  return key.slice(0, 2) + '*'.repeat(key.length - 4) + key.slice(-2)
}

interface SettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ConfigData {
  general: {
    timezone: string
    theme: string
    example_questions: string[]
  }
  database: {
    type: string
    sqlite_path: string
    postgresql_connection: string
    pool_size: number
  }
  agents: {
    master: {
      provider: string
      model: string
      max_tokens: number
      temperature: number
      system_prompt: string
    }
    planner: {
      provider: string
      model: string
      max_tokens: number
      system_prompt: string
    }
    researcher: {
      provider: string
      model: string
      max_tokens: number
      tavily_api_key: string
      max_urls_to_scrape: number
      scraping_timeout: number
      system_prompt: string
    }
    tools: {
      provider: string
      model: string
      max_tokens: number
      enabled_tools: string[]
      sandbox_enabled: boolean
      system_prompt: string
    }
    database: {
      provider: string
      model: string
      max_tokens: number
      data_warehouse_schema: string
      system_prompt: string
    }
  }
  api_keys: {
    anthropic: string
    openai: string
    openrouter: string
    tavily: string
  }
  profiles: {
    fast: { master: { model: string }; planner: { model: string } }
    deep: { master: { model: string }; researcher: { max_urls_to_scrape: number } }
  }
}

const defaultConfig: ConfigData = {
  general: {
    timezone: 'auto',
    theme: 'light',
    example_questions: [
      'What are the latest AI breakthroughs?',
      'Analyze my sales data for Q4',
      'How does quantum computing work?',
      'Generate a chart of user growth',
    ],
  },
  database: {
    type: 'sqlite',
    sqlite_path: './data/chatbot.db',
    postgresql_connection: '',
    pool_size: 5,
  },
  agents: {
    master: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      temperature: 0.7,
      system_prompt: 'You are a master orchestrator that coordinates subagents to answer complex questions.',
    },
    planner: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2048,
      system_prompt: 'You create step-by-step execution plans for the master agent.',
    },
    researcher: {
      provider: 'openai',
      model: 'gpt-4-turbo',
      max_tokens: 4096,
      tavily_api_key: '',
      max_urls_to_scrape: 5,
      scraping_timeout: 600,
      system_prompt: 'You are a research specialist that finds and analyzes information from the web.',
    },
    tools: {
      provider: 'openai',
      model: 'gpt-4-turbo',
      max_tokens: 2048,
      enabled_tools: ['code_executor', 'calculator', 'chart_generator'],
      sandbox_enabled: true,
      system_prompt: 'You execute code and calculations to help answer user questions.',
    },
    database: {
      provider: 'anthropic',
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      data_warehouse_schema: '',
      system_prompt: 'You query and analyze data from the data warehouse.',
    },
  },
  api_keys: {
    anthropic: '',
    openai: '',
    openrouter: '',
    tavily: '',
  },
  profiles: {
    fast: { master: { model: 'gpt-3.5-turbo' }, planner: { model: 'gpt-3.5-turbo' } },
    deep: { master: { model: 'claude-3-opus-20240229' }, researcher: { max_urls_to_scrape: 10 } },
  },
}

function ApiKeyInput({
  label,
  value,
  onChange,
  provider,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  provider: 'anthropic' | 'openai' | 'openrouter' | 'tavily'
  placeholder?: string
}) {
  const [show, setShow] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean | null
    message: string
  }>({ valid: null, message: '' })
  const [lastValidatedKey, setLastValidatedKey] = useState('')

  const maskedValue = value ? maskApiKey(value) : ''

  const handleValidate = useCallback(async () => {
    if (!value || value === lastValidatedKey) return

    setValidating(true)
    setValidationResult({ valid: null, message: '' })

    try {
      const response = await fetch(`/api/v1/config/validate-api-key?provider=${provider}&api_key=${encodeURIComponent(value)}`)
      
      if (response.ok) {
        const data = await response.json()
        setValidationResult({ valid: true, message: data.message || 'API key is valid' })
        setLastValidatedKey(value)
      } else {
        const errorData = await response.json()
        setValidationResult({ 
          valid: false, 
          message: errorData.message || errorData.detail?.message || 'Validation failed' 
        })
      }
    } catch (error) {
      setValidationResult({ 
        valid: false, 
        message: error instanceof Error ? error.message : 'Network error during validation' 
      })
    } finally {
      setValidating(false)
    }
  }, [value, provider, lastValidatedKey])

  // Auto-validate on blur if key changed
  const handleBlur = () => {
    if (value && value !== lastValidatedKey) {
      handleValidate()
    }
  }

  // Reset validation when value changes
  const handleChange = (newValue: string) => {
    onChange(newValue)
    if (newValue !== lastValidatedKey) {
      setValidationResult({ valid: null, message: '' })
    }
  }

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-foreground">{label}</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={show ? 'text' : 'password'}
            value={show ? value : maskedValue}
            onChange={(e) => handleChange(e.target.value)}
            onBlur={handleBlur}
            placeholder={placeholder || `Enter ${label.toLowerCase()}`}
            className={`w-full px-3 py-2 bg-background border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              validationResult.valid === false ? 'border-red-500 focus:ring-red-500' : 'border-input'
            }`}
          />
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {value && (
          <button
            type="button"
            onClick={handleValidate}
            disabled={validating || value === lastValidatedKey}
            className={`px-3 py-2 rounded-lg text-sm transition-colors disabled:opacity-50 ${
              validationResult.valid === true 
                ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                : validationResult.valid === false 
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-muted hover:bg-muted/80'
            }`}
            title={validationResult.valid === false ? validationResult.message : undefined}
          >
            {validating ? (
              <Loader2 size={16} className="animate-spin" />
            ) : validationResult.valid === true ? (
              <Check size={16} className="text-green-600" />
            ) : validationResult.valid === false ? (
              <AlertCircle size={16} className="text-red-600" />
            ) : (
              'Validate'
            )}
          </button>
        )}
      </div>
      {validationResult.message && (
        <p className={`text-xs ${
          validationResult.valid === true 
            ? 'text-green-600' 
            : validationResult.valid === false 
            ? 'text-red-600' 
            : 'text-muted-foreground'
        }`}>
          {validationResult.message}
        </p>
      )}
    </div>
  )
}

function AgentSettingsTab({
  title,
  icon: Icon,
  config,
  onChange,
  showTemperature = false,
  showTools = false,
  showSchema = false,
}: {
  title: string
  icon: React.ElementType
  config: ConfigData['agents']['master']
  onChange: (config: ConfigData['agents']['master']) => void
  showTemperature?: boolean
  showTools?: boolean
  showSchema?: boolean
}) {
  const availableModels = MODELS[config.provider] || MODELS.antropic

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Icon size={18} className="text-primary" />
        <h3 className="font-medium">{title} Settings</h3>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="block text-sm font-medium text-foreground">Provider</label>
          <select
            value={config.provider}
            onChange={(e) => onChange({ ...config, provider: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="block text-sm font-medium text-foreground">Model</label>
          <select
            value={config.model}
            onChange={(e) => onChange({ ...config, model: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {availableModels.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="block text-sm font-medium text-foreground">Max Tokens</label>
          <input
            type="number"
            value={config.max_tokens}
            onChange={(e) => onChange({ ...config, max_tokens: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {showTemperature && (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-foreground">Temperature</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={config.temperature}
              onChange={(e) => onChange({ ...config, temperature: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        )}

        {showTools && 'enabled_tools' in config && (
          <div className="col-span-2 space-y-2">
            <label className="block text-sm font-medium text-foreground">Enabled Tools</label>
            <div className="flex flex-wrap gap-2">
              {TOOL_OPTIONS.map((tool) => (
                <label key={tool.value} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(config as { enabled_tools: string[] }).enabled_tools.includes(tool.value)}
                    onChange={(e) => {
                      const enabled = e.target.checked
                        ? [...(config as { enabled_tools: string[] }).enabled_tools, tool.value]
                        : (config as { enabled_tools: string[] }).enabled_tools.filter(t => t !== tool.value)
                      onChange({ ...config, enabled_tools: enabled } as typeof config)
                    }}
                    className="rounded"
                  />
                  {tool.label}
                </label>
              ))}
            </div>
          </div>
        )}

        {showSchema && 'data_warehouse_schema' in config && (
          <div className="col-span-2 space-y-1">
            <label className="block text-sm font-medium text-foreground">Data Warehouse Schema</label>
            <textarea
              value={(config as { data_warehouse_schema: string }).data_warehouse_schema}
              onChange={(e) => onChange({ ...config, data_warehouse_schema: e.target.value } as typeof config)}
              placeholder="Describe your database schema..."
              rows={3}
              className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>
        )}
      </div>

      <div className="space-y-1">
        <label className="block text-sm font-medium text-foreground">System Prompt</label>
        <textarea
          value={config.system_prompt}
          onChange={(e) => onChange({ ...config, system_prompt: e.target.value })}
          rows={4}
          className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
        />
      </div>
    </div>
  )
}

export default function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState('general')
  const [config, setConfig] = useState<ConfigData>(defaultConfig)
  const [saving, setSaving] = useState(false)
  const [profile, setProfile] = useState('custom')

  // Load config on mount
  useEffect(() => {
    // In production, fetch config from API
    setConfig(defaultConfig)
  }, [])

  const handleSave = async () => {
    setSaving(true)
    // In production, save to API
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaving(false)
    onOpenChange(false)
  }

  const handleProfileChange = (newProfile: string) => {
    setProfile(newProfile)
    if (newProfile === 'fast') {
      setConfig({
        ...config,
        agents: {
          ...config.agents,
          master: { ...config.agents.master, model: 'gpt-3.5-turbo' },
          planner: { ...config.agents.planner, model: 'gpt-3.5-turbo' },
        },
      })
    } else if (newProfile === 'deep') {
      setConfig({
        ...config,
        agents: {
          ...config.agents,
          master: { ...config.agents.master, model: 'claude-3-opus-20240229' },
          researcher: { ...config.agents.researcher, max_urls_to_scrape: 10 },
        },
      })
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden animate-in zoom-in-95">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <SettingsIcon size={20} className="text-primary" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-semibold">Settings</Dialog.Title>
                <Dialog.Description className="text-sm text-muted-foreground">
                  Configure your chatbot preferences
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <button className="p-2 hover:bg-muted rounded-lg transition-colors">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {/* Profile Selector */}
          <div className="px-4 py-3 border-b bg-muted/30">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">Profile:</span>
              <div className="flex gap-1 bg-muted p-1 rounded-lg">
                {PROFILES.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => handleProfileChange(p.value)}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      profile === p.value
                        ? 'bg-background shadow-sm text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Tabs */}
          <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex">
            {/* Tab List */}
            <Tabs.List className="w-56 border-r p-2 space-y-1 bg-muted/30 overflow-y-auto max-h-[60vh]">
              <Tabs.Trigger
                value="general"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'general' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Globe size={16} />
                General
              </Tabs.Trigger>
              <Tabs.Trigger
                value="database"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'database' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Database size={16} />
                Database
              </Tabs.Trigger>
              <Tabs.Trigger
                value="master"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'master' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Cpu size={16} />
                Master Agent
              </Tabs.Trigger>
              <Tabs.Trigger
                value="planner"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'planner' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <SettingsIcon size={16} />
                Planner
              </Tabs.Trigger>
              <Tabs.Trigger
                value="researcher"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'researcher' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Search size={16} />
                Researcher
              </Tabs.Trigger>
              <Tabs.Trigger
                value="tools"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'tools' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Hammer size={16} />
                Tools
              </Tabs.Trigger>
              <Tabs.Trigger
                value="database-agent"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'database-agent' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Server size={16} />
                Database Agent
              </Tabs.Trigger>
              <Tabs.Trigger
                value="api-keys"
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'api-keys' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <KeyIcon size={16} />
                API Keys
              </Tabs.Trigger>
            </Tabs.List>

            {/* Tab Content */}
            <div className="flex-1 p-4 overflow-y-auto max-h-[60vh]">
              <Tabs.Content value="general" className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Timezone</label>
                  <select
                    value={config.general.timezone}
                    onChange={(e) => setConfig({ ...config, general: { ...config.general, timezone: e.target.value } })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">Eastern Time</option>
                    <option value="America/Los_Angeles">Pacific Time</option>
                    <option value="Europe/London">London</option>
                    <option value="Asia/Tokyo">Tokyo</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Theme</label>
                  <select
                    value={config.general.theme}
                    onChange={(e) => setConfig({ ...config, general: { ...config.general, theme: e.target.value } })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="system">System</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Example Questions</label>
                  <textarea
                    value={config.general.example_questions.join('\n')}
                    onChange={(e) => setConfig({ ...config, general: { ...config.general, example_questions: e.target.value.split('\n').filter(Boolean) } })}
                    placeholder="Enter one question per line..."
                    rows={6}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                </div>
              </Tabs.Content>

              <Tabs.Content value="database" className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Database Type</label>
                  <select
                    value={config.database.type}
                    onChange={(e) => setConfig({ ...config, database: { ...config.database, type: e.target.value } })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="sqlite">SQLite</option>
                    <option value="postgresql">PostgreSQL</option>
                  </select>
                </div>

                {config.database.type === 'sqlite' && (
                  <div className="space-y-1">
                    <label className="block text-sm font-medium text-foreground">SQLite Path</label>
                    <input
                      type="text"
                      value={config.database.sqlite_path}
                      onChange={(e) => setConfig({ ...config, database: { ...config.database, sqlite_path: e.target.value } })}
                      className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                )}

                {config.database.type === 'postgresql' && (
                  <div className="space-y-1">
                    <label className="block text-sm font-medium text-foreground">PostgreSQL Connection</label>
                    <input
                      type="text"
                      value={config.database.postgresql_connection}
                      onChange={(e) => setConfig({ ...config, database: { ...config.database, postgresql_connection: e.target.value } })}
                      placeholder="postgresql://user:password@localhost:5432/chatbot"
                      className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                )}

                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Pool Size</label>
                  <input
                    type="number"
                    value={config.database.pool_size}
                    onChange={(e) => setConfig({ ...config, database: { ...config.database, pool_size: parseInt(e.target.value) || 5 } })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </Tabs.Content>

              <Tabs.Content value="master">
                <AgentSettingsTab
                  title="Master Agent"
                  icon={Cpu}
                  config={config.agents.master}
                  onChange={(c) => setConfig({ ...config, agents: { ...config.agents, master: c } })}
                  showTemperature
                />
              </Tabs.Content>

              <Tabs.Content value="planner">
                <AgentSettingsTab
                  title="Planner"
                  icon={SettingsIcon}
                  config={config.agents.planner}
                  onChange={(c) => setConfig({ ...config, agents: { ...config.agents, planner: c } })}
                />
              </Tabs.Content>

              <Tabs.Content value="researcher">
                <AgentSettingsTab
                  title="Researcher"
                  icon={Search}
                  config={config.agents.researcher}
                  onChange={(c) => setConfig({ ...config, agents: { ...config.agents, researcher: c } })}
                />
                <div className="mt-4 space-y-4 pt-4 border-t">
                  <ApiKeyInput
                    label="Tavily API Key"
                    provider="tavily"
                    value={config.agents.researcher.tavily_api_key}
                    onChange={(v) => setConfig({ ...config, agents: { ...config.agents, researcher: { ...config.agents.researcher, tavily_api_key: v } } })}
                    placeholder="tvly-..."
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="block text-sm font-medium text-foreground">Max URLs to Scrape</label>
                      <input
                        type="number"
                        value={config.agents.researcher.max_urls_to_scrape}
                        onChange={(e) => setConfig({ ...config, agents: { ...config.agents, researcher: { ...config.agents.researcher, max_urls_to_scrape: parseInt(e.target.value) || 5 } } })}
                        className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="block text-sm font-medium text-foreground">Scraping Timeout (s)</label>
                      <input
                        type="number"
                        value={config.agents.researcher.scraping_timeout}
                        onChange={(e) => setConfig({ ...config, agents: { ...config.agents, researcher: { ...config.agents.researcher, scraping_timeout: parseInt(e.target.value) || 600 } } })}
                        className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                </div>
              </Tabs.Content>

              <Tabs.Content value="tools">
                <AgentSettingsTab
                  title="Tools"
                  icon={Hammer}
                  config={config.agents.tools}
                  onChange={(c) => setConfig({ ...config, agents: { ...config.agents, tools: c } })}
                  showTools
                />
              </Tabs.Content>

              <Tabs.Content value="database-agent">
                <AgentSettingsTab
                  title="Database Agent"
                  icon={Server}
                  config={config.agents.database}
                  onChange={(c) => setConfig({ ...config, agents: { ...config.agents, database: c } })}
                  showSchema
                />
              </Tabs.Content>

              <Tabs.Content value="api-keys" className="space-y-6">
                <div>
                  <h3 className="font-medium mb-4 flex items-center gap-2">
                    <KeyIcon size={18} />
                    API Keys
                  </h3>
                  <div className="space-y-4">
                    <ApiKeyInput
                      label="Anthropic API Key"
                      provider="anthropic"
                      value={config.api_keys.anthropic}
                      onChange={(v) => setConfig({ ...config, api_keys: { ...config.api_keys, anthropic: v } })}
                      placeholder="sk-ant-..."
                    />
                    <ApiKeyInput
                      label="OpenAI API Key"
                      provider="openai"
                      value={config.api_keys.openai}
                      onChange={(v) => setConfig({ ...config, api_keys: { ...config.api_keys, openai: v } })}
                      placeholder="sk-..."
                    />
                    <ApiKeyInput
                      label="OpenRouter API Key"
                      provider="openrouter"
                      value={config.api_keys.openrouter}
                      onChange={(v) => setConfig({ ...config, api_keys: { ...config.api_keys, openrouter: v } })}
                    />
                    <ApiKeyInput
                      label="Tavily API Key"
                      provider="tavily"
                      value={config.api_keys.tavily}
                      onChange={(v) => setConfig({ ...config, api_keys: { ...config.api_keys, tavily: v } })}
                      placeholder="tvly-..."
                    />
                  </div>
                </div>
              </Tabs.Content>
            </div>
          </Tabs.Root>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-4 border-t bg-muted/30">
            <Dialog.Close asChild>
              <button className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save Changes
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function KeyIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  )
}
