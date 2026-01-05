import { BrowserRouter, Routes, Route, lazy, Suspense } from 'react-router-dom'
import Layout from './components/layout/Layout'
import ChatContainer from './components/chat/ChatContainer'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'

const SettingsModal = lazy(() => import('./components/settings/SettingsModal'))

function App() {
  // Initialize keyboard shortcuts
  useKeyboardShortcuts()

  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}

export default App
