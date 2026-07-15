import React, { useState, useEffect, useCallback } from 'react'
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
  render_mode: string
  started_at?: string
  completed_at?: string
  output_video_path?: string
  error_message?: string
}

interface Scene {
  id: number
  scene_number: number
  name: string
  duration_seconds: number
}

interface ProjectDetailProps {
  token: string
  projectId: number
  onBack: () => void
}

const PIPELINE_STAGES = ['queued','planning','composing','rendering','assembling','done']
const ACTIVE_STAGES   = new Set(['queued','planning','composing','rendering','assembling'])

const STAGE_COLORS: Record<string, string> = {
  queued:     '#64748B',
  planning:   '#60A5FA',
  composing:  '#A78BFA',
  rendering:  '#F5A623',
  assembling: '#34D399',
  done:       '#22C55E',
  failed:     '#EF4444',
}

const STAGE_LABELS: Record<string, string> = {
  queued:     'Queued',
  planning:   'Planning',
  composing:  'Composing',
  rendering:  'Rendering',
  assembling: 'Assembling',
  done:       'Done',
  failed:     'Failed',
}

/**
 * The signature Pipeline Depth Sounder — visualises which stage is active
 * as a vertical fill column, like a vessel's draught marks.
 */
function DepthSounder({ status }: { status: string }) {
  const currentIdx = PIPELINE_STAGES.indexOf(status)
  const isFailed   = status === 'failed'
  const isDone     = status === 'done'
  // Display stages (exclude 'done' as a step — it becomes the all-filled state)
  const displayStages = PIPELINE_STAGES.slice(0, -1) // queued→assembling

  return (
    <div className="depth-sounder" aria-hidden="true">
      <div className="depth-sounder__track">
        {displayStages.map((stage, i) => {
          const isCurrent = !isDone && !isFailed && i === currentIdx
          const isFilled  = !isFailed && (isDone || i < currentIdx)
          return (
            <div
              key={stage}
              className={[
                'depth-stage',
                isFailed  ? 'failed-stage' : '',
                isCurrent ? 'active'       : '',
                isFilled  ? 'filled'       : '',
                isDone    ? 'done-stage'   : '',
              ].filter(Boolean).join(' ')}
              title={stage}
            >
              <div className="depth-stage__dot" />
            </div>
          )
        })}
      </div>
      <span className="depth-sounder__label">Pipeline</span>
    </div>
  )
}

function stageClass(status: string) {
  if (status === 'failed') return 'red'
  if (status === 'done')   return 'green'
  if (ACTIVE_STAGES.has(status)) return 'amber'
  return ''
}

