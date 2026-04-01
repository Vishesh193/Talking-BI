import { X, Volume2, VolumeX, Trash2, Info, Wifi, WifiOff } from 'lucide-react'
import { useBIStore } from '@/stores/biStore'

export default function SettingsPanel() {
  const {
    setShowSettings, ttsEnabled, toggleTts,
    wsConnected, sessionId, clearPage,
    connectors, uploadedFiles, queryHistory, pages,
  } = useBIStore()

  const totalPanels = pages.reduce((sum, p) => sum + p.panels.length, 0)

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(0,0,0,.35)',
        zIndex: 300,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'flex-end',
      }}
      onClick={() => setShowSettings(false)}
    >
      <div
        style={{
          width: 360,
          height: '100%',
          background: 'var(--surface-panel)',
          borderLeft: '1px solid var(--border-light)',
          boxShadow: 'var(--shadow-modal)',
          overflow: 'auto',
          animation: 'slideRight .2s ease',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '14px 16px',
            borderBottom: '1px solid var(--border-light)',
            background: 'var(--neutral-10)',
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 15, flex: 1, color: 'var(--text-primary)' }}>
            Settings
          </span>
          <button className="btn-icon" onClick={() => setShowSettings(false)}>
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '16px' }}>
          {/* Session */}
          <Section title="Session">
            <InfoRow
              icon={wsConnected ? <Wifi size={13} style={{ color: 'var(--pbi-green)' }} /> : <WifiOff size={13} style={{ color: 'var(--neutral-80)' }} />}
              label="WebSocket"
              value={wsConnected ? 'Connected' : 'Disconnected'}
              valueColor={wsConnected ? 'var(--pbi-green)' : 'var(--neutral-80)'}
            />
            <InfoRow icon={<Info size={13} />} label="Session ID" value={sessionId.slice(0, 24) + '...'} mono />
          </Section>

          {/* Voice */}
          <Section title="Voice & TTS">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 0',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {ttsEnabled
                  ? <Volume2 size={14} style={{ color: 'var(--pbi-blue)' }} />
                  : <VolumeX size={14} style={{ color: 'var(--neutral-80)' }} />
                }
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Text-to-Speech
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-placeholder)' }}>
                    Read insights aloud using browser voices
                  </div>
                </div>
              </div>
              <Toggle checked={ttsEnabled} onChange={toggleTts} />
            </div>
          </Section>

          {/* Stats */}
          <Section title="Dashboard Stats">
            <InfoRow icon={<Info size={13} />} label="Pages" value={String(pages.length)} />
            <InfoRow icon={<Info size={13} />} label="Total panels" value={String(totalPanels)} />
            <InfoRow icon={<Info size={13} />} label="Queries run" value={String(queryHistory.length)} />
            <InfoRow icon={<Info size={13} />} label="Files loaded" value={String(uploadedFiles.length)} />
          </Section>

          {/* Connectors */}
          {connectors.length > 0 && (
            <Section title="Connector Status">
              {connectors.map((c: any) => (
                <InfoRow
                  key={c.type}
                  icon={<div style={{ width: 8, height: 8, borderRadius: 4, background: c.connected ? 'var(--pbi-green)' : 'var(--neutral-60)', flexShrink: 0 }} />}
                  label={c.name}
                  value={c.connected ? 'Connected' : 'Disconnected'}
                  valueColor={c.connected ? 'var(--pbi-green)' : 'var(--neutral-80)'}
                />
              ))}
            </Section>
          )}

          {/* Danger zone */}
          <Section title="Reset">
            <button
              className="btn-secondary"
              style={{ width: '100%', justifyContent: 'center', color: 'var(--pbi-red)', borderColor: 'var(--pbi-red)' }}
              onClick={() => { clearPage(); }}
            >
              <Trash2 size={13} />
              Clear current page
            </button>
          </Section>
        </div>
      </div>
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: 'var(--text-placeholder)',
          letterSpacing: '0.6px',
          textTransform: 'uppercase',
          marginBottom: 10,
          paddingBottom: 6,
          borderBottom: '1px solid var(--border-light)',
        }}
      >
        {title}
      </div>
      {children}
    </div>
  )
}

function InfoRow({
  icon, label, value, mono = false, valueColor,
}: {
  icon: React.ReactNode
  label: string
  value: string
  mono?: boolean
  valueColor?: string
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', color: 'var(--text-secondary)' }}>
      <div style={{ color: 'var(--neutral-80)', flexShrink: 0 }}>{icon}</div>
      <span style={{ flex: 1, fontSize: 12 }}>{label}</span>
      <span
        style={{
          fontSize: 12,
          fontFamily: mono ? 'var(--font-mono)' : undefined,
          color: valueColor || 'var(--text-primary)',
          fontWeight: 500,
        }}
      >
        {value}
      </span>
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <div
      onClick={onChange}
      style={{
        width: 40, height: 22,
        background: checked ? 'var(--pbi-blue)' : 'var(--neutral-60)',
        borderRadius: 11,
        position: 'relative',
        cursor: 'pointer',
        transition: 'background .2s',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 3,
          left: checked ? 21 : 3,
          width: 16, height: 16,
          background: '#fff',
          borderRadius: 8,
          transition: 'left .2s',
          boxShadow: '0 1px 3px rgba(0,0,0,.2)',
        }}
      />
    </div>
  )
}
