import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import SidebarDrawer from './SidebarDrawer'
import Header from './Header'
import { useChatStore } from '../../stores/chatStore'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useKeyboardShortcuts()

  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="hidden xl:flex w-64 bg-secondary/50 flex-col border-r shrink-0">
        <div className="flex-1 flex flex-col">
        </div>
      </aside>

      <SidebarDrawer
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={() => {
          useChatStore.getState().setActiveSession(null)
        }}
      />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="xl:hidden h-14 border-b flex items-center px-3 sm:px-4 gap-2 bg-background shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="min-h-[44px] min-w-[44px] -ml-2 flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <div className="flex-1" />
          <Header />
        </header>

        <header className="hidden xl:flex h-14 border-b items-center justify-end px-4 gap-2 bg-background shrink-0">
          <Header />
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
