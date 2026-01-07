import { useState, useEffect, useCallback } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import { X, Check, AlertCircle, Eye, EyeOff, Save, Loader2, Database, Cpu, Search, Hammer, Server, Globe, Settings as SettingsIcon, Plus, Trash2, Edit, Wrench, RefreshCw } from 'lucide-react'
import { toolsApi, configApi, type CustomTool, type ModelOption } from '../../services/api'
import { useSettingsStore } from '../../stores/settingsStore'
import { useToastStore } from '../../hooks/useToast'

// Provider options
const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'openrouter', label: 'OpenRouter' },
]

// Model options per provider
const MODELS: Record<string, { value: string; label: string }[]> = {
  anthropic: [
    { value: 'claude-sonnet-4-20250514', label: 'Claude 4 Sonnet (Latest)' },
    { value: 'claude-opus-4-20250514', label: 'Claude 4 Opus' },
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
    { value: 'claude-3-5-sonnet-20240620', label: 'Claude 3.5 Sonnet (June 2024)' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-2024-11-20', label: 'GPT-4o (2024-11-20)' },
    { value: 'gpt-4o-2024-08-06', label: 'GPT-4o (2024-08-06)' },
    { value: 'gpt-4o-2024-05-13', label: 'GPT-4o (2024-05-13)' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-4-turbo-2024-04-09', label: 'GPT-4 Turbo (2024-04-09)' },
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    { value: 'gpt-3.5-turbo-0125', label: 'GPT-3.5 Turbo (0125)' },
    { value: 'o1', label: 'O1' },
    { value: 'o1-2024-12-17', label: 'O1 (2024-12-17)' },
    { value: 'o3-mini', label: 'O3 Mini' },
  ],
  openrouter: [
    { value: 'anthropic/claude-sonnet-4-20250514', label: 'Anthropic Claude Sonnet 4' },
    { value: 'anthropic/claude-opus-4-20250514', label: 'Anthropic Claude Opus 4' },
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

interface AgentConfig {
  provider: string
  model: string
  max_tokens: number
  temperature?: number
  system_prompt: string
  tavily_api_key?: string
  max_urls_to_scrape?: number
  scraping_timeout?: number
  enabled_tools?: string[]
  sandbox_enabled?: boolean
  data_warehouse_schema?: string
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
    master: AgentConfig
    planner: AgentConfig
    researcher: AgentConfig
    tools: AgentConfig
    database: AgentConfig
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
      const response = await fetch(`/api/v1/config/validate-api-key?provider=${provider}&api_key=${encodeURIComponent(value)}`, {
        method: 'POST',
      })
      
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
            className={`w-full px-3 py-2.5 bg-background border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              validationResult.valid === false ? 'border-red-500 focus:ring-red-500' : 'border-input'
            }`}
          />
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-2 top-1/2 -translate-y-1/2 min-h-[36px] min-w-[36px] flex items-center justify-center text-muted-foreground hover:text-foreground"
          >
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {value && (
          <button
            type="button"
            onClick={handleValidate}
            disabled={validating || value === lastValidatedKey}
            className={`px-3 py-2.5 min-h-[44px] rounded-lg text-sm transition-colors disabled:opacity-50 ${
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
  config: AgentConfig
  onChange: (config: AgentConfig) => void
  showTemperature?: boolean
  showTools?: boolean
  showSchema?: boolean
}) {
  const [models, setModels] = useState<ModelOption[]>(MODELS[config.provider] || MODELS.anthropic)
  const [loadingModels, setLoadingModels] = useState(false)
  const [modelError, setModelError] = useState<string | null>(null)

  const fetchModels = async (provider: string) => {
    setLoadingModels(true)
    setModelError(null)
    try {
      const response = await configApi.getModels(provider)
      if (response.data.models.length > 0) {
        setModels(response.data.models)
        if (!response.data.models.find(m => m.value === config.model)) {
          onChange({ ...config, model: response.data.models[0].value })
        }
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 
        'Failed to fetch models'
      setModelError(errorMessage)
      setModels(MODELS[provider] || MODELS.anthropic)
    } finally {
      setLoadingModels(false)
    }
  }

  useEffect(() => {
    fetchModels(config.provider)
  }, [config.provider])

  const handleRefreshModels = () => {
    fetchModels(config.provider)
  }

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
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-foreground">Model</label>
            <button
              type="button"
              onClick={handleRefreshModels}
              disabled={loadingModels}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors disabled:opacity-50"
              title="Refresh models from provider"
            >
              <RefreshCw size={14} className={loadingModels ? 'animate-spin' : ''} />
            </button>
          </div>
          <select
            value={config.model}
            onChange={(e) => onChange({ ...config, model: e.target.value })}
            className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {models.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          {modelError && (
            <p className="text-xs text-red-600">{modelError}</p>
          )}
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
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [profile, setProfile] = useState('custom')
  const { toast } = useToastStore()
  const detectedTimezone = typeof Intl !== 'undefined' 
    ? Intl.DateTimeFormat().resolvedOptions().timeZone 
    : 'UTC'

  const loadConfig = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await configApi.get()
      const data = response.data
      setConfig({
        general: data.general || defaultConfig.general,
        database: data.database || defaultConfig.database,
        agents: data.agents || defaultConfig.agents,
        profiles: data.profiles || defaultConfig.profiles,
      })
    } catch (err) {
      setError('Failed to load configuration')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadConfig()
    }
  }, [open, loadConfig])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await configApi.update({
        general: config.general,
        database: config.database,
        agents: config.agents,
        profiles: config.profiles,
      })
      await loadConfig()
      toast.success('Settings saved successfully')
      // Keep modal open - don't call onOpenChange(false)
    } catch (err) {
      setError('Failed to save configuration')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleProfileChange = async (newProfile: string) => {
    setProfile(newProfile)
    if (newProfile === 'custom') {
      return
    }
    try {
      setLoading(true)
      const response = await configApi.applyProfile(newProfile)
      const data = response.data
      setConfig({
        ...config,
        agents: data.config.agents || config.agents,
      })
    } catch (err) {
      setError(`Failed to apply profile: ${newProfile}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden animate-in zoom-in-95 z-50 sm:max-w-3xl flex flex-col">
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                <SettingsIcon size={20} className="text-primary" />
              </div>
              <div className="min-w-0">
                <Dialog.Title className="text-lg font-semibold truncate">Settings</Dialog.Title>
                <Dialog.Description className="text-sm text-muted-foreground truncate">
                  Configure your chatbot preferences
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <button className="min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-muted rounded-lg transition-colors shrink-0 ml-2">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {error && (
            <div className="mx-4 mt-3 p-3 bg-red-50 text-red-600 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {loading && !saving && (
            <div className="mx-4 mt-3 p-3 bg-muted/50 rounded-lg text-sm flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              Loading configuration...
            </div>
          )}

          <div className="px-4 py-3 border-b bg-muted/30">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <span className="text-sm font-medium shrink-0">Profile:</span>
              <div className="flex gap-1 bg-muted p-1 rounded-lg overflow-x-auto">
                {PROFILES.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => handleProfileChange(p.value)}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
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

          <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col sm:flex-row">
            <Tabs.List className="flex flex-row sm:flex-col w-full sm:w-48 border-b sm:border-r sm:border-b-0 p-2 gap-1 bg-muted/30 overflow-x-auto sm:overflow-x-visible sm:overflow-y-auto shrink-0 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] justify-start sm:justify-start">
              <Tabs.Trigger
                value="general"
                title="General"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'general' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Globe size={18} className="shrink-0" />
                <span className="hidden sm:inline">General</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="database"
                title="Database"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'database' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Database size={18} className="shrink-0" />
                <span className="hidden sm:inline">Database</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="master"
                title="Master Agent"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'master' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Cpu size={18} className="shrink-0" />
                <span className="hidden sm:inline">Master</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="planner"
                title="Planner Agent"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'planner' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <SettingsIcon size={18} className="shrink-0" />
                <span className="hidden sm:inline">Planner</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="researcher"
                title="Researcher Agent"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'researcher' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Search size={18} className="shrink-0" />
                <span className="hidden sm:inline">Researcher</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="tools"
                title="Tools Agent"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'tools' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Hammer size={18} className="shrink-0" />
                <span className="hidden sm:inline">Tools</span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="database-agent"
                title="Database Agent"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'database-agent' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Server size={18} className="shrink-0" />
                <span className="hidden sm:inline">DB Agent</span>
              </Tabs.Trigger>

              <Tabs.Trigger
                value="custom-tools"
                title="Custom Tools"
                className={`flex items-center justify-center sm:justify-start gap-2 p-2.5 sm:px-3 sm:py-2.5 min-h-[44px] min-w-[44px] sm:w-full rounded-lg text-sm transition-colors touch-manipulation ${
                  activeTab === 'custom-tools' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Wrench size={18} className="shrink-0" />
                <span className="hidden sm:inline">Custom</span>
              </Tabs.Trigger>
            </Tabs.List>

            {/* Tab Content */}
            <div className="flex-1 p-3 sm:p-4 overflow-y-auto">
              <Tabs.Content value="general" className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-foreground">Timezone</label>
                  <select
                    value={config.general.timezone}
                    onChange={(e) => setConfig({ ...config, general: { ...config.general, timezone: e.target.value } })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="auto">Auto-detect ({detectedTimezone})</option>
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
                    <p className="text-xs text-muted-foreground">
                      Use format: postgresql://username:password@host:port/database
                    </p>
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

                {config.database.type === 'sqlite' && config.database.postgresql_connection && (
                  <div className="pt-4 border-t space-y-3">
                    <h4 className="font-medium text-sm">Migrate to PostgreSQL</h4>
                    <p className="text-xs text-muted-foreground">
                      Copy all data from SQLite to PostgreSQL before switching.
                    </p>
                    <button
                      onClick={async () => {
                        if (confirm('Migrate all data from SQLite to PostgreSQL? This cannot be undone.')) {
                          const result = await useSettingsStore.getState().migrateDatabase(
                            config.database.sqlite_path,
                            config.database.postgresql_connection
                          )
                          if (result.success) {
                            alert('Migration completed! You can now switch to PostgreSQL.')
                          } else {
                            alert(`Migration failed: ${result.message}`)
                          }
                        }
                      }}
                      className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                      Migrate Data to PostgreSQL
                    </button>
                  </div>
                )}
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
                    value={config.agents.researcher.tavily_api_key || ''}
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



              <Tabs.Content value="custom-tools">
                <CustomToolsTab />
              </Tabs.Content>
            </div>
          </Tabs.Root>

          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 p-4 border-t bg-muted/30">
            <Dialog.Close asChild>
              <button className="w-full sm:w-auto px-4 py-2.5 min-h-[44px] text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
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

function CustomToolsTab() {
  const [tools, setTools] = useState<CustomTool[]>([])
  const [loading, setLoading] = useState(true)
  const [showEditor, setShowEditor] = useState(false)
  const [editingTool, setEditingTool] = useState<CustomTool | null>(null)
  const [editorForm, setEditorForm] = useState({ name: '', description: '', code: '' })
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<{ valid: boolean | null; error: string | null }>({ valid: null, error: null })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadTools = useCallback(async () => {
    try {
      setLoading(true)
      const response = await toolsApi.list(true)
      setTools(response.data)
    } catch (err) {
      setError('Failed to load tools')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTools()
  }, [loadTools])

  const handleNewTool = async () => {
    try {
      const templateResponse = await toolsApi.getTemplate()
      setEditorForm({ name: '', description: '', code: templateResponse.data.template })
      setEditingTool(null)
      setValidationResult({ valid: null, error: null })
      setShowEditor(true)
    } catch (err) {
      setError('Failed to load template')
    }
  }

  const handleEditTool = (tool: CustomTool) => {
    setEditorForm({ name: tool.name, description: tool.description || '', code: tool.code })
    setEditingTool(tool)
    setValidationResult({ valid: null, error: null })
    setShowEditor(true)
  }

  const handleValidate = async () => {
    setValidating(true)
    setValidationResult({ valid: null, error: null })
    try {
      const response = await toolsApi.validate(editorForm.code)
      setValidationResult({ valid: response.data.valid, error: response.data.error })
    } catch (err) {
      setValidationResult({ valid: false, error: 'Validation request failed' })
    } finally {
      setValidating(false)
    }
  }

  const handleSave = async () => {
    if (validationResult.valid !== true) {
      setError('Please fix validation errors before saving')
      return
    }

    setSaving(true)
    setError(null)
    try {
      if (editingTool) {
        await toolsApi.update(editingTool.id, editorForm)
      } else {
        await toolsApi.create(editorForm.name, editorForm.code, editorForm.description)
      }
      setShowEditor(false)
      await loadTools()
    } catch (err) {
      setError(editingTool ? 'Failed to update tool' : 'Failed to create tool')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (toolId: string) => {
    if (!confirm('Are you sure you want to delete this tool?')) return

    try {
      await toolsApi.delete(toolId)
      await loadTools()
    } catch (err) {
      setError('Failed to delete tool')
    }
  }

  const handleToggle = async (tool: CustomTool) => {
    try {
      await toolsApi.update(tool.id, { enabled: !tool.enabled })
      await loadTools()
    } catch (err) {
      setError('Failed to toggle tool')
    }
  }

  if (showEditor) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium flex items-center gap-2">
            <Edit size={18} />
            {editingTool ? 'Edit Tool' : 'New Tool'}
          </h3>
          <button
            onClick={() => setShowEditor(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-foreground">Tool Name</label>
            <input
              type="text"
              value={editorForm.name}
              onChange={(e) => setEditorForm({ ...editorForm, name: e.target.value })}
              placeholder="my_custom_tool"
              disabled={editingTool !== null}
              className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-foreground">Description</label>
            <input
              type="text"
              value={editorForm.description}
              onChange={(e) => setEditorForm({ ...editorForm, description: e.target.value })}
              placeholder="What does this tool do?"
              className="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium text-foreground">Python Code</label>
              <button
                onClick={handleValidate}
                disabled={validating}
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                {validating ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                Validate
              </button>
            </div>
            <textarea
              value={editorForm.code}
              onChange={(e) => setEditorForm({ ...editorForm, code: e.target.value })}
              placeholder="def my_tool(arg1, arg2, **kwargs): ..."
              rows={12}
              className={`w-full px-3 py-2 bg-background border rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary resize-none ${
                validationResult.valid === false ? 'border-red-500' : 'border-input'
              }`}
            />
            {validationResult.error && (
              <p className="text-xs text-red-600">{validationResult.error}</p>
            )}
            {validationResult.valid === true && (
              <p className="text-xs text-green-600 flex items-center gap-1">
                <Check size={12} /> Code is valid
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <button
            onClick={() => setShowEditor(false)}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || validationResult.valid !== true}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            {editingTool ? 'Update' : 'Create'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium flex items-center gap-2">
          <Wrench size={18} />
          Custom Tools
        </h3>
        <button
          onClick={handleNewTool}
          className="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus size={16} />
          New Tool
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={24} className="animate-spin text-muted-foreground" />
        </div>
      ) : tools.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Wrench size={48} className="mx-auto mb-3 opacity-50" />
          <p>No custom tools yet</p>
          <p className="text-sm">Create your first tool to extend the chatbot&apos;s capabilities</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tools.map((tool) => (
            <div
              key={tool.id}
              className={`flex items-center justify-between p-3 bg-muted/50 rounded-lg border ${
                !tool.enabled ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${tool.enabled ? 'bg-primary/10' : 'bg-muted'}`}>
                  <Wrench size={16} className={tool.enabled ? 'text-primary' : 'text-muted-foreground'} />
                </div>
                <div>
                  <p className="font-medium text-sm">{tool.name}</p>
                  {tool.description && (
                    <p className="text-xs text-muted-foreground">{tool.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggle(tool)}
                  className={`p-1.5 rounded transition-colors ${
                    tool.enabled
                      ? 'text-green-600 hover:bg-green-100'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                  title={tool.enabled ? 'Disable' : 'Enable'}
                >
                  {tool.enabled ? <Check size={16} /> : <X size={16} />}
                </button>
                <button
                  onClick={() => handleEditTool(tool)}
                  className="p-1.5 text-muted-foreground hover:bg-muted rounded transition-colors"
                  title="Edit"
                >
                  <Edit size={16} />
                </button>
                <button
                  onClick={() => handleDelete(tool.id)}
                  className="p-1.5 text-red-600 hover:bg-red-100 rounded transition-colors"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
