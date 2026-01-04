import { useSettingsStore } from '../../stores/settingsStore'
import { MessageSquare, BarChart, Brain, Sparkles } from 'lucide-react'

interface ExampleCardsProps {
  onSelect: (question: string) => void
}

export default function ExampleCards({ onSelect }: ExampleCardsProps) {
  const { general } = useSettingsStore()
  const examples = general.example_questions || []
  
  const icons = [
    MessageSquare,
    Brain,
    BarChart,
    Sparkles
  ]
  
  if (examples.length === 0) return null
  
  return (
    <div className="max-w-2xl mx-auto">
      <h3 className="text-xs font-medium text-muted-foreground mb-3 text-center uppercase tracking-wider">
        Example questions
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {examples.slice(0, 4).map((question, index) => {
          const Icon = icons[index % icons.length]
          return (
            <button
              key={index}
              onClick={() => onSelect(question)}
              className="flex items-start gap-3 p-3.5 rounded-xl bg-background hover:bg-accent hover:shadow-sm transition-all duration-200 text-left group border border-transparent hover:border-accent"
            >
              <Icon size={18} className="mt-0.5 text-muted-foreground group-hover:text-foreground shrink-0" />
              <span className="text-sm leading-snug">{question}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
