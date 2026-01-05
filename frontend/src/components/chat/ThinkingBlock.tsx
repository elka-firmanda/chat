import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import * as Collapsible from '@radix-ui/react-collapsible'
import MarkdownRenderer from './MarkdownRenderer'

interface ThinkingBlockProps {
  agent: 'master' | 'planner' | 'researcher' | 'tools' | 'database'
  content: string
  defaultCollapsed?: boolean
}

const agentColors = {
  master: 'border-l-[#8b5cf6]',
  planner: 'border-l-[#3b82f6]',
  researcher: 'border-l-[#22c55e]',
  tools: 'border-l-[#f97316]',
  database: 'border-l-[#ec4899]'
}

const agentLabels = {
  master: 'Master',
  planner: 'Planner',
  researcher: 'Researcher',
  tools: 'Tools',
  database: 'Database'
}

export default function ThinkingBlock({ 
  agent, 
  content, 
  defaultCollapsed = false 
}: ThinkingBlockProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  
  return (
    <Collapsible.Root 
      open={!collapsed} 
      onOpenChange={setCollapsed}
      className={`border-l-4 ${agentColors[agent]} pl-3 sm:pl-4 my-2 rounded-r bg-muted/50`}
    >
      <Collapsible.Trigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full min-h-[44px] px-2 -mx-2 rounded touch-manipulation">
        {collapsed ? (
          <ChevronRight size={16} className="transition-transform shrink-0" />
        ) : (
          <ChevronDown size={16} className="transition-transform shrink-0" />
        )}
        <span>{agentLabels[agent]} thinking</span>
      </Collapsible.Trigger>
      
      <Collapsible.Content>
        <div className="mt-2 text-sm animate-in fade-in">
          <MarkdownRenderer content={content} />
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  )
}
