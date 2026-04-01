import { useBIStore } from '@/stores/biStore'
import { History, ChevronDown, CheckCircle, XCircle, Clock } from 'lucide-react'
import { useState } from 'react'

export default function QueryHistoryPanel() {
  const { queryHistory } = useBIStore()
  const [expanded, setExpanded] = useState(false)
  if (!queryHistory.length) return null

  return (
    <div
      style={{
        borderBottom: '1px solid var(--border-light)',
        background: 'var(--surface-card)',
        flexShrink: 0,
      }}
    >
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 14px',
          fontSize: 12,
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          background: 'transparent',
          borderBottom: expanded ? '1px solid var(--border-light)' : 'none',
        }}
      >
        <History size={12} />
        <span style={{ fontWeight: 500 }}>Query History</span>
        <span className="badge badge-gray" style={{ fontSize: 10 }}>{queryHistory.length}</span>
        <ChevronDown
          size={12}
          style={{ marginLeft: 'auto', transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}
        />
      </button>

      {expanded && (
        <div
          style={{
            display: 'flex',
            gap: 6,
            padding: '6px 14px 8px',
            overflowX: 'auto',
          }}
        >
          {queryHistory.slice(0, 20).map((h, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 8px',
                background: 'var(--neutral-10)',
                border: '1px solid var(--border-light)',
                borderRadius: 2,
                flexShrink: 0,
                maxWidth: 240,
              }}
            >
              {h.success
                ? <CheckCircle size={10} style={{ color: 'var(--pbi-green)', flexShrink: 0 }} />
                : <XCircle size={10} style={{ color: 'var(--pbi-red)', flexShrink: 0 }} />
              }
              <span style={{ fontSize: 11, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {h.transcript}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-placeholder)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2 }}>
                <Clock size={8} />{new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
