import React, { useState, useEffect } from 'react'
import './Dashboard.css'

interface Project {
  id: number
  title: string
  prompt: string
  created_at: string
}

interface RenderJob {
  id: number
  status: string
  progress_percent: number
}

interface DashboardProps {
  token: string
  onSelectProject: (projectId: number) => void
}

export const Dashboard: React.FC<DashboardProps> = ({ token, onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showNewProject, setShowNewProject] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newPrompt, setNewPrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [token])

  const fetchProjects = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/projects', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()
      setProjects(data || [])
      setError('')
    } catch (err) {
      setError('Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const response = await fetch('http://localhost:8000/api/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: newTitle, prompt: newPrompt }),
      })

      if (!response.ok) {
        throw new Error('Failed to create project')
      }

      setNewTitle('')
      setNewPrompt('')
      setShowNewProject(false)
      await fetchProjects()
    } catch (err) {
      setError('Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>My Projects</h2>
        <button className="button" onClick={() => setShowNewProject(!showNewProject)}>
          {showNewProject ? '✕ Cancel' : '+ New Project'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showNewProject && (
        <div className="card new-project-form">
          <h3>Create New Project</h3>
          <form onSubmit={handleCreateProject}>
            <div className="input-group">
              <label htmlFor="title">Project Title</label>
              <input
                id="title"
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="e.g., Lifeboat Safety Training"
                required
                disabled={submitting}
              />
            </div>

            <div className="input-group">
              <label htmlFor="prompt">Video Prompt</label>
              <textarea
                id="prompt"
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                placeholder="Describe what you want in the video..."
                required
                disabled={submitting}
              />
            </div>

            <button type="submit" className="button" disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Project'}
            </button>
          </form>
        </div>
      )}

      <div className="projects-grid">
        {projects.length === 0 ? (
          <div className="empty-state">
            <p>📹 No projects yet</p>
            <p className="empty-help">Create your first project to get started</p>
          </div>
        ) : (
          projects.map((project) => (
            <div key={project.id} className="project-card card" onClick={() => onSelectProject(project.id)}>
              <h3>{project.title}</h3>
              <p className="project-prompt">{project.prompt}</p>
              <p className="project-date">Created: {new Date(project.created_at).toLocaleDateString()}</p>
              <button className="button secondary" onClick={(e) => {
                e.stopPropagation()
                onSelectProject(project.id)
              }}>
                View Project →
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
