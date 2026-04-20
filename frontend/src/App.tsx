import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Welcome from './pages/Welcome'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Home from './pages/home/index'
import Library from './pages/library'
import Progress from './pages/Progress'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes -- no auth required */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected routes */}
        <Route path="/" element={<ProtectedRoute><Welcome /></ProtectedRoute>} />
        <Route path="/home/*" element={<ProtectedRoute><Layout><Home /></Layout></ProtectedRoute>} />
        <Route path="/library/*" element={<ProtectedRoute><Layout><Library /></Layout></ProtectedRoute>} />
        <Route path="/progress" element={<ProtectedRoute><Layout><Progress /></Layout></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
      </Routes>
    </Router>
  )
}

export default App

