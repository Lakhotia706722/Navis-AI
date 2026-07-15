import React, { useState, useEffect } from 'react'
import './Dashboard.css'

interface Project {
  id: number
  title: string
  prompt: string
  status: string
  created_at: string
}

interface DashboardProps {
  token: string
  onSelectProject: (projectId: number) => void
}

// Pipeline stages in order — used for depth sounder mini strip
const PIPELINE_STAGES = ['queued','planning','composing','rendering','assembling','done']

function stageIndex(status: string): number {
  const idx = PIPELINE_STAGES.indexOf(status)
  return idx === -1 ? 0 : idx
}

/** Mini 6-stage depth sounder strip for project cards */
function DepthStrip({ status }: { status: string }) {
  const currentIdx = stageIndex(status)
  const isFailed = status === 'failed'
  const isDone   = status === 'done'

  return (
    <div className="project-card__depth" aria-hidden="true">
      {PIPELINE_STAGES.slice(0, -1).map((stage, i) => {
        const isActive = !isDone && !isFailed && i === currentIdx
        const isFilled = isDone || i < currentIdx
        return (
          <div
            key={stage}
            className={[
              'project-card__depth-stage',
              isFailed ? 'failed' : '',
              isActive ? 'active' : '',
              isFilled ? 'filled' : '',
            ].join(' ')}
          />
        )
      })}
    </div>
  )
}

export const Dashboard: React.FC<DashboardProps> = ({ token, onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newPrompt, setNewPrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { fetchProjects() }, [token])

  const fetchProjects = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/projects', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setProjects(data || [])
      setError('')
    } catch {
      setError('Could not load projects. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const res = await fetch('http://localhost:8000/api/projects', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle, prompt: newPrompt }),
      })
      if (!res.ok) throw new Error()
      setNewTitle('')
      setNewPrompt('')
      setShowForm(false)
      await fetchProjects()
    } catch {
      setError('Failed to create project. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="dashboard"><div className="spinner" /></div>
  }

  const active  = projects.filter(p => !['done','failed'].includes(p.status)).length
  const done    = projects.filter(p => p.status === 'done').length
  const failed  = projects.filter(p => p.status === 'failed').length

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-heading">Projects</h1>
          <p className="dashboard-subheading">
            {projects.length === 0
              ? 'No projects yet — create your first below'
              : `${projects.length} project${projects.length !== 1 ? 's' : ''} in this workspace`}
          </p>
        </div>
        <button
          className="button"
          onClick={() => setShowForm(v => !v)}
          aria-expanded={showForm}
        >
          {showForm ? '✕ Cancel' : '+ New Project'}
        </button>
      </div>

      {/* Stats bar — only shown when there's data */}
      {projects.length > 0 && (
        <div className="dashboard-stats">
          <div className="stat-chip">
            <span className="stat-chip__value">{projects.length}</span>
            <span className="stat-chip__label">Total</span>
          </div>
          {active > 0 && (
            <div className="stat-chip">
              <span className="stat-chip__value" style={{ color: 'var(--clr-amber)' }}>{active}</span>
              <span className="stat-chip__label">Active</span>
            </div>
          )}
          {done > 0 && (
            <div className="stat-chip">
              <span className="stat-chip__value" style={{ color: 'var(--clr-success)' }}>{done}</span>
              <span className="stat-chip__label">Done</span>
            </div>
          )}
          {failed > 0 && (
            <div className="stat-chip">
              <span className="stat-chip__value" style={{ color: 'var(--clr-error)' }}>{failed}</span>
              <span className="stat-chip__label">Failed</span>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && <div className="error-message" role="alert">{error}</div>}

      {/* New project form */}
      {showForm && (
        <div className="card new-project-form">
          <h2 className="new-project-form__title">New Project</h2>
          <form onSubmit={handleCreate}>
            <div className="input-group">
              <label htmlFor="proj-title">Project title</label>
              <input
                id="proj-title"
                type="text"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                placeholder="e.g., Lifeboat Safety Training"
                required
                disabled={submitting}
              />
            </div>
            <div className="input-group">
              <label htmlFor="proj-prompt">Video prompt</label>
              <textarea
                id="proj-prompt"
                value={newPrompt}
                onChange={e => setNewPrompt(e.target.value)}
                placeholder="Describe the training video — equipment, procedure, environment, tone…"
                required
                disabled={submitting}
                rows={4}
              />
            </div>
            <div className="form-row">
              <button type="submit" className="button" disabled={submitting}>
                {submitting ? 'Creating…' : 'Create Project'}
              </button>
              <button
                type="button"
                className="button ghost"
                onClick={() => setShowForm(false)}
                disabled={submitting}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Projects grid */}
      <div className="projects-grid">
        {projects.length === 0 ? (
          <div className="projects-empty">
            <div className="empty-state">
              <div className="empty-state__icon">⚓</div>
              <p className="empty-state__title">No projects yet</p>
              <p className="empty-state__body">
                Create a project, write a training brief, and Navis AI will generate a full maritime video —
                script, voice-over, scenes, and all.
              </p>
              <button className="button" onClick={() => setShowForm(true)}>
                + New Project
              </button>
            </div>
          </div>
        ) : (
          projects.map(project => (
            <div
              key={project.id}
              className="project-card card"
              onClick={() => onSelectProject(project.id)}
              role="button"
              tabIndex={0}
              aria-label={`Open project: ${project.title}`}
              onKeyDown={e => e.key === 'Enter' && onSelectProject(project.id)}
            >
              <DepthStrip status={project.status} />

              <div className="project-card__body">
                <h3 className="project-card__title">{project.title}</h3>
                <p className="project-card__prompt">{project.prompt}</p>
                <div className="project-card__meta">
                  <span className="project-card__date">
                    {new Date(project.created_at).toLocaleDateString('en-GB', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </span>
                  <span className={`status-badge ${project.status}`}>
                    {project.status}
                  </span>
                  <span className="project-card__arrow" aria-hidden="true">→</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
