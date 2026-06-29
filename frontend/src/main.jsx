import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Landing from './pages/Landing'
import { isAuthenticated, isGuest } from './api'
import './styles/tokens.css'

function Root() {
  const [showDashboard, setShowDashboard] = useState(
    isAuthenticated() || isGuest()
  )

  if (!showDashboard) {
    return <Landing onEnter={() => setShowDashboard(true)} />
  }

  return <App onLogout={() => {
    localStorage.removeItem('taggenie_token')
    localStorage.removeItem('taggenie_guest')
    setShowDashboard(false)
  }} />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
