import { useBIStore, ChartType, CanvasPanel } from '@/stores/biStore'
import {
  BarChart2, TrendingUp, AreaChart, PieChart, Table2,
  CreditCard, Layers, AlignLeft, Maximize2, Minimize2,
  Pin, Trash2, Code, Eye, EyeOff, LayoutGrid, Activity, 
  Map, Target, Circle, Database, MoveRight, Kanban, GitCommit
} from 'lucide-react'
import { useState } from 'react'

const CHART_TYPES: { type: ChartType; label: string; Icon: React.ComponentType<any> }[] = [
  { type: 'bar',          label: 'Bar',          Icon: BarChart2 },
  { type: 'grouped_bar',  label: 'Clustered',    Icon: Layers },
  { type: 'stacked_bar',  label: 'Stacked',      Icon: AlignLeft },
  { type: 'line',         label: 'Line',         Icon: TrendingUp },
  { type: 'area',         label: 'Area',         Icon: AreaChart },
  { type: 'stacked_area', label: 'Stack Area',   Icon: AlignLeft },
  { type: 'pie',          label: 'Pie',          Icon: PieChart },
  { type: 'donut',        label: 'Donut',        Icon: Circle },
  { type: 'scatter',      label: 'Scatter',      Icon: Activity },
  { type: 'heatmap',      label: 'Heatmap',      Icon: LayoutGrid },
  { type: 'treemap',      label: 'Treemap',      Icon: Kanban },
  { type: 'waterfall',    label: 'Waterfall',    Icon: BarChart2 },
  { type: 'gauge',        label: 'Gauge',        Icon: Target },
  { type: 'bullet',       label: 'Bullet',       Icon: Target },
  { type: 'sankey',       label: 'Sankey',       Icon: MoveRight },
  { type: 'geomap',       label: 'Map',          Icon: Map },
  { type: 'kpi_card',     label: 'KPI Card',     Icon: CreditCard },
  { type: 'table',        label: 'Table',        Icon: Table2 },
]

const PBI_COLORS = [
  '#0078D4','#00B7C3','#FF6B35','#8764B8','#FFB900',
  '#107C10','#D13438','#CA5010','#00BCF2','#2D7D9A',
]

