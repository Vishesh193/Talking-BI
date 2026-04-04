import { ShieldCheck, ShieldAlert, ShieldX, Info, AlertTriangle } from 'lucide-react'

interface QualityReport {
  score: number
  grade: string
  grade_color: string
  row_count: number
  null_pct: number
  outlier_count: number
  duplicate_count: number
  freshness: string
  signals: Array<{ type: 'warning' | 'info'; message: string }>
}

interface Props {
  quality: QualityReport | null | undefined
}

export default function DataQualityBadge({ quality }: Props) {
  if (!quality) return null

  const Icon =
    quality.score >= 90 ? ShieldCheck :
    quality.score >= 60 ? ShieldAlert :
    ShieldX

  const color = quality.grade_color

  return (
    <div
      title={`Data Quality: ${quality.grade} (${quality.score}/100)\nNulls: ${quality.null_pct}% | Outliers: ${quality.outlier_count} | Freshness: ${quality.freshness}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 7px',
        borderRadius: 10,
        background: `${color}18`,
        border: `1px solid ${color}40`,
        cursor: 'help',
      }}
    >
      <Icon size={10} style={{ color, flexShrink: 0 }} />
      <span style={{ fontSize: 10, fontWeight: 600, color }}>
        {quality.grade}
      </span>
      {quality.signals.some(s => s.type === 'warning') && (
        <AlertTriangle size={9} style={{ color: '#FF8C00', marginLeft: 2 }} />
      )}
    </div>
  )
}
