import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import type { ChartConfig } from '@/stores/biStore'
import DataTable from './DataTable'

interface Props {
  config: ChartConfig
  compact?: boolean
}

// ─── Light-theme chart styles ────────────────────────────────────────────────
const TICK_STYLE = {
  fontSize: 11,
  fontFamily: 'Segoe UI, Inter, sans-serif',
  fill: '#605E5C',
}
const GRID_STROKE = '#EDEBE9'
const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#FFFFFF',
    border: '1px solid #EDEBE9',
    borderRadius: '2px',
    fontFamily: 'Segoe UI, Inter, sans-serif',
    fontSize: '12px',
    color: '#201F1E',
    boxShadow: '0 2px 8px rgba(0,0,0,.12)',
  },
  labelStyle: { color: '#605E5C', marginBottom: 4, fontWeight: 600 },
  cursor: { fill: 'rgba(0,120,212,0.05)' },
}
const LEGEND_STYLE = {
  wrapperStyle: {
    fontSize: 11,
    fontFamily: 'Segoe UI, sans-serif',
    color: '#605E5C',
    paddingTop: 8,
  },
}

const DEFAULT_COLORS = ['#0078D4','#00B7C3','#FF6B35','#8764B8','#FFB900','#107C10','#D13438']

function fmt(value: any, unit?: string) {
  if (typeof value !== 'number') return String(value ?? '')
  if (unit === '$') {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
    return `$${value.toFixed(0)}`
  }
  if (unit === '%') return `${value.toFixed(1)}%`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toLocaleString()
}

export default function ChartRenderer({ config, compact }: Props) {
  const height = compact ? 160 : 240
  const colors = config.colors?.length ? config.colors : DEFAULT_COLORS

  if (!config || !config.data?.length) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: 120,
          color: 'var(--text-placeholder)',
          fontSize: 12,
          border: '1px dashed var(--border-light)',
          borderRadius: 2,
        }}
      >
        No data available
      </div>
    )
  }

  if (config.type === 'table') return <DataTable config={config} />

  if (config.type === 'kpi_card') {
    return <KPICardInline config={config} />
  }

  const commonProps = {
    data: config.data,
    margin: { top: 4, right: 16, left: 0, bottom: 4 },
  }

  const xAxis = (
    <XAxis
      dataKey={config.x_key}
      tick={TICK_STYLE}
      axisLine={{ stroke: GRID_STROKE }}
      tickLine={false}
      interval="preserveStartEnd"
    />
  )
  const yAxis = (
    <YAxis
      tick={TICK_STYLE}
      axisLine={false}
      tickLine={false}
      tickFormatter={v => fmt(v, config.unit)}
      width={54}
    />
  )
  const grid = config.show_grid
    ? <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
    : null
  const tooltip = (
    <Tooltip {...TOOLTIP_STYLE} formatter={(v: any) => [fmt(v, config.unit), '']} />
  )
  const legend = config.show_legend && config.y_keys.length > 1
    ? <Legend {...LEGEND_STYLE} />
    : null

  const chartType = config.type

  return (
    <div>
      {config.title && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 10,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {config.title}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {chartType === 'bar' || chartType === 'grouped_bar' || chartType === 'stacked_bar' ? (
          <BarChart {...commonProps}>
            {grid}{xAxis}{yAxis}{tooltip}{legend}
            {config.y_keys.map((key, i) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[i % colors.length]}
                radius={[3, 3, 0, 0]}
                stackId={chartType === 'stacked_bar' ? 'stack' : undefined}
                maxBarSize={52}
              />
            ))}
          </BarChart>
        ) : chartType === 'line' ? (
          <LineChart {...commonProps}>
            {grid}{xAxis}{yAxis}{tooltip}{legend}
            {config.y_keys.map((key, i) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[i % colors.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            ))}
          </LineChart>
        ) : chartType === 'area' || chartType === 'stacked_area' ? (
          <AreaChart {...commonProps}>
            <defs>
              {config.y_keys.map((key, i) => (
                <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={colors[i % colors.length]} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={colors[i % colors.length]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            {grid}{xAxis}{yAxis}{tooltip}{legend}
            {config.y_keys.map((key, i) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[i % colors.length]}
                strokeWidth={2}
                fill={`url(#grad-${key})`}
                stackId={chartType === 'stacked_area' ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        ) : chartType === 'pie' ? (
          <PieChart>
            <Pie
              data={config.data}
              dataKey={config.y_keys[0]}
              nameKey={config.x_key}
              cx="50%"
              cy="50%"
              outerRadius={height / 2 - 16}
              innerRadius={height / 4}
              paddingAngle={2}
            >
              {config.data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} formatter={(v: any) => [fmt(v, config.unit), '']} />
            {config.show_legend && <Legend {...LEGEND_STYLE} />}
          </PieChart>
        ) : (
          // Fallback bar
          <BarChart {...commonProps}>
            {grid}{xAxis}{yAxis}{tooltip}
            {config.y_keys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={colors[i % colors.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

// ─── Inline KPI Card (used inside panels) ────────────────────────────────────
function KPICardInline({ config }: { config: ChartConfig }) {
  const value = config.kpi_value ?? config.data?.[0]?.[config.y_keys?.[0]] ?? 0
  const label = config.kpi_label || config.title || config.y_keys?.[0] || 'KPI'
  const formatted = fmt(value, config.unit)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        textAlign: 'center',
        height: '100%',
        minHeight: 80,
      }}
    >
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: 'var(--pbi-blue)',
          lineHeight: 1,
          marginBottom: 8,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {formatted}
      </div>
      <div
        style={{
          fontSize: 13,
          color: 'var(--text-secondary)',
          fontWeight: 500,
        }}
      >
        {label.replace(/_/g, ' ')}
      </div>
    </div>
  )
}
