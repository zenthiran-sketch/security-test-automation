import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { ToolSelector } from '../components/ToolSelector'
import type { SelectedTool } from '../types'

export function NewScan() {
  const navigate = useNavigate()
  const [target, setTarget] = useState('')
  const [name, setName] = useState('')
  const [selectedTools, setSelectedTools] = useState<SelectedTool[]>([])
  const [error, setError] = useState('')

  const catalog = useQuery({ queryKey: ['tool-catalog'], queryFn: api.getToolCatalog })

  const createScan = useMutation({
    mutationFn: () => api.createScan(target.trim(), selectedTools, name.trim() || undefined),
    onSuccess: (data) => navigate(`/scan/${data.scan.id}`),
    onError: (err: Error) => setError(err.message),
  })

  const createAllWeb = useMutation({
    mutationFn: () => api.createAllWebScan(target.trim(), name.trim() || undefined),
    onSuccess: (data) => navigate(`/scan/${data.scan.id}`),
    onError: (err: Error) => setError(err.message),
  })

  const pending = createScan.isPending || createAllWeb.isPending
  const availableCount = catalog.data?.available_count ?? 0
  const totalCount = catalog.data?.count ?? 0

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!target.trim()) {
      setError('Target is required')
      return
    }
    if (!selectedTools.length) {
      setError('Select at least one tool, or use Scan all web tools')
      return
    }
    createScan.mutate()
  }

  const handleAllWeb = () => {
    setError('')
    if (!target.trim()) {
      setError('Target is required')
      return
    }
    createAllWeb.mutate()
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>New Scan</h1>
          <p className="muted">One URL → parallel web tools → master intelligence report</p>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="scan-form">
        <section className="panel">
          <h2>Target</h2>
          <div className="field-row">
            <label className="field flex-1">
              <span>Target (host, IP, or URL)</span>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="https://example.com"
              />
            </label>
            <label className="field flex-1">
              <span>Scan name (optional)</span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Production recon"
              />
            </label>
          </div>
          <p className="muted" style={{ marginTop: '0.75rem' }}>
            {availableCount} of {totalCount} catalog tools detected on PATH
          </p>
        </section>

        <section className="panel">
          <div className="filter-bar">
            <h2 style={{ margin: 0 }}>Tools</h2>
            <button
              type="button"
              className="btn primary"
              onClick={handleAllWeb}
              disabled={pending}
            >
              {createAllWeb.isPending ? 'Starting…' : 'Scan all web tools'}
            </button>
          </div>
          <p className="muted" style={{ marginBottom: '1rem' }}>
            Runs every web-profile tool in parallel. Missing binaries are skipped (not reported as vulns).
          </p>
          {catalog.isLoading && <p className="muted">Loading tool catalog…</p>}
          {catalog.error && <p className="error">Failed to load tools — is the API running?</p>}
          {catalog.data && (
            <ToolSelector
              catalog={catalog.data.tools}
              selected={selectedTools}
              onChange={setSelectedTools}
            />
          )}
        </section>

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" className="btn" disabled={pending}>
            {createScan.isPending
              ? 'Starting…'
              : `Run selected (${selectedTools.length})`}
          </button>
        </div>
      </form>
    </div>
  )
}
