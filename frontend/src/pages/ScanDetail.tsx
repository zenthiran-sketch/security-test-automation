import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { FindingsTable } from '../components/FindingsTable'
import { OutputViewer } from '../components/OutputViewer'
import type { SseEvent } from '../types'

export function ScanDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [events, setEvents] = useState<SseEvent[]>([])
  const [expandedJob, setExpandedJob] = useState<string | null>(null)

  const scan = useQuery({
    queryKey: ['scan', id],
    queryFn: () => api.getScan(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status && ['completed', 'completed_with_errors', 'cancelled', 'failed'].includes(status)) {
        return false
      }
      return 3000
    },
  })

  const cancelScan = useMutation({
    mutationFn: () => api.cancelScan(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scan', id] }),
  })

  useEffect(() => {
    if (!id) return
    const source = api.subscribeScanEvents(id, (data) => {
      setEvents((prev) => [...prev.slice(-50), data as SseEvent])
      const evt = data as SseEvent
      if (evt.type === 'tool_completed' || evt.type === 'scan_completed') {
        queryClient.invalidateQueries({ queryKey: ['scan', id] })
        queryClient.invalidateQueries({ queryKey: ['scans'] })
        queryClient.invalidateQueries({ queryKey: ['reports'] })
      }
    })
    return () => source.close()
  }, [id, queryClient])

  if (!id) return null
  if (scan.isLoading) return <p className="muted page">Loading scan…</p>
  if (scan.error || !scan.data) return <p className="error page">Scan not found</p>

  const data = scan.data
  const isRunning = ['queued', 'running'].includes(data.status)

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>{data.name}</h1>
          <p className="muted mono">{data.target}</p>
        </div>
        <div className="header-actions">
          <span className={`status-pill status-${data.status}`}>{data.status}</span>
          {isRunning && (
            <button
              type="button"
              className="btn danger"
              onClick={() => cancelScan.mutate()}
              disabled={cancelScan.isPending}
            >
              Cancel
            </button>
          )}
        </div>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Jobs</span>
          <strong>{data.jobs?.length ?? 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Findings</span>
          <strong>{data.findings_count ?? data.findings?.length ?? 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Started</span>
          <strong className="small">{new Date(data.created_at).toLocaleString()}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Completed</span>
          <strong className="small">
            {data.completed_at ? new Date(data.completed_at).toLocaleString() : '—'}
          </strong>
        </div>
      </div>

      <section className="panel">
        <h2>Tool Jobs</h2>
        <div className="jobs-list">
          {data.jobs?.map((job) => (
            <div key={job.id} className="job-card">
              <button
                type="button"
                className="job-header"
                onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
              >
                <span className="mono">{job.tool_name}</span>
                <span className={`status-pill status-${job.status}`}>{job.status}</span>
                {job.execution_time != null && (
                  <span className="muted">{job.execution_time.toFixed(1)}s</span>
                )}
              </button>
              {expandedJob === job.id && (
                <OutputViewer stdout={job.stdout} stderr={job.stderr} toolName={job.tool_name} />
              )}
            </div>
          ))}
        </div>
      </section>

      {data.findings && data.findings.length > 0 && (
        <section className="panel">
          <h2>Findings</h2>
          <FindingsTable findings={data.findings} showTarget />
        </section>
      )}

      {events.length > 0 && (
        <section className="panel">
          <h2>Live Events</h2>
          <div className="event-log">
            {events.slice(-12).map((evt, i) => (
              <div key={i} className="event-line mono">
                <span className="muted">{evt.type}</span>
                {evt.tool && <span> {evt.tool}</span>}
                {evt.status && <span> → {evt.status}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      {!isRunning && (
        <div className="form-actions">
          <Link to="/reports" className="btn">
            View Reports
          </Link>
        </div>
      )}
    </div>
  )
}
