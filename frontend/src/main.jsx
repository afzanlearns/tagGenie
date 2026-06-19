import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Landing from './pages/Landing'
import './styles/tokens.css'

function Root() {
  const [showDashboard, setShowDashboard] = useState(
    !!localStorage.getItem('taggenie_token')
  )

  if (!showDashboard) {
    return <Landing onEnter={() => setShowDashboard(true)} />
  }

  return <App onLogout={() => {
    localStorage.removeItem('taggenie_token')
    setShowDashboard(false)
  }} />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
