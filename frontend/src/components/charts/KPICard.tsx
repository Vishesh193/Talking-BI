import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { ChartConfig } from '@/stores/biStore'

interface Props { config: ChartConfig }

function fmt(value: number, unit?: string) {
  if (unit === '$' || unit === 'currency') {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
    return `$${value.toFixed(0)}`
  }
  if (unit === '%' || unit === 'percentage') return `${value.toFixed(1)}%`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toLocaleString()
}

export default function KPICard({ config }: Props) {
  const value = config.kpi_value ?? config.data?.[0]?.[config.y_keys?.[0]] ?? 0
  const label = config.kpi_label || config.title || config.y_keys?.[0] || 'KPI'
  const formatted = typeof value === 'number' ? fmt(value, config.unit) : String(value)

  // Optional: detect change % from data if available
  const prev = config.data?.length > 1 ? config.data[1]?.[config.y_keys?.[0]] : null
  const changePct = (prev && typeof value === 'number' && typeof prev === 'number' && prev !== 0)
    ? ((value - prev) / Math.abs(prev)) * 100
    : null

  const isPositive = changePct !== null && changePct > 0
  const isNegative = changePct !== null && changePct < 0

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        height: '100%',
        justifyContent: 'center',
        background: 'var(--surface-card)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative bar */}
      <div
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0,
          height: 3,
          background: 'linear-gradient(90deg, var(--pbi-blue), var(--pbi-teal))',
        }}
      />

      {/* Label */}
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.6px',
          marginBottom: 10,
        }}
      >
        {label.replace(/_/g, ' ')}
      </div>

      {/* Value */}
      <div
        style={{
          fontSize: 34,
          fontWeight: 700,
          color: 'var(--pbi-blue)',
          lineHeight: 1,
          marginBottom: 8,
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-1px',
        }}
      >
        {formatted}
      </div>

      {/* Change indicator */}
      {changePct !== null && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 12,
            color: isPositive ? 'var(--pbi-green)' : isNegative ? 'var(--pbi-red)' : 'var(--neutral-80)',
            fontWeight: 500,
          }}
        >
          {isPositive ? <TrendingUp size={13} /> : isNegative ? <TrendingDown size={13} /> : <Minus size={13} />}
          {Math.abs(changePct).toFixed(1)}% vs prior period
        </div>
      )}
    </div>
  )
}
