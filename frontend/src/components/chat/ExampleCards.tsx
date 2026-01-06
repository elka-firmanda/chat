import { useEffect, useMemo } from 'react'
import { Search, Code, Database, Cloud } from 'lucide-react'
import { useSettingsStore } from '../../stores/settingsStore'

interface ExampleCardsProps {
  onSelect: (question: string, requiresDeepSearch?: boolean) => void
}

// Default example questions for fallback
const defaultExamples = [
  {
    icon: Search,
    title: "Research AI developments",
    description: "What are the latest AI breakthroughs?",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
  },
  {
    icon: Code,
    title: "Compare technologies",
    description: "Compare Python vs JavaScript for web development",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
  },
  {
    icon: Database,
    title: "Best practices",
    description: "What are best practices for database design?",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
  },
  {
    icon: Cloud,
    title: "Industry trends",
    description: "What are the current trends in cloud computing?",
    color: "text-orange-500",
    bgColor: "bg-orange-500/10",
  },
]

// Map example questions to card format
function mapQuestionToCard(question: string, index: number) {
  // Use default examples for matching, or generate from question
  if (index < defaultExamples.length) {
    return defaultExamples[index]
  }
  
  // Generate a card from the question
  const title = question.length > 50 ? question.substring(0, 47) + '...' : question
  const icons = [Search, Code, Database, Cloud]
  const colors = [
    { color: "text-blue-500", bgColor: "bg-blue-500/10" },
    { color: "text-green-500", bgColor: "bg-green-500/10" },
    { color: "text-purple-500", bgColor: "bg-purple-500/10" },
    { color: "text-orange-500", bgColor: "bg-orange-500/10" },
  ]
  
  const iconIndex = index % icons.length
  const colorIndex = index % colors.length
  
  return {
    icon: icons[iconIndex],
    title: title,
    description: question,
    color: colors[colorIndex].color,
    bgColor: colors[colorIndex].bgColor,
  }
}

export default function ExampleCards({ onSelect }: ExampleCardsProps) {
  const { general, loadConfig, isLoading } = useSettingsStore()
  
  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [loadConfig])
  
  // Get example questions from config or use defaults
  const examples = useMemo(() => {
    const questions = general.example_questions && general.example_questions.length > 0
      ? general.example_questions
      : defaultExamples.map(ex => ex.description)
    
    return questions.map((question, index) => mapQuestionToCard(question, index))
  }, [general.example_questions])
  
  const handleClick = (query: string) => {
    onSelect(query, true)
  }
  
  // Show loading state briefly
  if (isLoading && general.example_questions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="animate-pulse text-muted-foreground">Loading examples...</div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-2">Welcome to Agentic Chat</h2>
        <p className="text-muted-foreground">
          Ask anything or try one of these examples with Deep Search
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl w-full">
        {examples.map((example, index) => {
          const Icon = example.icon
          return (
            <button
              key={index}
              onClick={() => handleClick(example.description)}
              className="flex items-start gap-4 p-4 rounded-xl border border-border bg-background hover:bg-muted/50 transition-colors text-left group"
            >
              <div className={`p-2.5 rounded-lg ${example.bgColor}`}>
                <Icon className={`w-5 h-5 ${example.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium mb-1 group-hover:text-primary transition-colors">
                  {example.title}
                </h3>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {example.description}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      <p className="text-sm text-muted-foreground mt-8">
        Enable <span className="font-medium text-primary">Deep Search</span> for
        comprehensive research with multiple agents
      </p>
    </div>
  )
}
