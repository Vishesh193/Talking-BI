import { Database, CheckCircle, XCircle, ExternalLink } from 'lucide-react'
import { useBIStore } from '@/stores/biStore'

export default function ConnectorsPanel() {
  const { connectors, toggleConnectorsPanel } = useBIStore()

  const CONNECTOR_LOGOS: Record<string, string> = {
    sql:        '🗄️',
    powerbi:    '📊',
    salesforce: '☁️',
    shopify:    '🛍️',
    csv:        '📄',
  }

  return (
    <div
      style={{
        width: 'var(--fields-w)',
        background: 'var(--surface-panel)',
        borderRight: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '10px 12px 8px',
          borderBottom: '1px solid var(--border-light)',
          background: 'var(--neutral-10)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <Database size={13} style={{ color: 'var(--pbi-blue)' }} />
        <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.5px', textTransform: 'uppercase', flex: 1 }}>
          Data Sources
        </div>
        <button className="btn-ghost" style={{ fontSize: 11, padding: '2px 6px' }} onClick={toggleConnectorsPanel}>
          ✕
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {connectors.map((c: any) => (
          <div
            key={c.type}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              padding: '10px 10px',
              borderRadius: 2,
              marginBottom: 4,
              border: '1px solid var(--border-light)',
              background: 'var(--surface-card)',
            }}
          >
            <span style={{ fontSize: 20, flexShrink: 0 }}>{CONNECTOR_LOGOS[c.type] || '🔌'}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <span style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-primary)' }}>{c.name}</span>
                {c.connected
                  ? <CheckCircle size={11} style={{ color: 'var(--pbi-green)' }} />
                  : <XCircle size={11} style={{ color: 'var(--neutral-80)' }} />
                }
              </div>
              {c.error && (
                <div style={{ fontSize: 10, color: 'var(--text-placeholder)', lineHeight: 1.4 }}>
                  {c.error}
                </div>
              )}
              {c.connected && c.tables_or_endpoints?.length > 0 && (
                <div style={{ fontSize: 10, color: 'var(--pbi-green)' }}>
                  {c.tables_or_endpoints.join(', ')}
                </div>
              )}
            </div>
            <ExternalLink size={11} style={{ color: 'var(--text-placeholder)', flexShrink: 0 }} />
          </div>
        ))}

        <div style={{ padding: '12px 10px', fontSize: 11, color: 'var(--text-placeholder)', lineHeight: 1.6 }}>
          Configure data sources in your <code style={{ fontSize: 10, background: 'var(--neutral-20)', padding: '1px 4px', borderRadius: 2 }}>.env</code> file.
        </div>
      </div>
    </div>
  )
}
