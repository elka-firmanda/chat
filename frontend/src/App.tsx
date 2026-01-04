import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import Layout from './components/layout/Layout'
import SettingsModal from './components/settings/SettingsModal'
import ChatContainer from './components/chat/ChatContainer'

function App() {
  const { theme } = useTheme()

  return (
    <div className={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<ChatContainer />} />
            <Route path="settings" element={<SettingsModal />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  )
}

export default App
