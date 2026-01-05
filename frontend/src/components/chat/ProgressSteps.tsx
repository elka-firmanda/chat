import { useState, useEffect, useRef } from 'react'
import { CheckCircle, Circle, AlertCircle, Loader2 } from 'lucide-react'
import * as Collapsible from '@radix-ui/react-collapsible'
import { AgentStep } from '../../stores/chatStore'
import { ChevronDown } from 'lucide-react'

interface ProgressStepsProps {
  steps: AgentStep[]
  onToggleLogs?: (stepId: string) => void
}

export default function ProgressSteps({ steps, onToggleLogs }: ProgressStepsProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const activeStepRef = useRef<HTMLDivElement>(null)
  
  if (steps.length === 0) return null
  
  // Check if all steps are complete
  const allCompleted = steps.every(step => step.status === 'completed' || step.status === 'failed')
  
  // Find the currently running step for auto-scroll
  const runningStepId = steps.find(step => step.status === 'running')?.id

  // Auto-scroll to running step
  useEffect(() => {
    if (runningStepId && activeStepRef.current) {
      activeStepRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [runningStepId])

  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
    onToggleLogs?.(stepId)
  }
  
  const getStatusIcon = (status: string, stepId: string) => {
    const isExpanded = expandedSteps.has(stepId)
    
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500 shrink-0" size={18} />
      case 'running':
        return isExpanded ? (
          <Loader2 className="text-blue-500 animate-spin shrink-0" size={18} />
        ) : (
          <Loader2 className="text-blue-500 animate-spin shrink-0" size={18} />
        )
      case 'failed':
        return <AlertCircle className="text-red-500 shrink-0" size={18} />
      default:
        return <Circle className="text-gray-400 dark:text-gray-500 shrink-0" size={18} />
    }
  }
  
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return '✓ Completed'
      case 'running':
        return '⟳ Running...'
      case 'failed':
        return '✗ Failed'
      default:
        return '○ Pending'
    }
  }
  
  // Don't render if all steps are complete (hide when done)
  if (allCompleted && steps.length > 0) {
    return null
  }
  
  return (
    <div className="bg-muted/50 dark:bg-muted/20 rounded-xl p-3 md:p-4 mx-2 md:mx-4 mb-3 border border-muted-foreground/20">
      <h3 className="text-sm font-medium mb-3 flex items-center gap-2 text-foreground">
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        {runningStepId ? 'Processing...' : 'Planning steps'}
      </h3>
      <div className="space-y-1">
        {steps.map((step, index) => {
          const isRunning = step.status === 'running'
          const isActiveRef = isRunning ? { ref: activeStepRef } : {}
          
          return (
            <div 
              key={step.id} 
              className={`transition-all duration-300 ${
                isRunning ? 'bg-blue-500/10 dark:bg-blue-500/20 -mx-2 px-2 py-1 rounded-lg' : ''
              }`}
              {...isActiveRef}
            >
              <Collapsible.Root 
                open={expandedSteps.has(step.id)}
                onOpenChange={() => toggleStep(step.id)}
              >
                <Collapsible.Trigger className="w-full flex items-start gap-2 text-left p-1 rounded hover:bg-muted/50 dark:hover:bg-muted/30 transition-colors">
                  <div className="mt-0.5">
                    {getStatusIcon(step.status, step.id)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-sm truncate ${
                        step.status === 'completed' 
                          ? 'text-muted-foreground line-through' 
                          : step.status === 'failed'
                          ? 'text-red-500 dark:text-red-400'
                          : 'text-foreground'
                      }`}>
                        {index + 1}. {step.description}
                      </p>
                      {step.logs && (
                        <ChevronDown 
                          size={14} 
                          className={`shrink-0 transition-transform duration-200 ${
                            expandedSteps.has(step.id) ? 'rotate-180' : ''
                          }`}
                        />
                      )}
                    </div>
                    <span className={`text-xs ${
                      step.status === 'completed' 
                        ? 'text-green-500 dark:text-green-400' 
                        : step.status === 'failed'
                        ? 'text-red-500 dark:text-red-400'
                        : step.status === 'running'
                        ? 'text-blue-500 dark:text-blue-400'
                        : 'text-muted-foreground'
                    }`}>
                      {getStatusLabel(step.status)}
                    </span>
                  </div>
                </Collapsible.Trigger>
                
                <Collapsible.Content>
                  {step.logs && (
                    <div className="ml-7 mt-1 animate-in slide-in-from-top-2 duration-200">
                      <pre className="p-3 bg-background dark:bg-background/50 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap text-muted-foreground border border-border">
                        {step.logs}
                      </pre>
                    </div>
                  )}
                  {step.result && (
                    <div className="ml-7 mt-1">
                      <p className="text-xs text-muted-foreground">
                        Result: {step.result}
                      </p>
                    </div>
                  )}
                </Collapsible.Content>
              </Collapsible.Root>
            </div>
          )
        })}
      </div>
    </div>
  )
}
