import { X, Pin, Code, BarChart2, Clock, Database, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useBIStore, CanvasPanel, ChartType } from '@/stores/biStore'
import ChartRenderer from '@/components/charts/ChartRenderer'

interface Props {
  panel: CanvasPanel
}

export default function CanvasPanelCard({ panel }: Props) {
  const { selectedPanelId, setSelectedPanelId, removePanel, pinPanel } = useBIStore()
  const { result, chartTypeOverride } = panel
  const isSelected = selectedPanelId === panel.id

  const effectiveChart = chartTypeOverride
    ? { ...result.chart!, type: chartTypeOverride as ChartType }
    : result.chart

  const intentTag = result.intent
    ? `${result.intent.type} · ${result.intent.metric || '?'}`
    : 'query'

  return (
    <div
      onClick={() => setSelectedPanelId(isSelected ? null : panel.id)}
      style={{
        background: 'var(--surface-card)',
        border: `1px solid ${isSelected ? 'var(--pbi-blue)' : 'var(--border-light)'}`,
        boxShadow: isSelected
          ? '0 0 0 1px var(--pbi-blue), var(--shadow-card)'
          : 'var(--shadow-card)',
        borderRadius: 2,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'box-shadow .15s, border-color .15s',
        height: '100%',
        position: 'relative',
      }}
    >
      {/* Selected indicator */}
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            top: 0, left: 0, right: 0,
            height: 2,
            background: 'var(--pbi-blue)',
            zIndex: 1,
          }}
        />
      )}

      {/* Panel header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 10px',
          borderBottom: '1px solid var(--border-light)',
          background: panel.pinned ? 'var(--pbi-blue-light)' : 'var(--neutral-10)',
          flexShrink: 0,
        }}
      >
        <BarChart2 size={13} style={{ color: 'var(--pbi-blue)', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--text-primary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {effectiveChart?.title || result.transcript}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <span className="badge badge-blue" style={{ fontSize: 10 }}>{intentTag}</span>
            {result.data_source_used && (
              <span style={{ fontSize: 10, color: 'var(--text-placeholder)', display: 'flex', alignItems: 'center', gap: 3 }}>
                <Database size={9} />{result.data_source_used.replace('_', ' ')}
              </span>
            )}
            <span style={{ fontSize: 10, color: 'var(--text-placeholder)', display: 'flex', alignItems: 'center', gap: 3, marginLeft: 'auto' }}>
              <Clock size={9} />{result.execution_time_ms?.toFixed(0)}ms
            </span>
          </div>
        </div>

        {/* Actions — stop propagation */}
        <div
          style={{ display: 'flex', gap: 2, flexShrink: 0 }}
          onClick={e => e.stopPropagation()}
        >
          <button
            className="btn-icon"
            style={{ width: 22, height: 22, color: panel.pinned ? 'var(--pbi-blue)' : undefined }}
            onClick={() => pinPanel(panel.id)}
            title={panel.pinned ? 'Unpin' : 'Pin'}
          >
            <Pin size={11} />
          </button>
          <button
            className="btn-icon"
            style={{ width: 22, height: 22, color: 'var(--pbi-red)' }}
            onClick={() => removePanel(panel.id)}
            title="Remove"
          >
            <X size={11} />
          </button>
        </div>
      </div>

      {/* Error state */}
      {result.error && (
        <div
          style={{
            padding: '8px 12px',
            background: '#FDE7E9',
            borderBottom: '1px solid #F1707B',
            display: 'flex',
            gap: 8,
            alignItems: 'center',
          }}
        >
          <AlertTriangle size={13} style={{ color: 'var(--pbi-red)', flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: 'var(--pbi-red)' }}>{result.error}</span>
        </div>
      )}

      {/* Chart area */}
      {effectiveChart && !result.error && (
        <div style={{ flex: 1, padding: '12px 12px 8px', overflow: 'hidden', minHeight: 0 }}>
          <ChartRenderer config={effectiveChart} />
        </div>
      )}

      {/* Insights strip */}
      {result.insights?.length > 0 && (
        <div
          style={{
            borderTop: '1px solid var(--border-light)',
            padding: '8px 12px',
            display: 'flex',
            gap: 8,
            overflowX: 'auto',
            flexShrink: 0,
          }}
        >
          {result.insights.slice(0, 3).map((ins, i) => {
            const dir = ins.direction || 'neutral'
            const Icon = dir === 'up' ? TrendingUp : dir === 'down' ? TrendingDown : Minus
            const color = dir === 'up' ? 'var(--pbi-green)' : dir === 'down' ? 'var(--pbi-red)' : 'var(--neutral-80)'
            return (
              <div
                key={i}
                style={{
                  flexShrink: 0,
                  maxWidth: 220,
                  padding: '4px 8px',
                  background: 'var(--neutral-10)',
                  borderLeft: `3px solid ${color}`,
                  borderRadius: '0 2px 2px 0',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                  <Icon size={11} style={{ color, flexShrink: 0 }} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ins.title}
                  </span>
                </div>
                <p style={{ fontSize: 10, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  {ins.body}
                </p>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer transcript */}
      <div
        style={{
          padding: '4px 12px',
          fontSize: 10,
          color: 'var(--text-placeholder)',
          borderTop: '1px solid var(--border-light)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
        title={`"${result.transcript}"`}
      >
        "{result.transcript}"
        {result.row_count > 0 && ` · ${result.row_count} rows`}
      </div>
    </div>
  )
}
