import { TrendingUp, TrendingDown, Minus, Zap } from 'lucide-react'
import type { InsightCard } from '@/stores/biStore'

interface Props { insights: InsightCard[] }

export default function InsightsList({ insights }: Props) {
  if (!insights?.length) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {insights.map((ins, i) => {
        const dir = ins.direction || 'neutral'
        const Icon = dir === 'up' ? TrendingUp : dir === 'down' ? TrendingDown : Minus
        const color = ins.is_anomaly
          ? 'var(--pbi-orange)'
          : dir === 'up' ? 'var(--pbi-green)' : dir === 'down' ? 'var(--pbi-red)' : 'var(--neutral-80)'

        return (
          <div
            key={i}
            style={{
              padding: '10px 12px',
              borderLeft: `3px solid ${color}`,
              background: 'var(--neutral-10)',
              borderRadius: '0 2px 2px 0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              {ins.is_anomaly
                ? <Zap size={12} style={{ color, flexShrink: 0 }} />
                : <Icon size={12} style={{ color, flexShrink: 0 }} />
              }
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>
                {ins.title}
              </span>
              {ins.change_pct !== undefined && (
                <span style={{ fontSize: 11, color, fontWeight: 600, flexShrink: 0 }}>
                  {ins.change_pct > 0 ? '+' : ''}{ins.change_pct.toFixed(1)}%
                </span>
              )}
              {ins.is_anomaly && (
                <span className="badge badge-orange" style={{ fontSize: 9, flexShrink: 0 }}>anomaly</span>
              )}
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              {ins.body}
            </p>
            {ins.action && (
              <div style={{ marginTop: 6, fontSize: 10, color: 'var(--pbi-blue)', fontWeight: 500 }}>
                → {ins.action}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
