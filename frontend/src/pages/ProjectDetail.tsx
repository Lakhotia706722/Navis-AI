import React, { useState, useEffect } from 'react'
import './ProjectDetail.css'

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
  started_at?: string
  completed_at?: string
  output_video_path?: string
  error_message?: string
  render_mode?: string
}

interface Scene {
  id: number
  scene_number: number
  name: string
  duration_seconds: number
}

interface UsageLog {
  gpt_tokens: number
  tts_characters: number
  render_minutes: number
  total_cost: number
}

interface ProjectDetailProps {
  token: string
  projectId: number
  onBack: () => void
}

export const ProjectDetail: React.FC<ProjectDetailProps> = ({ token, projectId, onBack }) => {
  const [project, setProject] = useState<Project | null>(null)
  const [renders, setRenders] = useState<RenderJob[]>([])
  const [selectedRender, setSelectedRender] = useState<RenderJob | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [usageStats, setUsageStats] = useState<UsageLog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [renderMode, setRenderMode] = useState<'preview' | 'full'>('preview')
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    fetchProjectData()
  }, [projectId, token])

  useEffect(() => {
    const interval = setInterval(() => {
      if (selectedRender && ['queued', 'planning', 'composing', 'rendering', 'assembling'].includes(selectedRender.status)) {
        fetchRenderStatus(selectedRender.id)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [selectedRender])

  const fetchProjectData = async () => {
    try {
      setLoading(true)
      const [projectRes, rendersRes] = await Promise.all([
        fetch(`http://localhost:8000/api/projects/${projectId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`http://localhost:8000/api/projects/${projectId}/renders`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ])

      const projectData = await projectRes.json()
      const rendersData = await rendersRes.json()

      setProject(projectData)
      setRenders(rendersData || [])

      if (rendersData && rendersData.length > 0) {
        const latestRender = rendersData[0]
        setSelectedRender(latestRender)

        if (latestRender.scenes) {
          setScenes(latestRender.scenes)
        }
      }

      setError('')
    } catch (err) {
      setError('Failed to load project details')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRenderStatus = async (renderId: number) => {
    try {
      const response = await fetch(`http://localhost:8000/api/renders/${renderId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json()

      setSelectedRender(data)
      setRenders((prev) => prev.map((r) => (r.id === renderId ? data : r)))

      if (data.scenes) {
        setScenes(data.scenes)
      }
    } catch (err) {
      console.error('Failed to fetch render status:', err)
    }
  }

  const handleStartRender = async () => {
    setStarting(true)
    try {
      const response = await fetch(`http://localhost:8000/api/renders/${projectId}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ render_mode: renderMode }),
      })

      if (!response.ok) {
        throw new Error('Failed to start render')
      }

      const newRender = await response.json()
      setRenders((prev) => [newRender, ...prev])
      setSelectedRender(newRender)
      setError('')
    } catch (err) {
      setError('Failed to start render')
    } finally {
      setStarting(false)
    }
  }

  if (loading) {
    return (
      <div className="project-detail">
        <button className="back-button" onClick={onBack}>← Back</button>
        <div className="spinner"></div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="project-detail">
        <button className="back-button" onClick={onBack}>← Back</button>
        <div className="error-message">Project not found</div>
      </div>
    )
  }

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      queued: '#f59e0b',
      planning: '#3b82f6',
      composing: '#6b7280',
      rendering: '#8b5cf6',
      assembling: '#06b6d4',
      done: '#10b981',
      failed: '#ef4444',
    }
    return colors[status] || '#6b7280'
  }

  return (
    <div className="project-detail">
      <div className="detail-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>{project.title}</h1>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="detail-grid">
        {/* Project Info */}
        <div className="card project-info">
          <h3>Project Details</h3>
          <p><strong>Prompt:</strong></p>
          <p className="prompt-text">{project.prompt}</p>
          <p className="project-date">Created: {new Date(project.created_at).toLocaleDateString()}</p>
        </div>

        {/* Render Controls */}
        <div className="card render-controls">
          <h3>Start New Render</h3>
          <div className="input-group">
            <label htmlFor="render-mode">Render Quality</label>
            <select
              id="render-mode"
              value={renderMode}
              onChange={(e) => setRenderMode(e.target.value as 'preview' | 'full')}
              disabled={starting}
            >
              <option value="preview">Preview (Fast, 480p, ~5 min)</option>
              <option value="full">Full Quality (Production, 1080p, ~20 min)</option>
            </select>
          </div>
          <button
            className="button"
            onClick={handleStartRender}
            disabled={starting || (selectedRender && !['done', 'failed'].includes(selectedRender.status))}
          >
            {starting ? 'Starting...' : 'Start Render'}
          </button>
          {selectedRender && !['done', 'failed'].includes(selectedRender.status) && (
            <p className="info-text">⚠ A render is already in progress</p>
          )}
        </div>
      </div>

      {/* Render Status */}
      {selectedRender && (
        <div className="card render-status">
          <h3>Current Render</h3>
          <div className="status-row">
            <span>Status:</span>
            <span className="status-badge" style={{ backgroundColor: getStatusColor(selectedRender.status), color: 'white' }}>
              {selectedRender.status.toUpperCase()}
            </span>
          </div>

          <div className="progress-section">
            <div className="progress-label">
              <span>Progress</span>
              <span className="progress-percent">{selectedRender.progress_percent}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${selectedRender.progress_percent}%` }}></div>
            </div>
          </div>

          {selectedRender.started_at && (
            <p className="render-info">Started: {new Date(selectedRender.started_at).toLocaleString()}</p>
          )}

          {selectedRender.completed_at && (
            <p className="render-info">Completed: {new Date(selectedRender.completed_at).toLocaleString()}</p>
          )}

          {selectedRender.error_message && (
            <div className="error-box">
              <strong>Error:</strong> {selectedRender.error_message}
            </div>
          )}

          {selectedRender.status === 'done' && selectedRender.output_video_path && (
            <div className="success-box">
              <p>✓ Render complete!</p>
              <p className="video-path">Video: {selectedRender.output_video_path}</p>
              <button className="button secondary">
                ↓ Download Video
              </button>
            </div>
          )}
        </div>
      )}

      {/* Scenes */}
      {scenes.length > 0 && (
        <div className="card scenes-section">
          <h3>Scenes ({scenes.length})</h3>
          <div className="scenes-list">
            {scenes.map((scene) => (
              <div key={scene.id} className="scene-item">
                <span className="scene-number">Scene {scene.scene_number}</span>
                <span className="scene-name">{scene.name || 'Untitled Scene'}</span>
                <span className="scene-duration">{scene.duration_seconds}s</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Render History */}
      {renders.length > 1 && (
        <div className="card render-history">
          <h3>Render History</h3>
          <div className="renders-timeline">
            {renders.slice(1).map((render) => (
              <div key={render.id} className="timeline-item" onClick={() => setSelectedRender(render)}>
                <div className="timeline-marker" style={{ backgroundColor: getStatusColor(render.status) }}></div>
                <div className="timeline-content">
                  <p className="timeline-status">{render.status.toUpperCase()} - {render.progress_percent}%</p>
                  {render.started_at && (
                    <p className="timeline-date">{new Date(render.started_at).toLocaleString()}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