export default function VisualizationPanel() {
  const {
    selectedPanelId, pages, activePageId,
    updatePanelChart, movePanelLayout,
    removePanel, pinPanel, updatePanelColor
  } = useBIStore()

  const [showSQL, setShowSQL] = useState(false)

  const activePage = pages.find(p => p.id === activePageId)
  const selectedPanel: CanvasPanel | undefined = activePage?.panels.find(p => p.id === selectedPanelId)

  const handleChartChange = (type: ChartType) => {
    if (!selectedPanelId) return
    updatePanelChart(selectedPanelId, type)
  }

  const handleSizeChange = (w: number, h: number) => {
    if (!selectedPanelId) return
    movePanelLayout(selectedPanelId, { w, h })
  }

  const handleColorChange = (c: string) => {
    if (!selectedPanelId) return
    updatePanelColor(selectedPanelId, c)
  }

  return (
    <div
      style={{
        width: 'var(--viz-w)',
        background: 'var(--surface-panel)',
        borderLeft: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '10px 12px 8px',
          borderBottom: '1px solid var(--border-light)',
          background: 'var(--neutral-10)',
        }}
      >
        <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          Visualizations
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {/* Chart type grid */}
        <div style={{ padding: '10px 10px 4px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-placeholder)', marginBottom: 8, fontWeight: 500 }}>
            CHART TYPE
          </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(5, 1fr)',
                gap: 4,
              }}
            >
              {CHART_TYPES.map(({ type, label, Icon }) => {
                const isActive =
                  selectedPanel?.chartTypeOverride === type ||
                  (!selectedPanel?.chartTypeOverride && selectedPanel?.result.chart?.type === type)
                return (
                  <button
                    key={type}
                    title={label}
                    onClick={() => handleChartChange(type)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '8px',
                      borderRadius: 2,
                      border: isActive ? '1px solid var(--pbi-blue)' : '1px solid transparent',
                      background: isActive ? 'var(--pbi-blue-light)' : 'transparent',
                      color: isActive ? 'var(--pbi-blue)' : 'var(--text-secondary)',
                      cursor: selectedPanel ? 'pointer' : 'default',
                      opacity: selectedPanel ? 1 : 0.5,
                      transition: 'all .12s',
                    }}
                    className="hover-bg-neutral-10"
                  >
                    <Icon size={18} strokeWidth={1.5} />
                  </button>
                )
              })}
            </div>
        </div>

        <div style={{ height: 1, background: 'var(--border-light)', margin: '8px 0' }} />

        {/* Size controls */}
        <div style={{ padding: '0 10px 8px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-placeholder)', marginBottom: 8, fontWeight: 500 }}>
            SIZE
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              className="btn-ghost"
              style={{ flex: 1, justifyContent: 'center', fontSize: 11 }}
              onClick={() => handleSizeChange(2, 1)}
              title="Small"
            >
              <Minimize2 size={12} /> Small
            </button>
            <button
              className="btn-ghost"
              style={{ flex: 1, justifyContent: 'center', fontSize: 11 }}
              onClick={() => handleSizeChange(3, 2)}
              title="Medium"
            >
              <LayoutGrid size={12} /> Med
            </button>
            <button
              className="btn-ghost"
              style={{ flex: 1, justifyContent: 'center', fontSize: 11 }}
              onClick={() => handleSizeChange(6, 3)}
              title="Large"
            >
              <Maximize2 size={12} /> Large
            </button>
          </div>
        </div>

        <div style={{ height: 1, background: 'var(--border-light)', margin: '0 0 8px' }} />

        {/* Color palette */}
        <div style={{ padding: '0 10px 8px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-placeholder)', marginBottom: 8, fontWeight: 500 }}>
            COLORS
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {PBI_COLORS.map(c => {
              const isActive = selectedPanel?.colorOverride === c || 
                               (!selectedPanel?.colorOverride && selectedPanel?.result.chart?.colors?.[0] === c);
              return (
                <div
                  key={c}
                  onClick={() => handleColorChange(c)}
                  style={{
                    width: 18, height: 18,
                    background: c,
                    borderRadius: 2,
                    cursor: selectedPanel ? 'pointer' : 'default',
                    border: isActive ? '2px solid black' : '1px solid rgba(0,0,0,.1)',
                    boxShadow: isActive ? '0 0 0 1px white inset' : 'none',
                    opacity: selectedPanel ? 1 : 0.5,
                    transition: 'all .15s',
                  }}
                  title={c}
                />
              )
            })}
          </div>
        </div>

        <div style={{ height: 1, background: 'var(--border-light)', margin: '0 0 8px' }} />

        {/* Panel actions (when selected) */}
        {selectedPanel && (
          <div style={{ padding: '0 10px 12px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-placeholder)', marginBottom: 8, fontWeight: 500 }}>
              PANEL ACTIONS
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <button
                className="btn-ghost"
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={() => pinPanel(selectedPanel.id)}
              >
                <Pin size={12} />
                {selectedPanel.pinned ? 'Unpin panel' : 'Pin to top'}
              </button>
              {selectedPanel.result.sql && (
                <button
                  className="btn-ghost"
                  style={{ justifyContent: 'flex-start', gap: 8 }}
                  onClick={() => setShowSQL(v => !v)}
                >
                  <Code size={12} />
                  {showSQL ? 'Hide SQL' : 'View SQL'}
                </button>
              )}
              <button
                className="btn-ghost"
                style={{ justifyContent: 'flex-start', gap: 8, color: 'var(--pbi-red)' }}
                onClick={() => removePanel(selectedPanel.id)}
              >
                <Trash2 size={12} />
                Remove panel
              </button>
            </div>

            {/* SQL viewer */}
            {showSQL && selectedPanel.result.sql && (
              <div
                style={{
                  marginTop: 8,
                  padding: 10,
                  background: 'var(--neutral-10)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 2,
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--pbi-blue)',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  maxHeight: 200,
                  overflowY: 'auto',
                }}
              >
                {selectedPanel.result.sql}
              </div>
            )}
          </div>
        )}

        {!selectedPanel && (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-placeholder)', fontSize: 12 }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>🖱️</div>
            Click a chart on the canvas to edit it
          </div>
        )}
      </div>
    </div>
  )
}
