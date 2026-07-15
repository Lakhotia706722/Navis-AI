import React, { useState, useEffect } from 'react'
import './AssetLibrary.css'

interface Asset {
  id: number
  name: string
  category: string
  tags: string[] | string
  file_path: string
  file_format: string
  created_at: string
}

interface AssetLibraryProps {
  token: string
  onBack: () => void
}

const CATEGORIES = [
  'vessel',
  'infrastructure',
  'safety_equipment',
  'navigation_tool',
  'cargo',
  'environment',
]

const FORMAT_ICON: Record<string, string> = {
  blend: '🔵',
  fbx:   '🟠',
  glb:   '🟢',
}

function formatTags(raw: string[] | string): string[] {
  if (Array.isArray(raw)) return raw
  if (!raw) return []
  return raw.split(',').map(t => t.trim()).filter(Boolean)
}

export const AssetLibrary: React.FC<AssetLibraryProps> = ({ token, onBack }) => {
  const [assets,           setAssets]           = useState<Asset[]>([])
  const [loading,          setLoading]          = useState(true)
  const [error,            setError]            = useState('')
  const [searchQuery,      setSearchQuery]      = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [uploading,        setUploading]        = useState(false)

  useEffect(() => { fetchAssets() }, [token, searchQuery, selectedCategory])

  const fetchAssets = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (searchQuery)      params.append('search',   searchQuery)
      if (selectedCategory) params.append('category', selectedCategory)

      const res = await fetch(`http://localhost:8000/api/assets?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      setAssets(await res.json() || [])
      setError('')
    } catch {
      setError('Could not load assets. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['blend','fbx','glb'].includes(ext ?? '')) {
      setError('Only .blend, .fbx, and .glb files are supported.')
      e.target.value = ''
      return
    }

    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    form.append('name', file.name.replace(/\.[^/.]+$/, ''))
    form.append('category', 'vessel')

    try {
      const res = await fetch('http://localhost:8000/api/assets', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Upload failed')
      }
      await fetchAssets()
      setError('')
    } catch (err: any) {
      setError(err.message ?? 'Upload failed. Check the file format and try again.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="asset-library">
      {/* Header */}
      <div className="library-header">
        <div>
          <h1 className="library-heading">Asset Library</h1>
          <p className="library-subheading">
            {loading ? 'Loading…' : `${assets.length} asset${assets.length !== 1 ? 's' : ''}${selectedCategory ? ` in ${selectedCategory}` : ''}`}
          </p>
        </div>
        <button className="button ghost" onClick={onBack}>← Dashboard</button>
      </div>

      {/* Controls */}
      <div className="library-controls">
        <div className="library-search">
          <span className="library-search__icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            placeholder="Search assets…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            aria-label="Search assets"
          />
        </div>

        <div className="library-category">
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>
                {cat.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        <label className={`upload-label${uploading ? ' disabled' : ''}`}>
          {uploading ? '↑ Uploading…' : '+ Upload asset'}
          <input
            type="file"
            accept=".blend,.fbx,.glb"
            onChange={handleUpload}
            disabled={uploading}
            style={{ display: 'none' }}
            aria-label="Upload 3D asset file"
          />
        </label>
      </div>

      {/* Category chips */}
      <div className="category-chips" role="group" aria-label="Category filters">
        <button
          className={`category-chip${selectedCategory === '' ? ' active' : ''}`}
          onClick={() => setSelectedCategory('')}
        >
          All
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`category-chip${selectedCategory === cat ? ' active' : ''}`}
            onClick={() => setSelectedCategory(selectedCategory === cat ? '' : cat)}
          >
            {cat.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <div className="error-message" role="alert">{error}</div>}

      {/* Grid */}
      {loading ? (
        <div className="spinner" />
      ) : assets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">📦</div>
          <p className="empty-state__title">
            {searchQuery || selectedCategory ? 'No assets match that filter' : 'Library is empty'}
          </p>
          <p className="empty-state__body">
            {searchQuery || selectedCategory
              ? `Try clearing the search or choosing a different category.`
              : `Upload .blend, .fbx, or .glb files to build your 3D asset library. Assets are used automatically by the AI scene planner.`}
          </p>
          {!(searchQuery || selectedCategory) && (
            <label className="upload-label" style={{ display: 'inline-flex' }}>
              + Upload first asset
              <input
                type="file"
                accept=".blend,.fbx,.glb"
                onChange={handleUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
          )}
        </div>
      ) : (
        <div className="assets-grid">
          {assets.map(asset => {
            const tags = formatTags(asset.tags)
            const icon = FORMAT_ICON[asset.file_format] ?? '📁'
            return (
              <div key={asset.id} className="asset-card card">
                <div className="asset-card__preview" aria-hidden="true">
                  <span>{icon}</span>
                  <span className="asset-card__format-badge">.{asset.file_format}</span>
                </div>

                <h4 className="asset-card__name" title={asset.name}>{asset.name}</h4>

                <span className="asset-card__category">
                  {asset.category.replace(/_/g, ' ')}
                </span>

                {tags.length > 0 && (
                  <div className="asset-card__tags">
                    {tags.slice(0, 4).map(tag => (
                      <span key={tag} className="asset-tag">{tag}</span>
                    ))}
                  </div>
                )}

                <div className="asset-card__footer">
                  <span className="asset-card__date">
                    {new Date(asset.created_at).toLocaleDateString('en-GB', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
