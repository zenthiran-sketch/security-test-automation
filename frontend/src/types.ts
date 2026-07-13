export interface ToolParam {
  name: string
  type: string
  default: string
  label: string
  options?: string[]
}

export interface ToolCatalogItem {
  name: string
  label: string
  category: string
  description: string
  params: ToolParam[]
  available?: boolean
  profile?: string
  target_kind?: string
  binary?: string
}

export interface ScanJob {
  id: string
  scan_id: string
  tool_name: string
  status: string
  params_json: string
  stdout?: string
  stderr?: string
  return_code?: number
  execution_time?: number
  started_at?: string
  completed_at?: string
}

export interface Finding {
  id: string
  scan_id: string
  job_id?: string
  severity: string
  title: string
  description?: string
  evidence?: string
  tool_name?: string
  created_at: string
}

export interface Scan {
  id: string
  name: string
  target: string
  status: string
  created_at: string
  completed_at?: string
  config_json: string
  jobs?: ScanJob[]
  findings?: Finding[]
  findings_count?: number
}

export interface ReportSummaryLegacy {
  scan_id: string
  target: string
  total_findings: number
  critical: number
  high: number
  medium: number
  low: number
  info: number
  tools_executed: string[]
  tools_failed: string[]
}

export interface MasterDigest {
  scan_id: string
  target: string
  status?: string
  duration_seconds?: number | null
  risk_score?: number
  executive_summary?: {
    total_findings: number
    critical: number
    high: number
    medium: number
    low: number
    info: number
    tools_executed: string[]
    tools_failed: string[]
    tools_skipped?: string[]
    tools_total?: number
  }
  attack_surface?: {
    open_ports: Array<{ port: string; proto: string; evidence?: string }>
    subdomains: string[]
    endpoints: string[]
  }
  findings_board?: Finding[]
  tool_failures?: Array<{ tool: string; status: string; reason: string }>
  generated_at?: string
  // legacy flat fields still possible
  total_findings?: number
  critical?: number
  high?: number
  medium?: number
  low?: number
  info?: number
  tools_executed?: string[]
  tools_failed?: string[]
}

export type ReportSummary = ReportSummaryLegacy & MasterDigest

export interface Report {
  id: string
  scan_id: string
  title: string
  summary_json: string
  summary?: ReportSummary
  created_at: string
  target?: string
  scan_name?: string
  scan_status?: string
  findings?: Finding[]
  jobs?: ScanJob[]
  job_outputs?: Array<{
    id: string
    tool_name: string
    status: string
    stdout?: string
    stderr?: string
    return_code?: number
    execution_time?: number
  }>
}

export interface HealthResponse {
  status: string
  version: string
  total_tools_available: number
  total_tools_count: number
  database?: { status: string; path?: string }
  system_load?: { cpu_percent: number; memory_percent: number }
}

export interface SelectedTool {
  name: string
  params: Record<string, string>
}

export interface SseEvent {
  type: string
  scan_id?: string
  tool?: string
  job_id?: string
  status?: string
  findings_count?: number
  execution_time?: number
  timestamp?: string
  reason?: string
}
