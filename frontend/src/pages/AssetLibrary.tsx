import React, { useState, useEffect } from 'react'
import './AssetLibrary.css'

interface Asset {
  id: number
  name: string
  category: string
  tags: string
  file_path: string
  created_at: string
}

interface AssetLibraryProps {
  token: string
  onBack: () => void
}

export const AssetLibrary: React.FC<AssetLibraryProps> = ({ token, onBack }) => {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [uploading, setUploading] = useState(false)

  const categories = ['vessel', 'infrastructure', 'safety_equipment', 'navigation_tool', 'cargo', 'environment']

  useEffect(() => {
    fetchAssets()
  }, [token, searchQuery, selectedCategory])

  const fetchAssets = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (searchQuery) params.append('search', searchQuery)
      if (selectedCategory) params.append('category', selectedCategory)

      const response = await fetch(`http://localhost:8000/api/assets?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) throw new Error('Failed to fetch assets')

      const data = await response.json()
      setAssets(data || [])
      setError('')
    } catch (err) {
      setError('Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', file.name.replace(/\.[^/.]+$/, ''))
    formData.append('category', 'vessel') // Default category

    try {
      const response = await fetch('http://localhost:8000/api/assets', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (!response.ok) throw new Error('Upload failed')

      await fetchAssets()
      setError('')
    } catch (err) {
      setError('Failed to upload asset')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="asset-library">
      <div className="library-header">
        <h2>Asset Library</h2>
        <button className="back-button" onClick={onBack}>← Back to Dashboard</button>
      </div>

      <div className="library-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="category-filter">
          <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}>
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat.replace(/_/g, ' ').toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <label className="upload-button">
          {uploading ? 'Uploading...' : '+ Upload Asset'}
          <input
            type="file"
            accept=".blend,.fbx,.glb"
            onChange={handleFileUpload}
            disabled={uploading}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="spinner"></div>
      ) : (
        <div className="assets-grid">
          {assets.length === 0 ? (
            <div className="empty-state">
              <p>📦 No assets found</p>
              <p className="empty-help">Upload 3D models (.blend, .fbx, .glb) to get started</p>
            </div>
          ) : (
            assets.map((asset) => (
              <div key={asset.id} className="asset-card card">
                <div className="asset-icon">🎨</div>
                <h4>{asset.name}</h4>
                <p className="asset-category">
                  <span className="category-badge">{asset.category}</span>
                </p>
                {asset.tags && (
                  <div className="asset-tags">
                    {asset.tags.split(',').map((tag) => (
                      <span key={tag} className="tag">
                        #{tag.trim()}
                      </span>
                    ))}
                  </div>
                )}
                <p className="asset-date">
                  Added: {new Date(asset.created_at).toLocaleDateString()}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
