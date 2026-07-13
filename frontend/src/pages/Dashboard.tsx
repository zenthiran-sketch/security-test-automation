import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { SeverityBadge } from '../components/SeverityBadge'

export function Dashboard() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.getHealth, refetchInterval: 30000 })
  const scans = useQuery({ queryKey: ['scans'], queryFn: () => api.listScans() })
  const reports = useQuery({ queryKey: ['reports'], queryFn: api.listReports })
  const dashboard = useQuery({
    queryKey: ['process-dashboard'],
    queryFn: api.getProcessDashboard,
    refetchInterval: 10000,
  })

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Direct scan pipeline — no AI processing required</p>
        </div>
        <Link to="/scan/new" className="btn primary">
          New Scan
        </Link>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">API Status</span>
          <strong>{health.data?.status ?? '…'}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Tools Available</span>
          <strong>
            {health.data?.total_tools_available ?? 0} / {health.data?.total_tools_count ?? 0}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Database</span>
          <strong>{health.data?.database?.status ?? '…'}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">CPU / Memory</span>
          <strong>
            {dashboard.data?.system_load.cpu_percent?.toFixed(0) ?? '—'}% /{' '}
            {dashboard.data?.system_load.memory_percent?.toFixed(0) ?? '—'}%
          </strong>
        </div>
      </div>

      <section className="panel">
        <h2>Recent Scans</h2>
        {scans.isLoading && <p className="muted">Loading scans…</p>}
        {scans.data?.scans.length === 0 && <p className="muted">No scans yet.</p>}
        <div className="list-cards">
          {scans.data?.scans.slice(0, 8).map((scan) => (
            <Link key={scan.id} to={`/scan/${scan.id}`} className="list-card">
              <div>
                <strong>{scan.name}</strong>
                <p className="muted mono">{scan.target}</p>
              </div>
              <span className={`status-pill status-${scan.status}`}>{scan.status}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Recent Reports</h2>
        {reports.data?.reports.length === 0 && <p className="muted">No reports yet.</p>}
        <div className="list-cards">
          {reports.data?.reports.slice(0, 8).map((report) => {
            let critical = 0
            let high = 0
            let total = 0
            try {
              const raw = report.summary ?? JSON.parse(report.summary_json || '{}')
              const exec = raw.executive_summary ?? raw
              critical = exec.critical ?? 0
              high = exec.high ?? 0
              total = exec.total_findings ?? 0
            } catch {
              /* ignore */
            }
            return (
              <Link key={report.id} to={`/reports/${report.id}`} className="list-card">
                <div>
                  <strong>{report.title}</strong>
                  <p className="muted mono">{report.target}</p>
                </div>
                <div className="report-badges">
                  {critical > 0 && <SeverityBadge severity="critical" />}
                  {high > 0 && <SeverityBadge severity="high" />}
                  <span className="muted">{total} findings</span>
                </div>
              </Link>
            )
          })}
        </div>
      </section>
    </div>
  )
}
