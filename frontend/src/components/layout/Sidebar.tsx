import { useState } from 'react'
import { MessageSquare, Plus, Archive, Settings } from 'lucide-react'

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <aside className={`${isCollapsed ? 'w-16' : 'w-64'} bg-secondary flex flex-col transition-all duration-300`}>
      {/* New Chat Button */}
      <div className="p-4 border-b">
        <button 
          className="w-full flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <Plus size={18} />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          {/* Placeholder sessions */}
          <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors text-left">
            <MessageSquare size={16} />
            {!isCollapsed && <span className="truncate">AI Research Discussion</span>}
          </button>
          <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors text-left">
            <MessageSquare size={16} />
            {!isCollapsed && <span className="truncate">Data Analysis Q4</span>}
          </button>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="p-2 border-t">
        <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors">
          <Archive size={16} />
          {!isCollapsed && <span>Archived</span>}
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-accent transition-colors">
          <Settings size={16} />
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>

      {/* Collapse Toggle */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute top-1/2 -right-3 transform -translate-y-1/2 bg-background border rounded-full p-1 shadow-md"
      >
        {isCollapsed ? '→' : '←'}
      </button>
    </aside>
  )
}
