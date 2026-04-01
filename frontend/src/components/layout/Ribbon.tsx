import { useState, useRef } from 'react'
import {
  BarChart2, Home, Plus, Download, Settings, Database,
  ChevronDown, Mic, Wand2, RefreshCw, Eye, Grid, FileText,
  Layers, Zap, Link, Save,
} from 'lucide-react'
import { useBIStore } from '@/stores/biStore'
import { apiService } from '@/services/api'
import toast from 'react-hot-toast'
import DownloadMenu from '@/components/ui/DownloadMenu'

interface RibbonProps {
  onQuery: (q: string) => void
}

export default function Ribbon({ onQuery }: RibbonProps) {
  const {
    activeRibbonTab, setActiveRibbonTab,
    wsConnected, agentStage, agentMessage,
    sessionId, setFileAnalysis, addUploadedFile,
    toggleFieldsPanel, toggleVizPanel, toggleConnectorsPanel,
  } = useBIStore()

  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [showDownload, setShowDownload] = useState(false)
  const downloadBtnRef = useRef<HTMLDivElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await apiService.analyzeFile(file, sessionId)
      addUploadedFile({
        file_id: result.file_id,
        filename: result.filename,
        rows: result.rows,
        columns: result.columns,
      })
      setFileAnalysis(result)
      toast.success(`"${result.filename}" analyzed — choose your dashboard`)
    } catch {
      toast.error('Failed to analyze file')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const stageLabelMap: Record<string, string> = {
    idle: wsConnected ? 'Ready' : 'Connecting...',
    listening: 'Listening...',
    transcribing: 'Transcribing...',
    thinking: agentMessage || 'Thinking...',
    querying: 'Querying data...',
    rendering: 'Building chart...',
    done: agentMessage || 'Complete',
    error: agentMessage || 'Error',
  }

  const tabs = [
    { id: 'home', label: 'Home' },
    { id: 'insert', label: 'Insert' },
    { id: 'view', label: 'View' },
    { id: 'data', label: 'Data' },
  ] as const

  return (
    <div
      style={{
        background: 'var(--surface-ribbon)',
        borderBottom: '1px solid var(--border-light)',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      {/* ── Title bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '0 16px',
          height: 44,
          borderBottom: '1px solid var(--border-light)',
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <div
            style={{
              width: 24, height: 24,
              background: 'linear-gradient(135deg, #0078D4, #00B7C3)',
              borderRadius: 3,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <BarChart2 size={14} color="#fff" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
            Talking BI
          </span>
        </div>

        {/* Tab row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveRibbonTab(tab.id)}
              style={{
                padding: '5px 12px',
                fontSize: 13,
                fontWeight: activeRibbonTab === tab.id ? 600 : 400,
                color: activeRibbonTab === tab.id ? 'var(--pbi-blue)' : 'var(--text-secondary)',
                borderRadius: '2px 2px 0 0',
                borderBottom: activeRibbonTab === tab.id ? '2px solid var(--pbi-blue)' : '2px solid transparent',
                marginBottom: -1,
                transition: 'all .15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div className={`status-dot ${
            agentStage === 'error' ? 'error' :
            agentStage !== 'idle' && agentStage !== 'done' ? 'thinking' :
            wsConnected ? 'connected' : 'disconnected'
          }`} />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 200, truncate: 'ellipsis' }}>
            {stageLabelMap[agentStage]}
          </span>
        </div>

        <div style={{ width: 1, height: 20, background: 'var(--border-light)', margin: '0 8px' }} />

        {/* Settings */}
        <button className="btn-icon" title="Settings" onClick={() => useBIStore.getState().setShowSettings(true)}>
          <Settings size={15} />
        </button>
      </div>

      {/* ── Ribbon command area ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          padding: '0 8px',
          height: 52,
          overflowX: 'auto',
        }}
      >
        {activeRibbonTab === 'home' && (
          <>
            {/* Get Data group */}
            <RibbonGroup label="Get Data">
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileUpload} style={{ display: 'none' }} />
              <RibbonBtn
                icon={<Plus size={16} />}
                label={uploading ? 'Analyzing...' : 'Get Data'}
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                primary
              />
              <RibbonBtn icon={<Link size={14} />} label="Connect" onClick={toggleConnectorsPanel} />
              <RibbonBtn icon={<RefreshCw size={14} />} label="Refresh" onClick={() => toast('Data refreshed')} />
            </RibbonGroup>

            <RibbonDivider />

            {/* AI group */}
            <RibbonGroup label="AI Analyst">
              <RibbonBtn icon={<Mic size={16} />} label="Voice" onClick={() => useBIStore.getState().setAgentStage('listening')} primary />
              <RibbonBtn icon={<Wand2 size={14} />} label="Auto Insights" onClick={() => onQuery('Give me key insights and anomalies from the current data')} />
              <RibbonBtn icon={<Zap size={14} />} label="Summarize" onClick={() => onQuery('Summarize the uploaded data in a dashboard')} />
            </RibbonGroup>

            <RibbonDivider />

            {/* Export */}
            <RibbonGroup label="Share">
              <div ref={downloadBtnRef} style={{ position: 'relative' }}>
                <RibbonBtn
                  icon={<Download size={14} />}
                  label="Export"
                  onClick={() => setShowDownload(v => !v)}
                  suffix={<ChevronDown size={10} />}
                />
                {showDownload && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      zIndex: 100,
                      marginTop: 2,
                    }}
                    onMouseLeave={() => setShowDownload(false)}
                  >
                    <DownloadMenu onClose={() => setShowDownload(false)} />
                  </div>
                )}
              </div>
              <RibbonBtn icon={<Save size={14} />} label="Save" onClick={() => toast.success('Dashboard saved')} />
            </RibbonGroup>
          </>
        )}

        {activeRibbonTab === 'view' && (
          <>
            <RibbonGroup label="Panels">
              <RibbonBtn icon={<Layers size={14} />} label="Fields" onClick={toggleFieldsPanel} />
              <RibbonBtn icon={<Grid size={14} />} label="Visualizations" onClick={toggleVizPanel} />
              <RibbonBtn icon={<Database size={14} />} label="Connectors" onClick={toggleConnectorsPanel} />
            </RibbonGroup>
          </>
        )}

        {activeRibbonTab === 'insert' && (
          <>
            <RibbonGroup label="Visualizations">
              {(['bar','line','area','pie','kpi_card','table'] as const).map(type => (
                <RibbonBtn
                  key={type}
                  icon={<BarChart2 size={14} />}
                  label={type.replace('_', ' ')}
                  onClick={() => onQuery(`Show a ${type} chart of the data`)}
                />
              ))}
            </RibbonGroup>
          </>
        )}

        {activeRibbonTab === 'data' && (
          <>
            <RibbonGroup label="Data Sources">
              <RibbonBtn icon={<FileText size={14} />} label="CSV/Excel" onClick={() => fileRef.current?.click()} />
              <RibbonBtn icon={<Database size={14} />} label="SQL" onClick={toggleConnectorsPanel} />
              <RibbonBtn icon={<Eye size={14} />} label="Query Log" onClick={() => toast('Query log coming soon')} />
            </RibbonGroup>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────────────────────

function RibbonGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 2,
        padding: '4px 8px',
        borderRight: '1px solid var(--border-light)',
        minWidth: 'fit-content',
        height: '100%',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 2, paddingBottom: 14 }}>
        {children}
      </div>
      <span
        style={{
          position: 'absolute',
          bottom: 4,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: 10,
          color: 'var(--text-placeholder)',
          letterSpacing: '0.3px',
        }}
      >
        {label}
      </span>
    </div>
  )
}

function RibbonDivider() {
  return <div style={{ width: 1, height: 40, background: 'var(--border-light)', margin: '0 4px', alignSelf: 'center' }} />
}

interface RibbonBtnProps {
  icon: React.ReactNode
  label: string
  onClick?: () => void
  disabled?: boolean
  primary?: boolean
  suffix?: React.ReactNode
}

function RibbonBtn({ icon, label, onClick, disabled, primary, suffix }: RibbonBtnProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        padding: '4px 8px',
        borderRadius: 2,
        minWidth: 44,
        color: primary ? 'var(--pbi-blue)' : 'var(--text-secondary)',
        background: 'transparent',
        fontSize: 11,
        fontWeight: primary ? 600 : 400,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background .12s',
      }}
      className="ribbon-btn"
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--neutral-20)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        {icon}
        {suffix}
      </div>
      <span style={{ whiteSpace: 'nowrap', textTransform: 'capitalize' }}>{label}</span>
    </button>
  )
}
