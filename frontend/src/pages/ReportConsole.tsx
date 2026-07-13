import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { FindingsTable } from '../components/FindingsTable'
import { OutputViewer } from '../components/OutputViewer'
import { SeverityBadge } from '../components/SeverityBadge'
import type { Finding, MasterDigest, ReportSummary } from '../types'

function asDigest(summary: ReportSummary | undefined, raw: string): MasterDigest {
  if (summary?.executive_summary || summary?.attack_surface) {
    return summary
  }
  try {
    const parsed = JSON.parse(raw || '{}')
    if (parsed.executive_summary) return parsed
    // legacy flat summary
    return {
      scan_id: parsed.scan_id || '',
      target: parsed.target || '',
      risk_score: undefined,
      executive_summary: {
        total_findings: parsed.total_findings ?? 0,
        critical: parsed.critical ?? 0,
        high: parsed.high ?? 0,
        medium: parsed.medium ?? 0,
        low: parsed.low ?? 0,
        info: parsed.info ?? 0,
        tools_executed: parsed.tools_executed ?? [],
        tools_failed: parsed.tools_failed ?? [],
      },
    }
  } catch {
    return { scan_id: '', target: '' }
  }
}

function ReportList() {
  const [severityFilter, setSeverityFilter] = useState('')
  const reports = useQuery({ queryKey: ['reports'], queryFn: api.listReports })

  const filtered = useMemo(() => {
    if (!reports.data) return []
    if (!severityFilter) return reports.data.reports
    return reports.data.reports.filter((report) => {
      try {
        const digest = asDigest(report.summary, report.summary_json || '{}')
        const exec = digest.executive_summary as Record<string, unknown> | undefined
        const count = Number(exec?.[severityFilter] ?? 0)
        return count > 0
      } catch {
        return false
      }
    })
  }, [reports.data, severityFilter])

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Report Console</h1>
          <p className="muted">Master intelligence digests + raw tool appendix</p>
        </div>
        <Link to="/scan/new" className="btn primary">
          New Scan
        </Link>
      </header>

      <section className="panel">
        <div className="filter-bar">
          <label>
            Severity filter
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </label>
        </div>

        {reports.isLoading && <p className="muted">Loading reports…</p>}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Target</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Findings</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((report) => {
                const digest = asDigest(report.summary, report.summary_json || '{}')
                const exec = digest.executive_summary
                return (
                  <tr key={report.id}>
                    <td>
                      <Link to={`/reports/${report.id}`}>{report.title}</Link>
                    </td>
                    <td className="mono">{report.target}</td>
                    <td>
                      <span className={`status-pill status-${report.scan_status}`}>
                        {report.scan_status}
                      </span>
                    </td>
                    <td>{digest.risk_score ?? '—'}</td>
                    <td>
                      <div className="report-badges">
                        {(exec?.critical ?? 0) > 0 && <SeverityBadge severity="critical" />}
                        {(exec?.high ?? 0) > 0 && <SeverityBadge severity="high" />}
                        <span>{exec?.total_findings ?? 0}</span>
                      </div>
                    </td>
                    <td>{new Date(report.created_at).toLocaleString()}</td>
                    <td>
                      <Link to={`/reports/${report.id}`} className="btn small">
                        Open
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!reports.isLoading && filtered.length === 0 && (
          <p className="muted">No reports yet. Run a scan to generate one.</p>
        )}
      </section>
    </div>
  )
}

type Tab = 'digest' | 'findings' | 'failures' | 'raw'

function ReportDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [severityFilter, setSeverityFilter] = useState('')
  const [expandedTool, setExpandedTool] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('digest')

  const report = useQuery({
    queryKey: ['report', id],
    queryFn: () => api.getReport(id!),
    enabled: !!id,
  })

  const deleteReport = useMutation({
    mutationFn: () => api.deleteReport(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      window.location.href = '/reports'
    },
  })

  const exportReport = useMutation({
    mutationFn: () => api.exportReport(id!),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data.export, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `hexstrike-report-${id}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const digest = asDigest(report.data?.summary, report.data?.summary_json || '{}')
  const exec = digest.executive_summary

  const filteredFindings: Finding[] = useMemo(() => {
    const board = digest.findings_board?.length
      ? digest.findings_board
      : (report.data?.findings ?? [])
    if (!severityFilter) return board
    return board.filter((f) => f.severity.toLowerCase() === severityFilter)
  }, [report.data, severityFilter, digest.findings_board])

  if (!id) return <ReportList />
  if (report.isLoading) return <p className="muted page">Loading report…</p>
  if (report.error || !report.data) return <p className="error page">Report not found</p>

  const data = report.data
  const surface = digest.attack_surface

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>{data.title}</h1>
          <p className="muted mono">{data.target}</p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn" onClick={() => exportReport.mutate()}>
            Export JSON
          </button>
          <button
            type="button"
            className="btn danger"
            onClick={() => deleteReport.mutate()}
            disabled={deleteReport.isPending}
          >
            Delete
          </button>
        </div>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Risk score</span>
          <strong>{digest.risk_score ?? 0}</strong>
        </div>
        <div className="stat-card">
          <SeverityBadge severity="critical" />
          <strong>{exec?.critical ?? 0}</strong>
        </div>
        <div className="stat-card">
          <SeverityBadge severity="high" />
          <strong>{exec?.high ?? 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Tools run / skip / fail</span>
          <strong className="small">
            {(exec?.tools_executed?.length ?? 0)} / {(exec?.tools_skipped?.length ?? 0)} /{' '}
            {(exec?.tools_failed?.length ?? 0)}
          </strong>
        </div>
      </div>

      <div className="report-tabs">
        {(['digest', 'findings', 'failures', 'raw'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? 'active' : ''}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'digest' && (
        <>
          <section className="panel">
            <h2>Executive summary</h2>
            <p className="muted">
              Duration: {digest.duration_seconds != null ? `${digest.duration_seconds}s` : '—'} · Status:{' '}
              {digest.status || data.scan_status}
            </p>
            <div className="chip-row">
              {(exec?.tools_executed ?? []).map((t) => (
                <span key={t} className="chip ok">
                  {t}
                </span>
              ))}
              {(exec?.tools_skipped ?? []).map((t) => (
                <span key={t} className="chip skip">
                  {t} (skipped)
                </span>
              ))}
              {(exec?.tools_failed ?? []).map((t) => (
                <span key={t} className="chip fail">
                  {t} (failed)
                </span>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Attack surface</h2>
            <div className="surface-grid">
              <div>
                <h3>Open ports ({surface?.open_ports?.length ?? 0})</h3>
                <ul className="mono list-compact">
                  {(surface?.open_ports ?? []).slice(0, 40).map((p, i) => (
                    <li key={i}>
                      {p.port}/{p.proto}
                    </li>
                  ))}
                  {!surface?.open_ports?.length && <li className="muted">None extracted</li>}
                </ul>
              </div>
              <div>
                <h3>Subdomains ({surface?.subdomains?.length ?? 0})</h3>
                <ul className="mono list-compact">
                  {(surface?.subdomains ?? []).slice(0, 40).map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                  {!surface?.subdomains?.length && <li className="muted">None extracted</li>}
                </ul>
              </div>
              <div>
                <h3>Endpoints ({surface?.endpoints?.length ?? 0})</h3>
                <ul className="mono list-compact">
                  {(surface?.endpoints ?? []).slice(0, 40).map((u) => (
                    <li key={u}>{u}</li>
                  ))}
                  {!surface?.endpoints?.length && <li className="muted">None extracted</li>}
                </ul>
              </div>
            </div>
          </section>
        </>
      )}

      {tab === 'findings' && (
        <section className="panel">
          <div className="filter-bar">
            <h2>Findings board</h2>
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
              <option value="">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>
          <FindingsTable findings={filteredFindings} showTarget />
        </section>
      )}

      {tab === 'failures' && (
        <section className="panel">
          <h2>Tool failures & skips</h2>
          {!digest.tool_failures?.length && <p className="muted">No failures recorded.</p>}
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tool</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {(digest.tool_failures ?? []).map((f, i) => (
                  <tr key={i}>
                    <td className="mono">{f.tool}</td>
                    <td>
                      <span className={`status-pill status-${f.status}`}>{f.status}</span>
                    </td>
                    <td className="mono">{f.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'raw' && (
        <section className="panel">
          <h2>Raw appendix</h2>
          {data.job_outputs?.map((job) => (
            <div key={job.id} className="job-card">
              <button
                type="button"
                className="job-header"
                onClick={() => setExpandedTool(expandedTool === job.id ? null : job.id)}
              >
                <span className="mono">{job.tool_name}</span>
                <span className={`status-pill status-${job.status}`}>{job.status}</span>
              </button>
              {expandedTool === job.id && (
                <OutputViewer stdout={job.stdout} stderr={job.stderr} toolName={job.tool_name} />
              )}
            </div>
          ))}
        </section>
      )}

      <div className="form-actions">
        <Link to="/reports" className="btn">
          Back to Reports
        </Link>
        <Link to={`/scan/${data.scan_id}`} className="btn">
          View Scan
        </Link>
      </div>
    </div>
  )
}

export function ReportConsole() {
  const { id } = useParams<{ id: string }>()
  if (id) return <ReportDetail />
  return <ReportList />
}
