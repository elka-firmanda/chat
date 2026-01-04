import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, Circle, AlertCircle } from 'lucide-react'
import { AgentStep } from '../../stores/chatStore'

interface ProgressStepsProps {
  steps: AgentStep[]
  onToggleLogs?: (stepId: string) => void
}

export default function ProgressSteps({ steps, onToggleLogs }: ProgressStepsProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  
  if (steps.length === 0) return null
  
  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500 shrink-0" size={18} />
      case 'running':
        return <Circle className="text-blue-500 animate-pulse shrink-0" size={18} />
      case 'failed':
        return <AlertCircle className="text-red-500 shrink-0" size={18} />
      default:
        return <Circle className="text-gray-400 shrink-0" size={18} />
    }
  }
  
  return (
    <div className="bg-muted/50 rounded-xl p-3 md:p-4 mx-2 md:mx-4 mb-3">
      <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        Processing...
      </h3>
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-2">
            {getStatusIcon(step.status)}
            <div className="flex-1 min-w-0">
              <button
                onClick={() => step.logs && toggleStep(step.id)}
                className="w-full flex items-center justify-between text-left"
                disabled={!step.logs}
              >
                <p className="text-sm truncate">{step.description}</p>
                {step.logs && (
                  expandedSteps.has(step.id) 
                    ? <ChevronDown size={14} className="shrink-0" />
                    : <ChevronRight size={14} className="shrink-0" />
                )}
              </button>
              
              {expandedSteps.has(step.id) && step.logs && (
                <pre className="mt-2 p-2 bg-background rounded text-xs overflow-x-auto whitespace-pre-wrap">
                  {step.logs}
                </pre>
              )}
              
              {step.result && (
                <p className="text-xs text-muted-foreground mt-1">
                  Result: {step.result}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
