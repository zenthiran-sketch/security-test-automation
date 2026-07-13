import { useState } from 'react'

interface Props {
  stdout?: string
  stderr?: string
  toolName?: string
}

export function OutputViewer({ stdout = '', stderr = '', toolName }: Props) {
  const [tab, setTab] = useState<'stdout' | 'stderr'>('stdout')
  const content = tab === 'stdout' ? stdout : stderr

  return (
    <div className="output-viewer">
      {toolName && <div className="output-viewer-title">{toolName}</div>}
      <div className="output-tabs">
        <button
          type="button"
          className={tab === 'stdout' ? 'active' : ''}
          onClick={() => setTab('stdout')}
        >
          stdout ({stdout.length})
        </button>
        <button
          type="button"
          className={tab === 'stderr' ? 'active' : ''}
          onClick={() => setTab('stderr')}
        >
          stderr ({stderr.length})
        </button>
      </div>
      <pre className="output-content">{content || '(empty)'}</pre>
    </div>
  )
}
