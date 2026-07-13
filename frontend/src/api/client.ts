import type {
  HealthResponse,
  Report,
  Scan,
  SelectedTool,
  ToolCatalogItem,
} from '../types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    })
  } catch {
    throw new Error(
      'Cannot reach API server. Start it with: start.bat or python start.py (port 8888)',
    )
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    if (res.status === 502) {
      throw new Error(
        'API server not running on port 8888. Run: start.bat or python start.py',
      )
    }
    throw new Error(body.error || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  getHealth: () => request<HealthResponse>('/health'),

  getToolCatalog: () =>
    request<{ tools: ToolCatalogItem[]; count: number; available_count: number }>(
      '/api/tools/catalog',
    ),

  listScans: (status?: string) => {
    const q = status ? `?status=${status}` : ''
    return request<{ scans: Scan[]; count: number }>(`/api/scans${q}`)
  },

  getScan: (id: string) => request<Scan>(`/api/scans/${id}`),

  createScan: (target: string, tools: SelectedTool[], name?: string) =>
    request<{ success: boolean; scan: Scan }>('/api/scans', {
      method: 'POST',
      body: JSON.stringify({ target, tools, name }),
    }),

  createAllWebScan: (target: string, name?: string) =>
    request<{ success: boolean; scan: Scan }>('/api/scans', {
      method: 'POST',
      body: JSON.stringify({ target, mode: 'all_web', name }),
    }),

  cancelScan: (id: string) =>
    request<{ success: boolean }>(`/api/scans/${id}/cancel`, { method: 'POST' }),

  listReports: () =>
    request<{ reports: Report[]; count: number }>('/api/reports'),

  getReport: (id: string) => request<Report>(`/api/reports/${id}`),

  exportReport: (id: string) =>
    request<{ success: boolean; export: Report }>(`/api/reports/${id}/export`, {
      method: 'POST',
    }),

  deleteReport: (id: string) =>
    request<{ success: boolean }>(`/api/reports/${id}`, { method: 'DELETE' }),

  getProcessDashboard: () =>
    request<{
      system_load: { cpu_percent: number; memory_percent: number; active_connections: number }
      total_processes: number
      processes: Array<{ pid: number; command: string; status: string; progress_percent: string }>
    }>('/api/processes/dashboard'),

  subscribeScanEvents: (scanId: string, onEvent: (data: unknown) => void) => {
    const source = new EventSource(`/api/scans/${scanId}/stream`)
    source.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data))
      } catch {
        /* ignore parse errors */
      }
    }
    return source
  },
}
