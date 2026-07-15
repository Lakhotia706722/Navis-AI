import { useState, useEffect } from 'react'
import './index.css'
import { Login }         from './pages/Login'
import { Dashboard }     from './pages/Dashboard'
import { ProjectDetail } from './pages/ProjectDetail'
import { AssetLibrary }  from './pages/AssetLibrary'

type Page = 'login' | 'dashboard' | 'project' | 'assets'

interface User {
  id: number
  email: string
  full_name?: string
}

export default function App() {
  const [token,             setToken]             = useState<string | null>(localStorage.getItem('token'))
  const [user,              setUser]              = useState<User | null>(null)
  const [currentPage,       setCurrentPage]       = useState<Page>('login')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)

  useEffect(() => {
    if (token) verifyToken()
  }, [token])

  const verifyToken = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
        setCurrentPage('dashboard')
      } else {
        clearSession()
      }
    } catch {
      clearSession()
    }
  }

  const clearSession = () => {
    setToken(null)
    localStorage.removeItem('token')
    setUser(null)
    setCurrentPage('login')
  }

  const handleLogin  = (t: string) => { setToken(t); localStorage.setItem('token', t) }
  const handleLogout = () => clearSession()

  const handleSelectProject = (id: number) => {
    setSelectedProjectId(id)
    setCurrentPage('project')
  }

  if (!token || !user) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="app-container">
      <nav className="navbar" role="navigation" aria-label="Main navigation">
        <div className="nav-left">
          {/* Logo mark */}
          <div className="logo-mark" aria-hidden="true">⚓</div>
          <span className="logo">NAVIS AI</span>
        </div>

        <div className="nav-right">
          <button
            className={`nav-button${currentPage === 'dashboard' ? ' active' : ''}`}
            onClick={() => setCurrentPage('dashboard')}
          >
            Projects
          </button>
          <button
            className={`nav-button${currentPage === 'assets' ? ' active' : ''}`}
            onClick={() => setCurrentPage('assets')}
          >
            Assets
          </button>

          <span className="user-email" title={user.email}>
            {user.full_name || user.email}
          </span>

          <button
            className="nav-button logout-btn"
            onClick={handleLogout}
            aria-label="Log out"
          >
            Log out
          </button>
        </div>
      </nav>

      <main className="main-content" id="main">
        {currentPage === 'dashboard' && (
          <Dashboard
            token={token}
            onSelectProject={handleSelectProject}
          />
        )}
        {currentPage === 'project' && selectedProjectId != null && (
          <ProjectDetail
            token={token}
            projectId={selectedProjectId}
            onBack={() => { setCurrentPage('dashboard'); setSelectedProjectId(null) }}
          />
        )}
        {currentPage === 'assets' && (
          <AssetLibrary
            token={token}
            onBack={() => setCurrentPage('dashboard')}
          />
        )}
      </main>
    </div>
  )
}
