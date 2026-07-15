import React, { useState } from 'react'
import './Login.css'

interface LoginProps {
  onLogin: (token: string) => void
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)

  const switchTab = (register: boolean) => {
    setIsRegistering(register)
    setError('')
    setSuccess('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const endpoint = isRegistering ? '/api/auth/register' : '/api/auth/login'
      const body: Record<string, string> = { email, password }
      if (isRegistering && fullName) body.full_name = fullName

      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Authentication failed')
        return
      }

      if (isRegistering) {
        setSuccess('Account created — log in to continue.')
        setIsRegistering(false)
        setEmail('')
        setPassword('')
        setFullName('')
      } else {
        onLogin(data.access_token)
      }
    } catch {
      setError('Cannot reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-panel">
        {/* Brand */}
        <div className="login-brand">
          <div className="login-brand__mark" aria-hidden="true">⚓</div>
          <span className="login-brand__name">NAVIS AI</span>
          <span className="login-brand__sub">Maritime training video platform</span>
        </div>

        {/* Tab switcher */}
        <div className="login-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={!isRegistering}
            className={`login-tab${!isRegistering ? ' active' : ''}`}
            onClick={() => switchTab(false)}
            disabled={loading}
          >
            Log in
          </button>
          <button
            role="tab"
            aria-selected={isRegistering}
            className={`login-tab${isRegistering ? ' active' : ''}`}
            onClick={() => switchTab(true)}
            disabled={loading}
          >
            Register
          </button>
        </div>

        {/* Feedback */}
        {success && <div className="login-success" role="status">{success}</div>}
        {error   && <div className="error-message"  role="alert">{error}</div>}

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate>
          {isRegistering && (
            <div className="input-group">
              <label htmlFor="full-name">Full name</label>
              <input
                id="full-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Blackwood"
                disabled={loading}
                autoComplete="name"
              />
            </div>
          )}

          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="navigator@vessel.com"
              required
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              autoComplete={isRegistering ? 'new-password' : 'current-password'}
            />
          </div>

          <button type="submit" className="button login-submit" disabled={loading}>
            {loading ? 'One moment…' : isRegistering ? 'Create account' : 'Log in'}
          </button>
        </form>

        {/* Demo info */}
        {!isRegistering && (
          <div className="login-demo" aria-label="Demo credentials">
            <span className="login-demo__label">Demo credentials</span>
            <code className="login-demo__creds">demo@example.com / password123</code>
          </div>
        )}
      </div>
    </div>
  )
}
