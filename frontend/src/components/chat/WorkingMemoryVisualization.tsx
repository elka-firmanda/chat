import { useState, useMemo } from 'react'
import * as Collapsible from '@radix-ui/react-collapsible'
import * as Dialog from '@radix-ui/react-dialog'
import { 
  ChevronDown, 
  ChevronRight, 
  Brain, 
  Clock, 
  Network, 
  X, 
  Filter,
  ZoomIn,
  Check
} from 'lucide-react'
import { WorkingMemory, WorkingMemoryNode, TimelineEntry } from '../../stores/chatStore'

interface WorkingMemoryVisualizationProps {
  memory: WorkingMemory
}

const agentColors = {
  master: 'text-agent-master',
  planner: 'text-agent-planner',
  researcher: 'text-agent-researcher',
  tools: 'text-agent-tools',
  database: 'text-agent-database'
}

const agentBgColors = {
  master: 'bg-agent-master/10 border-agent-master/30',
  planner: 'bg-agent-planner/10 border-agent-planner/30',
  researcher: 'bg-agent-researcher/10 border-agent-researcher/30',
  tools: 'bg-agent-tools/10 border-agent-tools/30',
  database: 'bg-agent-database/10 border-agent-database/30'
}

const agentBorderColors = {
  master: 'border-agent-master',
  planner: 'border-agent-planner',
  researcher: 'border-agent-researcher',
  tools: 'border-agent-tools',
  database: 'border-agent-database'
}

const agentLabels = {
  master: 'Master',
  planner: 'Planner',
  researcher: 'Researcher',
  tools: 'Tools',
  database: 'Database'
}

const statusIcons = {
  pending: '○',
  running: '◐',
  completed: '●',
  failed: '×'
}

