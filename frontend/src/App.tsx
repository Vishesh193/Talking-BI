import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useBIStore } from '@/stores/biStore'
import { apiService } from '@/services/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import PBILayout from '@/components/layout/PBILayout'
import DashboardSuggestionsModal from '@/components/modals/DashboardSuggestionsModal'

export default function App() {
  const { setConnectors, fileAnalysis } = useBIStore()
  const ws = useWebSocket()

  const { data: connectors } = useQuery({
    queryKey: ['connectors'],
    queryFn: apiService.getConnectors,
    refetchInterval: 30000,
  })

  useEffect(() => {
    if (connectors) setConnectors(connectors)
  }, [connectors, setConnectors])

  return (
    <>
      <PBILayout ws={ws} />
      {fileAnalysis && <DashboardSuggestionsModal ws={ws} />}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            fontFamily: 'var(--font-ui)',
            fontSize: '13px',
            background: 'var(--surface-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-light)',
            boxShadow: 'var(--shadow-panel)',
            borderRadius: '2px',
          },
          success: { iconTheme: { primary: '#107C10', secondary: '#fff' } },
          error: { iconTheme: { primary: '#D13438', secondary: '#fff' } },
        }}
      />
    </>
  )
}