export const ProjectDetail: React.FC<ProjectDetailProps> = ({ token, projectId, onBack }) => {
  const [project,        setProject]        = useState<Project | null>(null)
  const [renders,        setRenders]        = useState<RenderJob[]>([])
  const [selectedRender, setSelectedRender] = useState<RenderJob | null>(null)
  const [scenes,         setScenes]         = useState<Scene[]>([])
  const [loading,        setLoading]        = useState(true)
  const [error,          setError]          = useState('')
  const [renderMode,     setRenderMode]     = useState<'preview' | 'full'>('preview')
  const [starting,       setStarting]       = useState(false)

  // ── Fetch ─────────────────────────────────────────────────
  const fetchProjectData = useCallback(async () => {
    try {
      setLoading(true)
      const [projRes, rendersRes] = await Promise.all([
        fetch(`http://localhost:8000/api/projects/${projectId}`,         { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`http://localhost:8000/api/projects/${projectId}/renders`, { headers: { Authorization: `Bearer ${token}` } }),
      ])
      if (!projRes.ok) throw new Error('Project not found')

      const projData    = await projRes.json()
      const rendersData = await rendersRes.json()

      setProject(projData)
      const renderList = rendersData || []
      setRenders(renderList)

      if (renderList.length > 0) {
        const latest = renderList[0]
        setSelectedRender(latest)
        if (latest.scenes) setScenes(latest.scenes)
      }
      setError('')
    } catch (err: any) {
      setError(err.message || 'Failed to load project.')
    } finally {
      setLoading(false)
    }
  }, [projectId, token])

  const fetchRenderStatus = useCallback(async (renderId: number) => {
    try {
      const res  = await fetch(`http://localhost:8000/api/renders/${renderId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      setSelectedRender(data)
      setRenders(prev => prev.map(r => r.id === renderId ? data : r))
      if (data.scenes) setScenes(data.scenes)
    } catch { /* silent — polling */ }
  }, [token])

  useEffect(() => { fetchProjectData() }, [fetchProjectData])

  // Poll while a render is active
  useEffect(() => {
    if (!selectedRender || !ACTIVE_STAGES.has(selectedRender.status)) return
    const id = setInterval(() => fetchRenderStatus(selectedRender.id), 3000)
    return () => clearInterval(id)
  }, [selectedRender, fetchRenderStatus])

  // ── Actions ───────────────────────────────────────────────
  const handleStartRender = async () => {
    setStarting(true)
    setError('')
    try {
      const res = await fetch(`http://localhost:8000/api/renders/${projectId}/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ render_mode: renderMode }),
      })
      if (!res.ok) throw new Error('Failed to start render')
      const newRender = await res.json()
      setRenders(prev => [newRender, ...prev])
      setSelectedRender(newRender)
    } catch {
      setError('Render could not be started. Check the project prompt and try again.')
    } finally {
      setStarting(false)
    }
  }

  // ── Render helpers ────────────────────────────────────────
  const isActive = selectedRender && ACTIVE_STAGES.has(selectedRender.status)

  if (loading) return (
    <div className="project-detail">
      <button className="back-button" onClick={onBack}>← Projects</button>
      <div className="spinner" />
    </div>
  )

  if (!project) return (
    <div className="project-detail">
      <button className="back-button" onClick={onBack}>← Projects</button>
      <div className="empty-state">
        <div className="empty-state__icon">🔍</div>
        <p className="empty-state__title">Project not found</p>
        <p className="empty-state__body">
          This project may have been deleted, or you may not have access to it.
        </p>
        <button className="button" onClick={onBack}>Back to Projects</button>
      </div>
    </div>
  )

  return (
    <div className="project-detail">
      {/* Header */}
      <div className="detail-header">
        <button className="back-button" onClick={onBack}>← Projects</button>
        <h1 className="detail-title">{project.title}</h1>
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}

      {/* Top grid: project info + render controls */}
      <div className="detail-grid">
        {/* Project info */}
        <div className="card">
          <span className="project-info__label">Training brief</span>
          <p className="project-info__prompt">{project.prompt}</p>
          <span className="project-info__date">
            Created {new Date(project.created_at).toLocaleDateString('en-GB', {
              day: 'numeric', month: 'long', year: 'numeric',
            })}
          </span>
        </div>

        {/* Render controls */}
        <div className="card">
          <h2 className="render-controls__title">Start Render</h2>

          <div className="render-quality-options" role="radiogroup" aria-label="Render quality">
            {[
              { value: 'preview', name: 'Preview',   desc: '16 samples · 480p · ~5 min' },
              { value: 'full',    name: 'Production', desc: '128 samples · 1080p · ~20 min' },
            ].map(opt => (
              <label
                key={opt.value}
                className={`render-quality-option${renderMode === opt.value ? ' selected' : ''}`}
              >
                <input
                  type="radio"
                  name="renderMode"
                  value={opt.value}
                  checked={renderMode === opt.value}
                  onChange={() => setRenderMode(opt.value as 'preview' | 'full')}
                  disabled={!!isActive || starting}
                />
                <div className="render-quality-option__info">
                  <span className="render-quality-option__name">{opt.name}</span>
                  <span className="render-quality-option__desc">{opt.desc}</span>
                </div>
              </label>
            ))}
          </div>

          <button
            className="button"
            style={{ width: '100%' }}
            onClick={handleStartRender}
            disabled={starting || !!isActive}
          >
            {starting ? 'Starting…' : 'Start Render'}
          </button>

          {isActive && (
            <div className="render-in-progress-notice">
              <span>⏳</span>
              <span>Render in progress — wait for it to finish or cancel below.</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Pipeline Depth Sounder ── */}
      {selectedRender && (
        <div className="card render-status">
          <div className="render-status__inner">
            <DepthSounder status={selectedRender.status} />

            <div className="render-status__content">
              {/* Stage label + badge */}
              <div className="render-status__head">
                <span className="render-status__stage">
                  {STAGE_LABELS[selectedRender.status] ?? selectedRender.status}
                </span>
                <span className={`status-badge ${selectedRender.status}`}>
                  {selectedRender.render_mode === 'preview' ? 'Preview' : 'Production'}
                </span>
              </div>

              {/* Progress bar */}
              <div className="progress-section">
                <div className="progress-row">
                  <span className="progress-label">Progress</span>
                  <span className={`progress-pct ${stageClass(selectedRender.status)}`}>
                    {selectedRender.progress_percent}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill${selectedRender.status === 'rendering' ? ' amber' : ''}`}
                    style={{ width: `${selectedRender.progress_percent}%` }}
                  />
                </div>
              </div>

              {/* Timestamps */}
              <div className="render-meta">
                {selectedRender.started_at && (
                  <div className="render-meta__item">
                    <span className="render-meta__key">Started</span>
                    <span className="render-meta__val">
                      {new Date(selectedRender.started_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {selectedRender.completed_at && (
                  <div className="render-meta__item">
                    <span className="render-meta__key">Finished</span>
                    <span className="render-meta__val">
                      {new Date(selectedRender.completed_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>

              {/* Error callout */}
              {selectedRender.status === 'failed' && (
                <div className="render-callout error">
                  <div className="render-callout__title">⚠ Render failed</div>
                  <p>
                    {selectedRender.error_message
                      ? `${selectedRender.error_message}. Check your project prompt for scene or asset issues, then start a new render.`
                      : 'An unexpected error occurred during rendering. Check worker logs and start a new render.'}
                  </p>
                </div>
              )}

              {/* Success callout */}
              {selectedRender.status === 'done' && (
                <div className="render-callout success">
                  <div className="render-callout__title">✓ Render complete</div>
                  {selectedRender.output_video_path && (
                    <p className="video-path">{selectedRender.output_video_path}</p>
                  )}
                  <button className="button sm secondary">↓ Download video</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* No renders yet */}
      {!selectedRender && !isActive && (
        <div className="empty-state" style={{ marginBottom: 'var(--space-5)' }}>
          <div className="empty-state__icon">🎬</div>
          <p className="empty-state__title">No renders yet</p>
          <p className="empty-state__body">
            Pick a render quality above — Preview is faster for checking the script and timing,
            Production is for the final deliverable.
          </p>
        </div>
      )}

      {/* ── Storyboard / Scenes ── */}
      {scenes.length > 0 && (
        <div className="card scenes-section">
          <div className="scenes-section__header">
            <span className="scenes-section__title">Storyboard</span>
            <span className="scenes-section__count">
              {scenes.length} scene{scenes.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="scenes-grid">
            {scenes.map(scene => (
              <div key={scene.id} className="scene-card">
                <span className="scene-card__number">Scene {scene.scene_number}</span>
                <div className="scene-card__thumbnail" aria-hidden="true">🎞</div>
                <span className="scene-card__name">{scene.name || 'Untitled Scene'}</span>
                <span className="scene-card__duration">
                  {scene.duration_seconds}s
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Render history ── */}
      {renders.length > 1 && (
        <div className="card render-history">
          <h3 className="history-title">Render History</h3>
          <div className="history-list">
            {renders.slice(1).map(render => (
              <div
                key={render.id}
                className={`history-item${selectedRender?.id === render.id ? ' selected' : ''}`}
                onClick={() => { setSelectedRender(render) }}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && setSelectedRender(render)}
              >
                <div
                  className="history-item__dot"
                  style={{ background: STAGE_COLORS[render.status] ?? '#64748B' }}
                />
                <div className="history-item__info">
                  <div className="history-item__status">
                    {STAGE_LABELS[render.status] ?? render.status}
                    {render.render_mode === 'preview' ? ' · Preview' : ' · Production'}
                  </div>
                  {render.started_at && (
                    <div className="history-item__date">
                      {new Date(render.started_at).toLocaleString()}
                    </div>
                  )}
                </div>
                <span className="history-item__pct">{render.progress_percent}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