function NodeDetailsDialog({ 
  node, 
  open, 
  onClose 
}: { 
  node: WorkingMemoryNode | null
  open: boolean
  onClose: () => void 
}) {
  if (!node) return null

  const agent = node.agent.toLowerCase() as keyof typeof agentColors

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-in fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background rounded-xl w-full max-w-md mx-4 p-6 z-50 animate-in zoom-in-95 shadow-xl">
          <Dialog.Title className="flex items-center gap-2 text-lg font-semibold mb-4">
            <Brain size={20} className={agentColors[agent] || 'text-muted-foreground'} />
            Node Details
          </Dialog.Title>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Agent</label>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs px-2 py-1 rounded ${agentBgColors[agent]} border`}>
                  {agentLabels[agent as keyof typeof agentLabels] || node.agent}
                </span>
                <span className="text-xs text-muted-foreground">
                  {statusIcons[node.status as keyof typeof statusIcons]} {node.status}
                </span>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Description</label>
              <p className="text-sm mt-1">{node.description}</p>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Node ID</label>
              <code className="text-xs bg-muted px-2 py-1 rounded mt-1 block w-full truncate">
                {node.id}
              </code>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Type</label>
              <p className="text-sm mt-1 capitalize">{node.node_type}</p>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Timestamp</label>
              <p className="text-sm mt-1 text-muted-foreground">
                {new Date(node.timestamp).toLocaleString()}
              </p>
            </div>

            {node.content && Object.keys(node.content).length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Content</label>
                <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-auto max-h-32">
                  {JSON.stringify(node.content, null, 2)}
                </pre>
              </div>
            )}
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute top-4 right-4 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-muted rounded-lg transition-colors"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function MemoryNode({ 
  node, 
  depth = 0, 
  onNodeClick,
  filteredAgents
}: { 
  node: WorkingMemoryNode; 
  depth?: number;
  onNodeClick: (node: WorkingMemoryNode) => void;
  filteredAgents: Set<string>;
}) {
  const [isOpen, setIsOpen] = useState(depth < 2) // Auto-expand first 2 levels
  const hasChildren = node.children && node.children.length > 0
  const isRunning = node.status === 'running'
  const isFailed = node.status === 'failed'
  const agent = node.agent.toLowerCase() as keyof typeof agentColors
  
  // Filter children based on agent selection
  const filteredChildren = useMemo(() => {
    if (!hasChildren) return []
    if (filteredAgents.size === 0) return node.children!
    return node.children!.filter(child => filteredAgents.has(child.agent.toLowerCase()))
  }, [node.children, hasChildren, filteredAgents])

  if (filteredAgents.size > 0 && !filteredAgents.has(agent)) {
    return null
  }

  return (
    <div className={`ml-4 ${depth > 0 ? 'border-l border-dashed border-muted-foreground/30 pl-2' : ''}`}>
      <Collapsible.Root open={isOpen}>
        <div 
          className={`flex items-center gap-1 py-1.5 px-1 rounded cursor-pointer transition-colors ${
            isRunning ? 'bg-primary/10' : 'hover:bg-muted/50'
          }`}
        >
          {filteredChildren.length > 0 ? (
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
            <span className="w-5 flex items-center justify-center">
              <span className={`text-xs ${isRunning ? 'animate-pulse text-primary' : 'text-muted-foreground'}`}>
                {statusIcons[node.status as keyof typeof statusIcons]}
              </span>
            </span>
          )}
          <span className={`text-xs px-1.5 py-0.5 rounded border ${agentBgColors[agent]} ${isRunning ? 'ring-1 ring-primary' : ''}`}>
            {agentLabels[agent as keyof typeof agentLabels] || node.agent}
          </span>
          <span className="text-sm text-foreground truncate flex-1">{node.description}</span>
          {isRunning && (
            <span className="w-2 h-2 bg-primary rounded-full animate-pulse ml-auto" />
          )}
          {isFailed && (
            <span className="w-2 h-2 bg-red-500 rounded-full ml-auto" title="Failed" />
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onNodeClick(node)
            }}
            className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-muted rounded ml-1"
            title="View details"
          >
            <ZoomIn size={12} className="text-muted-foreground" />
          </button>
        </div>
        <Collapsible.Content>
          {filteredChildren.length > 0 && (
            <div className="ml-2">
              {filteredChildren.map((child) => (
                <MemoryNode 
                  key={child.id} 
                  node={child} 
                  depth={depth + 1} 
                  onNodeClick={onNodeClick}
                  filteredAgents={filteredAgents}
                />
              ))}
            </div>
          )}
        </Collapsible.Content>
      </Collapsible.Root>
    </div>
  )
}

function TimelineItem({ 
  entry, 
  isLatest, 
  onClick 
}: { 
  entry: TimelineEntry; 
  isLatest: boolean;
  onClick: () => void;
}) {
  const agent = entry.agent.toLowerCase() as keyof typeof agentColors
  const isRunning = entry.status === 'running'
  const isFailed = entry.status === 'failed'

  return (
    <div 
      className={`flex items-start gap-2 py-1.5 px-2 rounded cursor-pointer transition-colors ${
        isLatest ? 'bg-primary/10 -mx-2 px-2' : 'hover:bg-muted/50'
      }`}
      onClick={onClick}
    >
      <span className={`text-xs px-1.5 py-0.5 rounded border ${agentBgColors[agent]}`}>
        {agentLabels[agent as keyof typeof agentLabels] || entry.agent}
      </span>
      <span className={`text-xs shrink-0 mt-0.5 font-mono ${isLatest ? 'text-primary' : 'text-muted-foreground'}`}>
        {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
      <span className="text-sm text-foreground truncate flex-1">{entry.description}</span>
      <span className={`text-xs ${isRunning ? 'animate-pulse text-primary' : isFailed ? 'text-red-500' : 'text-muted-foreground'}`}>
        {statusIcons[entry.status as keyof typeof statusIcons]}
      </span>
    </div>
  )
}

export default function WorkingMemoryVisualization({ memory }: WorkingMemoryVisualizationProps) {
  const [treeOpen, setTreeOpen] = useState(true)
  const [timelineOpen, setTimelineOpen] = useState(true)
  const [statsOpen, setStatsOpen] = useState(true)
  const [showVisualization, setShowVisualization] = useState(true)
  const [selectedNode, setSelectedNode] = useState<WorkingMemoryNode | null>(null)
  const [filterOpen, setFilterOpen] = useState(false)
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set())

  if (!memory.memory_tree && memory.timeline.length === 0) {
    return null
  }

  const sortedTimeline = [...memory.timeline].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  const allAgents = useMemo(() => {
    const agents = new Set<string>()
    if (memory.memory_tree) {
      const addAgent = (node: WorkingMemoryNode) => {
        agents.add(node.agent.toLowerCase())
        node.children?.forEach(addAgent)
      }
      addAgent(memory.memory_tree)
    }
    memory.timeline.forEach(entry => agents.add(entry.agent.toLowerCase()))
    return agents
  }, [memory])

  const toggleFilter = (agent: string) => {
    const newFilters = new Set(activeFilters)
    if (newFilters.has(agent)) {
      newFilters.delete(agent)
    } else {
      newFilters.add(agent)
    }
    setActiveFilters(newFilters)
  }

  const clearFilters = () => setActiveFilters(new Set())

  return (
    <>
      <div className="bg-muted/20 border-t px-3 py-2 space-y-2">
        {/* Header with toggle */}
        <div className="flex items-center justify-between">
          <Collapsible.Root open={statsOpen} onOpenChange={setStatsOpen}>
            <Collapsible.Trigger className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">
              <Network size={14} />
              <span>Working Memory</span>
              <span className="text-muted-foreground">
                ({memory.stats.total_nodes} nodes, {memory.stats.timeline_length} events)
              </span>
              {statsOpen ? (
                <ChevronDown size={14} />
              ) : (
                <ChevronRight size={14} />
              )}
            </Collapsible.Trigger>
          </Collapsible.Root>

          <div className="flex items-center gap-1">
            {/* Filter button */}
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`p-1.5 rounded hover:bg-muted transition-colors ${
                activeFilters.size > 0 ? 'text-primary' : 'text-muted-foreground'
              }`}
              title="Filter by agent"
            >
              <Filter size={14} />
              {activeFilters.size > 0 && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-primary text-primary-foreground text-[8px] rounded-full flex items-center justify-center">
                  {activeFilters.size}
                </span>
              )}
            </button>

            {/* Toggle visibility */}
            <button
              onClick={() => setShowVisualization(!showVisualization)}
              className="p-1.5 rounded hover:bg-muted text-muted-foreground transition-colors"
              title={showVisualization ? "Hide" : "Show"}
            >
              {showVisualization ? (
                <ChevronDown size={14} className="rotate-180" />
              ) : (
                <ChevronRight size={14} />
              )}
            </button>
          </div>
        </div>

        {/* Filter dropdown */}
        {filterOpen && (
          <div className="bg-background border rounded-lg p-3 space-y-2 animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">Filter by Agent</span>
              {activeFilters.size > 0 && (
                <button
                  onClick={clearFilters}
                  className="text-xs text-primary hover:underline"
                >
                  Clear all
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {Array.from(allAgents).map(agent => {
                const key = agent as keyof typeof agentBgColors
                const isActive = activeFilters.has(agent)
                return (
                  <button
                    key={agent}
                    onClick={() => toggleFilter(agent)}
                    className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded border transition-colors ${
                      isActive 
                        ? `${agentBgColors[key]} border-${agentBorderColors[key]}` 
                        : 'bg-muted/50 border-transparent'
                    }`}
                  >
                    {isActive && <Check size={10} />}
                    <span>{agentLabels[key] || agent}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Main content */}
        {showVisualization && (
          <div className="pl-6 animate-in fade-in slide-in-from-top-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
              {/* Tree View */}
              <Collapsible.Root open={treeOpen} onOpenChange={setTreeOpen}>
                <div className="space-y-1">
                  <Collapsible.Trigger className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground w-full p-1 rounded hover:bg-muted/50 transition-colors">
                    <Brain size={14} />
                    <span>Memory Tree</span>
                    {treeOpen ? (
                      <ChevronDown size={14} className="ml-auto" />
                    ) : (
                      <ChevronRight size={14} className="ml-auto" />
                    )}
                  </Collapsible.Trigger>
                  <Collapsible.Content>
                    <div className="max-h-48 overflow-auto pr-2 scrollbar-thin">
                      {memory.memory_tree ? (
                        <div className="group">
                          <MemoryNode 
                            node={memory.memory_tree} 
                            onNodeClick={setSelectedNode}
                            filteredAgents={activeFilters}
                          />
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground italic py-2">No tree data</p>
                      )}
                    </div>
                  </Collapsible.Content>
                </div>
              </Collapsible.Root>

              {/* Timeline View */}
              <Collapsible.Root open={timelineOpen} onOpenChange={setTimelineOpen}>
                <div className="space-y-1">
                  <Collapsible.Trigger className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground w-full p-1 rounded hover:bg-muted/50 transition-colors">
                    <Clock size={14} />
                    <span>Timeline</span>
                    {timelineOpen ? (
                      <ChevronDown size={14} className="ml-auto" />
                    ) : (
                      <ChevronRight size={14} className="ml-auto" />
                    )}
                  </Collapsible.Trigger>
                  <Collapsible.Content>
                    <div className="max-h-48 overflow-auto pr-2 scrollbar-thin">
                      {sortedTimeline.length > 0 ? (
                        sortedTimeline.map((entry, idx) => (
                          <TimelineItem
                            key={`${entry.node_id}-${entry.timestamp}`}
                            entry={entry}
                            isLatest={idx === 0}
                            onClick={() => {
                              // Could navigate to or highlight the node
                              console.log('Timeline item clicked:', entry)
                            }}
                          />
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground italic py-2">No timeline events</p>
                      )}
                    </div>
                  </Collapsible.Content>
                </div>
              </Collapsible.Root>
            </div>
          </div>
        )}
      </div>

      {/* Node details dialog */}
      <NodeDetailsDialog
        node={selectedNode}
        open={!!selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </>
  )
}
