import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Layout from './components/layout/Layout'
import ChatContainer from './components/chat/ChatContainer'
import ToastContainer from './components/ui/Toast'
import LoginScreen from './components/auth/LoginScreen'
import { useChatStore } from './stores/chatStore'
import { useEffect } from 'react'

const SettingsModal = lazy(() => import('./components/settings/SettingsModal'))

function AppContent() {
  const { chatAuthRequired, isChatAuthenticated, checkChatAuth } = useChatStore()

  useEffect(() => {
    checkChatAuth()
  }, [checkChatAuth])

  // Show loading while checking auth
  if (chatAuthRequired === null) {
    return null
  }

  // Show login screen if auth is required and not authenticated
  if (chatAuthRequired && !isChatAuthenticated) {
    return <LoginScreen />
  }

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<ChatContainer />} />
        <Route
          path="settings"
          element={
            <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
              <SettingsModal open={true} onOpenChange={() => {}} />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <AppContent />
    </BrowserRouter>
  )
}

export default App
