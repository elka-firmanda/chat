import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import SettingsModal from './components/settings/SettingsModal'
import ChatContainer from './components/chat/ChatContainer'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatContainer />} />
          <Route path="settings" element={<SettingsModal />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
