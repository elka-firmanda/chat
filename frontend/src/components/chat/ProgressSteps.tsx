import { useState, useEffect, useRef } from 'react'
import { CheckCircle, Circle, AlertCircle, Loader2 } from 'lucide-react'
import * as Collapsible from '@radix-ui/react-collapsible'
import { PlanStep } from '../../stores/chatStore'
import { ChevronDown } from 'lucide-react'

interface ProgressStepsProps {
  steps: PlanStep[]
  onToggleLogs?: (stepIndex: number) => void
}

export default function ProgressSteps({ steps, onToggleLogs }: ProgressStepsProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  const activeStepRef = useRef<HTMLDivElement>(null)
  
  if (steps.length === 0) return null
  
  const allCompleted = steps.every(step => step.status === 'completed' || step.status === 'failed')
  const runningStepIndex = steps.findIndex(step => step.status === 'in_progress')

  useEffect(() => {
    if (runningStepIndex >= 0 && activeStepRef.current) {
      activeStepRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [runningStepIndex])

  const toggleStep = (stepIndex: number) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepIndex)) {
      newExpanded.delete(stepIndex)
    } else {
      newExpanded.add(stepIndex)
    }
    setExpandedSteps(newExpanded)
    onToggleLogs?.(stepIndex)
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500 shrink-0" size={18} />
      case 'in_progress':
        return <Loader2 className="text-primary animate-spin shrink-0" size={18} />
      case 'failed':
        return <AlertCircle className="text-red-500 shrink-0" size={18} />
      default:
        return <Circle className="text-muted-foreground shrink-0" size={18} />
    }
  }
  
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return '✓ Completed'
      case 'in_progress':
        return '⟳ Running...'
      case 'failed':
        return '✗ Failed'
      default:
        return '○ Pending'
    }
  }
  
  if (allCompleted && steps.length > 0) {
    return null
  }
  
  return (
    <div className="bg-muted/50 rounded-xl p-3 md:p-4 mx-2 md:mx-4 mb-3 border border-border">
      <h3 className="text-sm font-medium mb-3 flex items-center gap-2 text-foreground">
        <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
        {runningStepIndex >= 0 ? 'Processing...' : 'Planning steps'}
      </h3>
      <div className="space-y-1">
        {steps.map((step, index) => {
          const isRunning = step.status === 'in_progress'
          const isActiveRef = isRunning ? { ref: activeStepRef } : {}
          
          return (
            <div 
              key={index} 
              className={`transition-all duration-300 ${
                isRunning ? 'bg-primary/10 -mx-2 px-2 py-1 rounded-lg' : ''
              }`}
              {...isActiveRef}
            >
              <Collapsible.Root 
                open={expandedSteps.has(index)}
                onOpenChange={() => toggleStep(index)}
              >
                <Collapsible.Trigger className="w-full flex items-start gap-2 text-left p-1 rounded hover:bg-muted/50 transition-colors">
                  <div className="mt-0.5">
                    {getStatusIcon(step.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-sm truncate ${
                        step.status === 'completed' 
                          ? 'text-muted-foreground line-through' 
                          : step.status === 'failed'
                          ? 'text-red-500'
                          : 'text-foreground'
                      }`}>
                        {step.step_number}. {step.description}
                      </p>
                      {step.result && (
                        <ChevronDown 
                          size={14} 
                          className={`shrink-0 transition-transform duration-200 ${
                            expandedSteps.has(index) ? 'rotate-180' : ''
                          }`}
                        />
                      )}
                    </div>
                    <span className={`text-xs ${
                      step.status === 'completed' 
                        ? 'text-green-500' 
                        : step.status === 'failed'
                        ? 'text-red-500'
                        : step.status === 'in_progress'
                        ? 'text-primary'
                        : 'text-muted-foreground'
                    }`}>
                      {getStatusLabel(step.status)}
                    </span>
                  </div>
                </Collapsible.Trigger>
                
                <Collapsible.Content>
                  {step.result && (
                    <div className="ml-7 mt-1 animate-in slide-in-from-top-2 duration-200">
                      <p className="text-xs text-muted-foreground">
                        Result: {step.result}
                      </p>
                    </div>
                  )}
                  {step.error && (
                    <div className="ml-7 mt-1">
                      <p className="text-xs text-red-500">
                        Error: {step.error}
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
