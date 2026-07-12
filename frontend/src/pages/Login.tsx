import React, { useState } from 'react'
import './Login.css'

interface LoginProps {
  onLogin: (token: string) => void
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = isRegistering ? '/api/auth/register' : '/api/auth/login'
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Authentication failed')
        return
      }

      if (isRegistering) {
        setIsRegistering(false)
        setEmail('')
        setPassword('')
        setError('Registration successful! Please login.')
      } else {
        onLogin(data.access_token)
      }
    } catch (err) {
      setError('Connection error. Make sure the backend is running on localhost:8000')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1 className="login-title">🎬 Yetrix Maritime AI</h1>
        <p className="login-subtitle">AI-powered maritime training videos</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
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
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="button login-button" disabled={loading}>
            {loading ? 'Please wait...' : isRegistering ? 'Create Account' : 'Login'}
          </button>
        </form>

        <p className="toggle-mode">
          {isRegistering ? 'Already have an account?' : "Don't have an account?"}
          <button
            type="button"
            className="toggle-button"
            onClick={() => {
              setIsRegistering(!isRegistering)
              setError('')
            }}
            disabled={loading}
          >
            {isRegistering ? 'Login' : 'Register'}
          </button>
        </p>

        <div className="demo-info">
          <p>Demo credentials:</p>
          <code>demo@example.com / password123</code>
        </div>
      </div>
    </div>
  )
}
