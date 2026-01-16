import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Welcome from './pages/Welcome'
import Home from './pages/Home'
import Practice from './pages/Practice'
import Progress from './pages/Progress'
import Vocabulary from './pages/Vocabulary'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <Routes>
        {/* Welcome page without Layout (no sidebar) */}
        <Route path="/" element={<Welcome />} />

        {/* Practice page without Layout (has its own sidebar) */}
        <Route path="/practice" element={<Practice />} />

        {/* Pages with Layout (with sidebar) */}
        <Route path="/home" element={<Layout><Home /></Layout>} />
        <Route path="/progress" element={<Layout><Progress /></Layout>} />
        <Route path="/vocabulary" element={<Layout><Vocabulary /></Layout>} />
        <Route path="/settings" element={<Layout><Settings /></Layout>} />
      </Routes>
    </Router>
  )
}

export default App

