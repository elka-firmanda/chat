import { useState } from 'react'
import { MessageSquare, Plus, Archive, Settings, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <aside className={`${isCollapsed ? 'w-16' : 'w-64'} bg-secondary flex flex-col transition-all duration-300 h-full`}>
      <div className="p-3 sm:p-4 border-b">
        <button 
          className="w-full flex items-center justify-center sm:justify-start gap-2 px-3 py-2.5 min-h-[44px] bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium touch-manipulation"
        >
          <Plus size={18} />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          <button className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors text-left touch-manipulation">
            <MessageSquare size={16} />
            {!isCollapsed && <span className="truncate">AI Research Discussion</span>}
          </button>
          <button className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors text-left touch-manipulation">
            <MessageSquare size={16} />
            {!isCollapsed && <span className="truncate">Data Analysis Q4</span>}
          </button>
        </div>
      </div>

      <div className="p-2 border-t">
        <button className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors touch-manipulation">
          <Archive size={16} />
          {!isCollapsed && <span>Archived</span>}
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2.5 min-h-[44px] text-sm rounded-lg hover:bg-accent transition-colors touch-manipulation">
          <Settings size={16} />
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>

      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="hidden xl:flex absolute top-1/2 right-0 translate-x-1/2 -translate-y-1/2 min-h-[32px] min-w-[32px] items-center justify-center bg-background border rounded-full shadow-md hover:bg-accent transition-colors z-10"
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  )
}
