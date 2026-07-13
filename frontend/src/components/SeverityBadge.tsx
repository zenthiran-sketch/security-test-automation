interface Props {
  severity: string
}

const COLORS: Record<string, string> = {
  critical: '#ff2d55',
  high: '#ff6b35',
  medium: '#ffb020',
  low: '#4dabf7',
  info: '#868e96',
}

export function SeverityBadge({ severity }: Props) {
  const key = severity.toLowerCase()
  const color = COLORS[key] || COLORS.info
  return (
    <span className="severity-badge" style={{ borderColor: color, color }}>
      {severity.toUpperCase()}
    </span>
  )
}
