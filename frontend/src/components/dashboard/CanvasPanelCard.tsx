import { X, Pin, Code, BarChart2, Clock, Database, AlertTriangle, TrendingUp, TrendingDown, Minus, FileDown, MoreVertical } from 'lucide-react'
import { useBIStore, CanvasPanel, ChartType } from '@/stores/biStore'
import ChartRenderer from '@/components/charts/ChartRenderer'
import DataQualityBadge from './DataQualityBadge'
import SuggestionChips from './SuggestionChips'
import { useWebSocket } from '@/hooks/useWebSocket'
import axios from 'axios'
import toast from 'react-hot-toast'

interface Props {
  panel: CanvasPanel
}

export default function CanvasPanelCard({ panel }: Props) {
  const { selectedPanelId, setSelectedPanelId, removePanel, pinPanel } = useBIStore()
  const { sendTextQuery } = useWebSocket()
  const { result, chartTypeOverride } = panel
  const isSelected = selectedPanelId === panel.id

  const effectiveChartConfig = chartTypeOverride
    ? { ...result.chart!, type: chartTypeOverride as ChartType }
    : result.chart

  // Build final effectiveChart applying the color override
  const effectiveChart = effectiveChartConfig ? {
    ...effectiveChartConfig,
    colors: panel.colorOverride 
      ? [panel.colorOverride, ...(effectiveChartConfig.colors?.slice(1) || [])]
      : effectiveChartConfig.colors
  } : undefined

  const intentTag = result.intent
    ? `${result.intent.type} · ${result.intent.metric || '?'}`
    : 'query'

  const handleExport = async (format: 'pdf' | 'excel') => {
    const loading = toast.loading(`Generating ${format.toUpperCase()}...`)
    try {
      const response = await axios.post(`/api/export/${format}`, {
        title: effectiveChart?.title || result.transcript,
        insights: result.insights,
        data: effectiveChart?.data || [],
        strategies: result.strategies,
        tts_text: result.tts_text
      }, { responseType: 'blob' })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `TalkingBI_Export_${panel.id}.${format === 'pdf' ? 'pdf' : 'xlsx'}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success(`${format.toUpperCase()} exported!`, { id: loading })
    } catch (err) {
      toast.error('Export failed', { id: loading })
    }
  }

  return (
    <div
      onClick={() => setSelectedPanelId(isSelected ? null : panel.id)}
      style={{
        background: '#FFFFFF',
        border: `1px solid ${isSelected ? 'var(--pbi-blue)' : 'rgba(0,0,0,0.07)'}`,
        boxShadow: isSelected
          ? '0 0 0 2px var(--pbi-blue), 0 2px 8px rgba(0,0,0,0.12)'
          : '0 1px 4px rgba(0,0,0,0.08), 0 0.5px 1.5px rgba(0,0,0,0.06)',
        borderRadius: 12,
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
            <DataQualityBadge quality={result.quality} />
          </div>
        </div>

        {/* Actions — stop propagation */}
        <div
          style={{ display: 'flex', gap: 2, flexShrink: 0 }}
          onClick={e => e.stopPropagation()}
        >
          <button className="btn-icon" onClick={() => handleExport('pdf')} title="Export PDF"><FileDown size={11} /></button>
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

      {/* AI Suggestions */}
      {result.suggestions && result.suggestions.length > 0 && (
        <SuggestionChips
          suggestions={result.suggestions}
          onSuggestionClick={(q) => sendTextQuery(q)}
        />
      )}

      {/* Footer transcript */}
      <div
        style={{
          padding: '4px 12px',
          fontSize: 10,
          color: 'var(--text-placeholder)',
          borderTop: '1px solid var(--border-light)',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          flexShrink: 0,
        }}
      >
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={`"${result.transcript}"`}>
           "{result.transcript}"
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-placeholder)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 3 }}>
           <Clock size={9} />{result.execution_time_ms?.toFixed(0)}ms
           {result.row_count > 0 && ` · ${result.row_count} rows`}
        </span>
      </div>
    </div>
  )
}
