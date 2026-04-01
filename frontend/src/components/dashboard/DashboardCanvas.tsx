import { useBIStore } from '@/stores/biStore'
import CanvasPanelCard from './CanvasPanelCard'
import EmptyCanvas from './EmptyCanvas'

interface Props {
  onQuery: (q: string) => void
}

export default function DashboardCanvas({ onQuery }: Props) {
  const { pages, activePageId } = useBIStore()
  const activePage = pages.find(p => p.id === activePageId)
  const panels = activePage?.panels || []

  if (panels.length === 0) {
    return <EmptyCanvas onQuery={onQuery} />
  }

  // Responsive masonry-ish grid: 2 columns for medium panels, 1 for large, flex for KPI cards
  const kpiPanels    = panels.filter(p => (p.chartTypeOverride || p.result.chart?.type) === 'kpi_card')
  const normalPanels = panels.filter(p => (p.chartTypeOverride || p.result.chart?.type) !== 'kpi_card')
  const pinnedPanels = normalPanels.filter(p => p.pinned)
  const otherPanels  = normalPanels.filter(p => !p.pinned)

  return (
    <div
      id="dashboard-canvas"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: 16,
        background: 'var(--surface-page)',
      }}
    >
      {/* KPI strip */}
      {kpiPanels.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${Math.min(kpiPanels.length, 5)}, 1fr)`,
            gap: 12,
            marginBottom: 12,
          }}
        >
          {kpiPanels.map(panel => (
            <div key={panel.id} style={{ minHeight: 100 }} className="fade-in">
              <CanvasPanelCard panel={panel} />
            </div>
          ))}
        </div>
      )}

      {/* Pinned panels — full width */}
      {pinnedPanels.map(panel => (
        <div
          key={panel.id}
          style={{ marginBottom: 12, minHeight: 320 }}
          className="fade-in"
        >
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
          {otherPanels.map(panel => {
            const isWide = panel.w >= 5
            return (
              <div
                key={panel.id}
                style={{
                  minHeight: 280,
                  gridColumn: isWide ? '1 / -1' : undefined,
                }}
                className="fade-in"
              >
                <CanvasPanelCard panel={panel} />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
