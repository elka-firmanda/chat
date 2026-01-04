import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface ThinkingBlockProps {
  agent: 'master' | 'planner' | 'researcher' | 'tools' | 'database'
  content: string
  defaultCollapsed?: boolean
}

const agentColors = {
  master: 'border-l-agent-master',
  planner: 'border-l-agent-planner',
  researcher: 'border-l-agent-researcher',
  tools: 'border-l-agent-tools',
  database: 'border-l-agent-database'
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
    <div className={`border-l-4 ${agentColors[agent]} pl-4 my-2 rounded-r`}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        {collapsed ? (
          <ChevronRight size={16} />
        ) : (
          <ChevronDown size={16} />
        )}
        <span>{agentLabels[agent]} thinking</span>
      </button>
      
      {!collapsed && (
        <div className="mt-2 text-sm text-muted-foreground animate-in fade-in">
          {content}
        </div>
      )}
    </div>
  )
}
