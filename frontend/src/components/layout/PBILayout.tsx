import { useBIStore } from '@/stores/biStore'
import Ribbon from '@/components/layout/Ribbon'
import FieldsPanel from '@/components/layout/FieldsPanel'
import VisualizationPanel from '@/components/layout/VisualizationPanel'
import PageTabs from '@/components/layout/PageTabs'
import DashboardCanvas from '@/components/dashboard/DashboardCanvas'
import VoiceBar from '@/components/voice/VoiceBar'
import ConnectorsPanel from '@/components/ui/ConnectorsPanel'
import SettingsPanel from '@/components/ui/SettingsPanel'
import QueryHistoryPanel from '@/components/ui/QueryHistoryPanel'

interface Props {
  ws: {
    sendTextQuery: (q: string) => void
    sendVoiceAudio: (b64: string) => void
    sendClarification: (r: string) => void
  }
}

export default function PBILayout({ ws }: Props) {
  const {
    showFieldsPanel, showVizPanel, showConnectorsPanel,
    showSettings,
  } = useBIStore()

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--surface-page)',
      }}
    >
      {/* ── Ribbon ── */}
      <Ribbon onQuery={ws.sendTextQuery} />

      {/* ── Main body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>

        {/* Left: Fields panel */}
        {showFieldsPanel && <FieldsPanel onQuery={ws.sendTextQuery} />}

        {/* Left: Connectors panel (overlay-style, same position) */}
        {showConnectorsPanel && <ConnectorsPanel />}

        {/* Center: Canvas + VoiceBar + PageTabs */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          {/* Query history strip (collapsible) */}
          <QueryHistoryPanel />

          {/* Dashboard canvas */}
          <DashboardCanvas onQuery={ws.sendTextQuery} />

          {/* Voice / text input bar */}
          <VoiceBar ws={ws} />

          {/* Page tabs */}
          <PageTabs />
        </div>

        {/* Right: Visualizations panel */}
        {showVizPanel && <VisualizationPanel />}
      </div>

      {/* ── Settings overlay ── */}
      {showSettings && <SettingsPanel />}
    </div>
  )
}
