import React, { useState, useEffect } from 'react'
import './index.css'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { ProjectDetail } from './pages/ProjectDetail'
import { AssetLibrary } from './pages/AssetLibrary'

type Page = 'login' | 'dashboard' | 'project' | 'assets'

interface User {
  id: number
  email: string
}

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [user, setUser] = useState<User | null>(null)
  const [currentPage, setCurrentPage] = useState<Page>('login')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)

  // Verify token on mount
  useEffect(() => {
    if (token) {
      verifyToken()
    }
  }, [token])

  const verifyToken = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setUser(data)
        setCurrentPage('dashboard')
      } else {
        setToken(null)
        localStorage.removeItem('token')
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      setToken(null)
      localStorage.removeItem('token')
    }
  }

  const handleLogin = (newToken: string) => {
    setToken(newToken)
    localStorage.setItem('token', newToken)
  }

  const handleLogout = () => {
    setToken(null)
    localStorage.removeItem('token')
    setUser(null)
    setCurrentPage('login')
  }

  const handleSelectProject = (projectId: number) => {
    setSelectedProjectId(projectId)
    setCurrentPage('project')
  }

  const handleBackToDashboard = () => {
    setCurrentPage('dashboard')
    setSelectedProjectId(null)
  }

  if (!token || !user) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="nav-left">
          <h1 className="logo">🎬 Yetrix Maritime AI</h1>
        </div>
        <div className="nav-right">
          <span className="user-email">{user.email}</span>
          <button className="nav-button" onClick={() => setCurrentPage('assets')}>
            Asset Library
          </button>
          <button className="nav-button logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <main className="main-content">
        {currentPage === 'dashboard' && (
          <Dashboard token={token} onSelectProject={handleSelectProject} />
        )}
        {currentPage === 'project' && selectedProjectId && (
          <ProjectDetail token={token} projectId={selectedProjectId} onBack={handleBackToDashboard} />
        )}
        {currentPage === 'assets' && (
          <AssetLibrary token={token} onBack={() => setCurrentPage('dashboard')} />
        )}
      </main>
    </div>
  )
}
