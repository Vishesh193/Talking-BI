import { useBIStore, CanvasPanel, DashboardPage, DashboardAdvancedMeta } from '@/stores/biStore'
import CanvasPanelCard from './CanvasPanelCard'
import EmptyCanvas from './EmptyCanvas'
import StrategicActions from './StrategicActions'
import SimulationResultView from './SimulationResultView'

interface Props {
  onQuery: (q: string) => void
}

// ─── Filter Pill ─────────────────────────────────────────────────────────────
function FilterPill({ label, color }: { label: string; color?: string }) {
  const bg = color || '#3C3489'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 12px',
        borderRadius: 999,
        backgroundColor: bg,
        color: '#fff',
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: 0.3,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}

// ─── Dashboard Header ─────────────────────────────────────────────────────────
function DashboardHeader({
  title,
  filterPills,
  paletteColors,
}: {
  title?: string
  filterPills?: { label: string }[]
  paletteColors?: string[]
}) {
  const pillColors = paletteColors && paletteColors.length >= 3
    ? [paletteColors[0], paletteColors[1], paletteColors[2]]
    : ['#3C3489', '#854F0B', '#0F6E56']

  if (!title && (!filterPills || filterPills.length === 0)) return null

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
        flexWrap: 'wrap',
        gap: 8,
      }}
    >
      {title && (
        <h1
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '-0.3px',
            margin: 0,
          }}
        >
          {title}
        </h1>
      )}
      {filterPills && filterPills.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {filterPills.map((pill, i) => (
            <FilterPill key={i} label={pill.label} color={pillColors[i % pillColors.length]} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function DashboardCanvas({ onQuery }: Props) {
  const { pages, activePageId } = useBIStore()
  const activePage = pages.find((p: DashboardPage) => p.id === activePageId)
  const panels: CanvasPanel[] = activePage?.panels || []

  if (panels.length === 0) {
    return <EmptyCanvas onQuery={onQuery} />
  }

  // ── Separate KPI cards vs chart panels ────────────────────────────────────
  const kpiPanels    = panels.filter((p: CanvasPanel) => (p.chartTypeOverride || p.result.chart?.type) === 'kpi_card')
  const normalPanels = panels.filter((p: CanvasPanel) => (p.chartTypeOverride || p.result.chart?.type) !== 'kpi_card')

  // ── Detect advanced dashboard metadata ────────────────────────────────────
  // Stored on the page when the 6-step agent generates the dashboard
  const meta: DashboardAdvancedMeta | undefined = (activePage as any)?.advancedMeta

  const paletteColors = meta?.colors
    ? [meta.colors.primary, meta.colors.secondary, meta.colors.positive, meta.colors.negative].filter(Boolean)
    : undefined

  const bgColor = meta?.colors?.background || 'var(--surface-page)'

  // ── Advanced layout: try to reconstruct 4-row structure ───────────────────
  // Row 1: kpi cards (up to 4)
  // Row 2: first wide panel left + donut right
  // Row 3: next 3 normal panels
  // Row 4: last 2 normal panels
  const isAdvanced = kpiPanels.length >= 3 && normalPanels.length >= 4

  const pinnedPanels  = normalPanels.filter((p: CanvasPanel) => p.pinned)
  const otherPanels   = normalPanels.filter((p: CanvasPanel) => !p.pinned)

  // Collect all strategies & simulations
  const allStrategies = panels.flatMap((p: CanvasPanel) => p.result.strategies || []).slice(0, 4)
  const lastSimulation = panels.find((p: CanvasPanel) => p.result.simulation)?.result.simulation

  return (
    <div
      id="dashboard-canvas"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: 20,
        background: bgColor,
      }}
    >
      {/* Dashboard header with title + filter pills */}
      <DashboardHeader
        title={meta?.dashboard_title}
        filterPills={meta?.filter_pills}
        paletteColors={paletteColors}
      />

      {isAdvanced ? (
        // ── ADVANCED FIXED LAYOUT ──────────────────────────────────────────
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* ROW 1: 4 KPI Cards — equal columns */}
          {kpiPanels.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${Math.min(kpiPanels.length, 4)}, 1fr)`,
                gap: 12,
              }}
            >
              {kpiPanels.slice(0, 4).map((panel: CanvasPanel) => (
                <div key={panel.id} className="fade-in" style={{ minHeight: 110 }}>
                  <CanvasPanelCard panel={panel} />
                </div>
              ))}
            </div>
          )}

          {/* ROW 2: Large chart (65%) + Donut (35%) */}
          {otherPanels.length >= 2 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr',
                gap: 12,
              }}
            >
              <div className="fade-in" style={{ minHeight: 280 }}>
                <CanvasPanelCard panel={otherPanels[0]} />
              </div>
              <div className="fade-in" style={{ minHeight: 280 }}>
                <CanvasPanelCard panel={otherPanels[1]} />
              </div>
            </div>
          )}

          {/* ROW 3: 3 Equal Cards */}
          {otherPanels.length >= 5 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 12,
              }}
            >
              {otherPanels.slice(2, 5).map((panel: CanvasPanel) => (
                <div key={panel.id} className="fade-in" style={{ minHeight: 240 }}>
                  <CanvasPanelCard panel={panel} />
                </div>
              ))}
            </div>
          )}

          {/* ROW 4: 2 Equal Cards */}
          {otherPanels.length >= 7 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 12,
              }}
            >
              {otherPanels.slice(5, 7).map((panel: CanvasPanel) => (
                <div key={panel.id} className="fade-in" style={{ minHeight: 240 }}>
                  <CanvasPanelCard panel={panel} />
                </div>
              ))}
            </div>
          )}

          {/* Any overflow panels (shouldn't happen, but safety net) */}
          {otherPanels.length > 7 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
                gap: 12,
              }}
            >
              {otherPanels.slice(7).map((panel: CanvasPanel) => (
                <div key={panel.id} className="fade-in" style={{ minHeight: 240 }}>
                  <CanvasPanelCard panel={panel} />
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        // ── STANDARD FREEFORM LAYOUT ───────────────────────────────────────
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* KPI strip */}
          {kpiPanels.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${Math.min(kpiPanels.length, 5)}, 1fr)`,
                gap: 12,
              }}
            >
              {kpiPanels.map((panel: CanvasPanel) => (
                <div key={panel.id} style={{ minHeight: 100 }} className="fade-in">
                  <CanvasPanelCard panel={panel} />
                </div>
              ))}
            </div>
          )}

          {/* Pinned panels — full width */}
          {pinnedPanels.map((panel: CanvasPanel) => (
            <div key={panel.id} style={{ minHeight: 320 }} className="fade-in">
              <CanvasPanelCard panel={panel} />
            </div>
          ))}

          {/* Normal panels — 2-column responsive grid */}
          {otherPanels.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
                gap: 12,
              }}
            >
              {otherPanels.map((panel: CanvasPanel) => {
                const isWide = panel.w >= 5
                return (
                  <div
                    key={panel.id}
                    style={{ minHeight: 280, gridColumn: isWide ? '1 / -1' : undefined }}
                    className="fade-in"
                  >
                    <CanvasPanelCard panel={panel} />
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Strategic Intelligence Summary */}
      {(allStrategies.length > 0 || lastSimulation) && (
        <div style={{ marginTop: 24, padding: '16px 0', borderTop: '1px solid var(--border-light)' }}>
          {lastSimulation && <SimulationResultView simulation={lastSimulation} />}
          <StrategicActions strategies={allStrategies} />
        </div>
      )}
    </div>
  )
}
