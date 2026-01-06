import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Layout from './components/layout/Layout'
import ChatContainer from './components/chat/ChatContainer'
import ToastContainer from './components/ui/Toast'

const SettingsModal = lazy(() => import('./components/settings/SettingsModal'))

function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
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
