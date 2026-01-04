import { useSettingsStore } from '../../stores/settingsStore'
import { MessageSquare, BarChart, Brain, Sparkles, Search, TrendingUp, Globe, Zap } from 'lucide-react'

interface ExampleCardsProps {
  onSelect: (question: string, requiresDeepSearch?: boolean) => void
}

// Keywords that suggest a question would benefit from deep search
const DEEP_SEARCH_KEYWORDS = [
  'latest', 'recent', 'current', 'new', 'trending', 'top',
  'research', 'analyze', 'compare', 'what is', 'how does',
  'explain', 'find', 'search', 'discover', 'explore',
  'statistics', 'data', 'trends', 'market', 'industry',
  'news', 'breakthroughs', 'developments', 'advancements'
]

interface QuestionItem {
  text: string
  requiresDeepSearch: boolean
}

export default function ExampleCards({ onSelect }: ExampleCardsProps) {
  const { general } = useSettingsStore()
  const examples = general.example_questions || []
  
  const iconSets = [
    [MessageSquare, Brain],
    [BarChart, TrendingUp],
    [Globe, Search],
    [Zap, Sparkles]
  ]
  
  // Check if a question might benefit from deep search
  const analyzeQuestion = (text: string): { requiresDeepSearch: boolean; keywords: string[] } => {
    const lowerText = text.toLowerCase()
    const foundKeywords = DEEP_SEARCH_KEYWORDS.filter(keyword => 
      lowerText.includes(keyword)
    )
    return {
      requiresDeepSearch: foundKeywords.length > 0,
      keywords: foundKeywords
    }
  }
  
  // Parse examples - support both string array and structured format
  const parseExamples = (): QuestionItem[] => {
    return examples.slice(0, 4).map(question => {
      if (typeof question === 'string') {
        const { requiresDeepSearch } = analyzeQuestion(question)
        return { text: question, requiresDeepSearch }
      }
      return { text: question, requiresDeepSearch: false }
    })
  }
  
  const questionItems = parseExamples()
  
  if (questionItems.length === 0) return null
  
  return (
    <div className="max-w-2xl mx-auto">
      <h3 className="text-xs font-medium text-muted-foreground mb-3 text-center uppercase tracking-wider">
        Try asking
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {questionItems.map((item, index) => {
          const [Icon1, Icon2] = iconSets[index % iconSets.length]
          const isDeepSearch = item.requiresDeepSearch
          
          return (
            <button
              key={index}
              onClick={() => onSelect(item.text, isDeepSearch)}
              className={`relative flex items-start gap-3 p-4 rounded-xl bg-background hover:shadow-md transition-all duration-300 text-left group border-2 ${
                isDeepSearch 
                  ? 'border-violet-200 dark:border-violet-800 hover:border-violet-400 dark:hover:border-violet-600' 
                  : 'border-transparent hover:border-accent'
              }`}
            >
              {/* Deep search indicator badge */}
              {isDeepSearch && (
                <div className="absolute -top-2 -right-2 flex items-center gap-1 px-2 py-0.5 bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 text-[10px] font-medium rounded-full shadow-sm">
                  <Sparkles size={10} className="animate-pulse" />
                  Deep search
                </div>
              )}
              
              {/* Icon */}
              <div className={`p-2 rounded-lg shrink-0 transition-colors ${
                isDeepSearch 
                  ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 group-hover:bg-violet-200 dark:group-hover:bg-violet-900/50' 
                  : 'bg-muted text-muted-foreground group-hover:bg-accent group-hover:text-foreground'
              }`}>
                {isDeepSearch ? <Icon2 size={18} /> : <Icon1 size={18} />}
              </div>
              
              {/* Question text */}
              <span className="text-sm leading-snug group-hover:text-foreground transition-colors">
                {item.text}
              </span>
              
              {/* Hover gradient effect */}
              <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none bg-gradient-to-r from-violet-500/5 to-blue-500/5 dark:from-violet-500/10 dark:to-blue-500/10" />
            </button>
          )
        })}
      </div>
      
      {/* Footer note */}
      <p className="text-[10px] text-muted-foreground/60 text-center mt-3">
        Questions marked with <Sparkles size={10} className="inline-block text-violet-500" /> benefit from deep research
      </p>
    </div>
  )
}
