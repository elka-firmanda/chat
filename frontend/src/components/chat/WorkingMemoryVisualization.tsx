import { useState } from 'react'
import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown, ChevronRight, Brain, Clock, Network } from 'lucide-react'
import { WorkingMemory, WorkingMemoryNode, TimelineEntry } from '../../stores/chatStore'

interface WorkingMemoryVisualizationProps {
  memory: WorkingMemory
}

const agentColors = {
  master: 'text-[#8b5cf6]',
  planner: 'text-[#3b82f6]',
  researcher: 'text-[#22c55e]',
  tools: 'text-[#f97316]',
  database: 'text-[#ec4899]'
}

const agentBgColors = {
  master: 'bg-[#8b5cf6]/10',
  planner: 'bg-[#3b82f6]/10',
  researcher: 'bg-[#22c55e]/10',
  tools: 'bg-[#f97316]/10',
  database: 'bg-[#ec4899]/10'
}

const agentLabels = {
  master: 'Master',
  planner: 'Planner',
  researcher: 'Researcher',
  tools: 'Tools',
  database: 'Database'
}

function MemoryNode({ node, depth = 0 }: { node: WorkingMemoryNode; depth?: number }) {
  const [isOpen, setIsOpen] = useState(false)
  const hasChildren = node.children && node.children.length > 0
  const isRunning = node.status === 'running'
  const agent = node.agent.toLowerCase() as keyof typeof agentColors

  return (
    <div className={`ml-4 ${depth > 0 ? 'border-l border-dashed border-muted-foreground/30 pl-2' : ''}`}>
      <Collapsible.Root open={isOpen}>
        <div className="flex items-center gap-1 py-1">
          {hasChildren ? (
            <Collapsible.Trigger
              onClick={() => setIsOpen(!isOpen)}
              className="p-0.5 hover:bg-muted rounded cursor-pointer"
            >
              {isOpen ? (
                <ChevronDown size={14} className="text-muted-foreground" />
              ) : (
                <ChevronRight size={14} className="text-muted-foreground" />
              )}
            </Collapsible.Trigger>
          ) : (
            <span className="w-5" />
          )}
          <span className={`text-xs px-1.5 py-0.5 rounded ${agentBgColors[agent] || 'bg-muted'} ${agentColors[agent] || 'text-muted-foreground'}`}>
            {agentLabels[agent as keyof typeof agentLabels] || node.agent}
          </span>
          <span className="text-sm text-foreground truncate">{node.description}</span>
          {isRunning && (
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse ml-auto" />
          )}
        </div>
        <Collapsible.Content>
          {hasChildren && (
            <div className="ml-2">
              {node.children!.map((child) => (
                <MemoryNode key={child.id} node={child} depth={depth + 1} />
              ))}
            </div>
          )}
        </Collapsible.Content>
      </Collapsible.Root>
    </div>
  )
}

function TimelineItem({ entry, isLatest }: { entry: TimelineEntry; isLatest: boolean }) {
  const agent = entry.agent.toLowerCase() as keyof typeof agentColors
  const isRunning = entry.status === 'running'

  return (
    <div className={`flex items-start gap-2 py-1.5 ${isLatest ? 'bg-blue-500/5 -mx-2 px-2 rounded' : ''}`}>
      <span className={`text-xs px-1.5 py-0.5 rounded ${agentBgColors[agent] || 'bg-muted'} ${agentColors[agent] || 'text-muted-foreground'}`}>
        {agentLabels[agent as keyof typeof agentLabels] || entry.agent}
      </span>
      <span className="text-xs text-muted-foreground shrink-0 mt-0.5">
        {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
      <span className="text-sm text-foreground truncate flex-1">{entry.description}</span>
      {isRunning && (
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse shrink-0 mt-1.5" />
      )}
    </div>
  )
}

export default function WorkingMemoryVisualization({ memory }: WorkingMemoryVisualizationProps) {
  const [treeOpen, setTreeOpen] = useState(true)
  const [timelineOpen, setTimelineOpen] = useState(true)
  const [statsOpen, setStatsOpen] = useState(true)

  if (!memory.memory_tree && memory.timeline.length === 0) {
    return null
  }

  const sortedTimeline = [...memory.timeline].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  return (
    <div className="bg-muted/30 border-t px-3 py-2 space-y-2">
      <Collapsible.Root open={statsOpen} onOpenChange={setStatsOpen}>
        <Collapsible.Trigger className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground w-full">
          <Network size={14} />
          <span>Working Memory</span>
          <span className="text-muted-foreground">
            ({memory.stats.total_nodes} nodes, {memory.stats.timeline_length} events)
          </span>
          {statsOpen ? (
            <ChevronDown size={14} className="ml-auto" />
          ) : (
            <ChevronRight size={14} className="ml-auto" />
          )}
        </Collapsible.Trigger>
        <Collapsible.Content>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 pl-6">
            <Collapsible.Root open={treeOpen} onOpenChange={setTreeOpen}>
              <div className="space-y-1">
                <Collapsible.Trigger className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground w-full">
                  <Brain size={14} />
                  <span>Memory Tree</span>
                  {treeOpen ? (
                    <ChevronDown size={14} className="ml-auto" />
                  ) : (
                    <ChevronRight size={14} className="ml-auto" />
                  )}
                </Collapsible.Trigger>
                <Collapsible.Content>
                  <div className="max-h-48 overflow-auto pr-2">
                    {memory.memory_tree ? (
                      <MemoryNode node={memory.memory_tree} />
                    ) : (
                      <p className="text-xs text-muted-foreground italic">No tree data</p>
                    )}
                  </div>
                </Collapsible.Content>
              </div>
            </Collapsible.Root>
            <Collapsible.Root open={timelineOpen} onOpenChange={setTimelineOpen}>
              <div className="space-y-1">
                <Collapsible.Trigger className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground w-full">
                  <Clock size={14} />
                  <span>Timeline</span>
                  {timelineOpen ? (
                    <ChevronDown size={14} className="ml-auto" />
                  ) : (
                    <ChevronRight size={14} className="ml-auto" />
                  )}
                </Collapsible.Trigger>
                <Collapsible.Content>
                  <div className="max-h-48 overflow-auto pr-2">
                    {sortedTimeline.length > 0 ? (
                      sortedTimeline.map((entry, idx) => (
                        <TimelineItem
                          key={`${entry.node_id}-${entry.timestamp}`}
                          entry={entry}
                          isLatest={idx === 0}
                        />
                      ))
                    ) : (
                      <p className="text-xs text-muted-foreground italic">No timeline events</p>
                    )}
                  </div>
                </Collapsible.Content>
              </div>
            </Collapsible.Root>
          </div>
        </Collapsible.Content>
      </Collapsible.Root>
    </div>
  )
}
