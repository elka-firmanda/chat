import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import ChatHeader from './ChatHeader'
import SettingsModal from '../settings/SettingsModal'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { useChatStore } from '../../stores/chatStore'
import { cn } from '../../utils'

export default function Layout() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { sidebarOpen } = useChatStore()

  useKeyboardShortcuts()

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Fixed header buttons - top right */}
      <div className={cn(
        "fixed top-4 md:top-2 right-4 z-50 flex items-center gap-1.5 md:gap-2"
      )}>
        <Header />
      </div>

      <Sidebar />

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />

      <div className={cn(
        "flex-1 flex flex-col min-w-0 transition-[margin] duration-300 ease-in-out",
        sidebarOpen ? "md:ml-72" : "md:ml-0"
      )}>
        <ChatHeader />

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
