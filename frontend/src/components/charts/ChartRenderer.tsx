import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
  ScatterChart, Scatter, ZAxis, Treemap
} from 'recharts'
import ReactECharts from 'echarts-for-react'
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

  if (config.type === 'heatmap' || config.type === 'sankey' || config.type === 'geomap') {
    return <EChartComponent config={config} height={height} colors={colors} />
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
    <Tooltip {...TOOLTIP_STYLE} formatter={(v: number | string) => [fmt(v, config.unit), '']} />
  )
  const legend = config.show_legend && config.y_keys.length > 1
    ? <Legend {...LEGEND_STYLE} />
    : null

  const chartType = config.type

  if (chartType === 'waterfall' || chartType === 'gauge' || chartType === 'treemap' || chartType === 'bullet') {
    return <EChartComponent config={config} height={height} colors={colors} />
  }

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
        ) : chartType === 'pie' || chartType === 'donut' ? (
          <PieChart>
            <Pie
              data={config.data}
              dataKey={config.y_keys[0]}
              nameKey={config.x_key}
              cx="50%"
              cy="50%"
              outerRadius={height / 2 - 16}
              innerRadius={chartType === 'donut' ? height / 4 + 10 : height / 4}
              paddingAngle={2}
              label={!compact}
            >
              {config.data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} formatter={(v: number | string) => [fmt(v, config.unit), '']} />
            {config.show_legend && <Legend {...LEGEND_STYLE} verticalAlign="bottom" />}
          </PieChart>
        ) : chartType === 'scatter' ? (
          <ScatterChart {...commonProps}>
            {grid}{xAxis}{yAxis}{tooltip}{legend}
            {config.y_keys.map((key, i) => (
              <Scatter
                key={key}
                name={key}
                dataKey={key}
                fill={colors[i % colors.length]}
                shape="circle"
              />
            ))}
          </ScatterChart>
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
  const data = config.data?.[0] || {}
  const primaryKey = config.kpi_value_key || config.y_keys?.[0] || 'value'
  const displayValue = data[primaryKey] ?? 0
  const secondaryValue = config.kpi_secondary_key ? data[config.kpi_secondary_key] : null
  
  const label = config.kpi_label || config.title || primaryKey || 'KPI'
  const formattedPrimary = fmt(displayValue, config.unit)
  const formattedSecondary = secondaryValue !== null ? fmt(secondaryValue, config.unit) : null

  const delta = config.kpi_delta
  const direction = config.kpi_direction
  const isUp = direction === 'up'
  const isDown = direction === 'down'

  const primaryColor = config.colors?.[0] || '#3C3489'

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '20px 20px',
        height: '100%',
        minHeight: 100,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#A19F9D',
          letterSpacing: 0.8,
          textTransform: 'uppercase',
          marginBottom: 6,
        }}
      >
        {label.replace(/_/g, ' ')}
      </div>

      <div
        style={{
          fontSize: 34,
          fontWeight: 700,
          color: primaryColor,
          lineHeight: 1.1,
          marginBottom: 8,
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.5px',
        }}
      >
        {formattedPrimary}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {formattedSecondary && (
          <div style={{ fontSize: 13, fontWeight: 500, color: '#605E5C' }}>
            {formattedSecondary}
          </div>
        )}

        {delta !== undefined && Math.abs(delta) > 0 && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 12,
              fontWeight: 600,
              color: isUp ? '#0F6E56' : isDown ? '#993C1D' : '#A19F9D',
            }}
          >
            <span style={{ fontSize: 10 }}>{isUp ? '▲' : isDown ? '▼' : '▬'}</span>
            {Math.abs(delta)}%
            <span style={{ fontSize: 11, fontWeight: 400, color: '#A19F9D' }}>vs last mo.</span>
          </div>
        )}
      </div>
    </div>
  )
}
// ─── ECharts Component for Advanced Visualizations ────────────────────────────
function EChartComponent({ config, height, colors }: { config: ChartConfig, height: number, colors: string[] }) {
  const { data, x_key, y_keys } = config

  // --- Heatmap Option ---
  if (config.type === 'heatmap') {
    const yAxisData = [...new Set(data.map(d => d[x_key]))]
    const xAxisData = Object.keys(data[0]).filter(k => k !== x_key && typeof data[0][k] === 'string')
    const metricKey = y_keys[0]

    const heatmapData = data.map(d => {
      const xIdx = xAxisData.indexOf(Object.keys(d).find(k => k !== x_key && typeof d[k] === 'string') || '')
      const yIdx = yAxisData.indexOf(d[x_key])
      return [xIdx, yIdx, d[metricKey] || 0]
    })

    const option = {
      tooltip: { position: 'top' },
      grid: { height: '80%', top: '10%' },
      xAxis: { type: 'category', data: xAxisData, splitArea: { show: true } },
      yAxis: { type: 'category', data: yAxisData, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: Math.max(...heatmapData.map(d => d[2] as number)),
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: { color: ['#fff7ec', '#fee8c8', '#fdbb84', '#fc8d59', '#ef6548', '#d7301f', '#990000'] }
      },
      series: [{ name: metricKey, type: 'heatmap', data: heatmapData, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } } }]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  // --- Sankey Option ---
  if (config.type === 'sankey') {
    const nodes: any[] = []
    const links: any[] = []
    const nodeSet = new Set()

    data.slice(0, 50).forEach(d => {
      const source = d[x_key]
      const target = Object.keys(d).find(k => k !== x_key && typeof d[k] === 'string') || 'Target'
      const value = d[y_keys[0]] || 1

      if (!nodeSet.has(source)) { nodeSet.add(source); nodes.push({ name: source }) }
      if (!nodeSet.has(target)) { nodeSet.add(target); nodes.push({ name: target }) }
      links.push({ source, target, value })
    })

    const option = {
      tooltip: { trigger: 'item', triggerOn: 'mousemove' },
      series: [{
        type: 'sankey',
        data: nodes,
        links: links,
        emphasis: { focus: 'adjacency' },
        lineStyle: { color: 'gradient', curveness: 0.5 }
      }]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  // --- Treemap ---
  if (config.type === 'treemap') {
    const treemapData = data.map(d => ({
      name: d[x_key],
      value: d[y_keys[0]]
    }))
    const option = {
      tooltip: { trigger: 'item' },
      series: [{
        type: 'treemap',
        data: treemapData,
        label: { show: true, formatter: '{b}' },
        itemStyle: { borderColor: '#fff' },
        breadcrumb: { show: false }
      }]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  // --- Waterfall ---
  if (config.type === 'waterfall') {
    const xAxisData = data.map(d => d[x_key])
    const values = data.map(d => d[y_keys[0]])
    const help = []
    const positive = []
    let sum = 0
    for (let i = 0; i < values.length; i++) {
      help.push(sum)
      sum += values[i]
      positive.push(values[i])
    }
    const option = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: xAxisData },
      yAxis: { type: 'value' },
      series: [
        { name: 'Placeholder', type: 'bar', stack: 'Total', itemStyle: { borderColor: 'transparent', color: 'transparent' }, emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } }, data: help },
        { name: 'Value', type: 'bar', stack: 'Total', label: { show: true, position: 'inside' }, data: positive, itemStyle: { color: colors[0] } }
      ]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  // --- Gauge ---
  if (config.type === 'gauge') {
    const val = config.kpi_value ?? data[0]?.[config.kpi_value_key || y_keys[0]] ?? 0
    const option = {
      tooltip: { formatter: '{a} <br/>{b} : {c}%' },
      series: [{
        name: 'Pressure',
        type: 'gauge',
        detail: { formatter: '{value}' },
        data: [{ value: val, name: y_keys[0] }],
        axisLine: { lineStyle: { width: 10, color: [[0.3, colors[1]], [0.7, colors[0]], [1, colors[2]]] } },
      }]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  // --- Bullet (as a nice bar for now) ---
  if (config.type === 'bullet') {
    const val = data[0]?.[y_keys[0]] ?? 0
    const option = {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value', max: val * 1.2 },
      yAxis: { type: 'category', data: [data[0]?.[x_key] || 'Result'] },
      series: [{ type: 'bar', data: [val], barWidth: 30, itemStyle: { color: colors[0] } }]
    }
    return <ReactECharts option={option} style={{ height }} />
  }

  return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-placeholder)' }}>Visualization type {config.type} not ready</div>
}
