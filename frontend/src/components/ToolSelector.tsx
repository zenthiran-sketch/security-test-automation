import type { SelectedTool, ToolCatalogItem } from '../types'

interface Props {
  catalog: ToolCatalogItem[]
  selected: SelectedTool[]
  onChange: (tools: SelectedTool[]) => void
}

export function ToolSelector({ catalog, selected, onChange }: Props) {
  const isSelected = (name: string) => selected.some((t) => t.name === name)

  const toggle = (tool: ToolCatalogItem) => {
    if (isSelected(tool.name)) {
      onChange(selected.filter((t) => t.name !== tool.name))
    } else {
      const params: Record<string, string> = {}
      tool.params.forEach((p) => {
        params[p.name] = p.default || ''
      })
      onChange([...selected, { name: tool.name, params }])
    }
  }

  const updateParam = (toolName: string, paramName: string, value: string) => {
    onChange(
      selected.map((t) =>
        t.name === toolName
          ? { ...t, params: { ...t.params, [paramName]: value } }
          : t,
      ),
    )
  }

  const categories = [...new Set(catalog.map((t) => t.category))]

  return (
    <div className="tool-selector">
      {categories.map((cat) => (
        <div key={cat} className="tool-category">
          <h3>{cat.replace('_', ' ')}</h3>
          <div className="tool-grid">
            {catalog
              .filter((t) => t.category === cat)
              .map((tool) => (
                <label
                  key={tool.name}
                  className={`tool-card ${isSelected(tool.name) ? 'selected' : ''} ${tool.available === false ? 'unavailable' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected(tool.name)}
                    onChange={() => toggle(tool)}
                  />
                  <div>
                    <strong>
                      {tool.label}{' '}
                      <span className={`avail-badge ${tool.available ? 'ok' : 'missing'}`}>
                        {tool.available ? 'on PATH' : 'missing'}
                      </span>
                    </strong>
                    <p>{tool.description}</p>
                  </div>
                </label>
              ))}
          </div>
        </div>
      ))}

      {selected.length > 0 && (
        <div className="tool-params-panel">
          <h3>Tool Parameters</h3>
          {selected.map((sel) => {
            const meta = catalog.find((t) => t.name === sel.name)
            if (!meta) return null
            return (
              <div key={sel.name} className="tool-params-group">
                <h4>{meta.label}</h4>
                {meta.params.map((p) => (
                  <label key={p.name} className="field">
                    <span>{p.label}</span>
                    {p.type === 'select' && p.options ? (
                      <select
                        value={sel.params[p.name] ?? p.default}
                        onChange={(e) => updateParam(sel.name, p.name, e.target.value)}
                      >
                        {p.options.map((o) => (
                          <option key={o} value={o}>
                            {o}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={sel.params[p.name] ?? p.default}
                        onChange={(e) => updateParam(sel.name, p.name, e.target.value)}
                      />
                    )}
                  </label>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
