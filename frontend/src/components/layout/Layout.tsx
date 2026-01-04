import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import SidebarDrawer from './SidebarDrawer'
import Header from './Header'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-background">
      {/* Desktop Sidebar - hidden on mobile */}
      <aside className="hidden lg:flex w-64 bg-secondary flex-col border-r">
        {/* Sidebar content - we'll reuse existing Sidebar component */}
        <div className="flex-1 flex flex-col">
          <Outlet />
        </div>
      </aside>

      {/* Mobile Drawer */}
      <SidebarDrawer
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={() => {
          useChatStore.getState().setActiveSession(null)
        }}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="lg:hidden h-14 border-b flex items-center px-4 gap-2">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-accent rounded-lg"
          >
            <Menu size={20} />
          </button>
          <div className="flex-1" />
          <Header />
          <style>{`
            @keyframes slide-in-left {
              from { transform: translateX(-100%); }
              to { transform: translateX(0); }
            }
            .animate-in {
              animation: slide-in-left 0.3s ease-out;
            }
          `}</style>
        </header>

        {/* Desktop Header - hidden on mobile */}
        <header className="hidden lg:flex h-14 border-b items-center justify-end px-4 gap-2">
          <Header />
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
