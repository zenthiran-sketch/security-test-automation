import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { NewScan } from './pages/NewScan'
import { ScanDetail } from './pages/ScanDetail'
import { ReportConsole } from './pages/ReportConsole'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="scan/new" element={<NewScan />} />
            <Route path="scan/:id" element={<ScanDetail />} />
            <Route path="reports" element={<ReportConsole />} />
            <Route path="reports/:id" element={<ReportConsole />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
