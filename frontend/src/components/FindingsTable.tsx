import type { Finding } from '../types'
import { SeverityBadge } from './SeverityBadge'

interface Props {
  findings: Finding[]
  showTarget?: boolean
}

export function FindingsTable({ findings, showTarget = false }: Props) {
  if (!findings.length) {
    return <p className="muted">No findings recorded.</p>
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Tool</th>
            <th>Title</th>
            <th>Description</th>
            {showTarget && <th>Evidence</th>}
          </tr>
        </thead>
        <tbody>
          {findings.map((f) => (
            <tr key={f.id}>
              <td>
                <SeverityBadge severity={f.severity} />
              </td>
              <td className="mono">{f.tool_name || '—'}</td>
              <td className="mono">{f.title}</td>
              <td>{f.description || '—'}</td>
              {showTarget && (
                <td className="mono evidence-cell">{f.evidence?.slice(0, 120) || '—'}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
