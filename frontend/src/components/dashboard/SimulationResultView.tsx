import { PlayCircle, ArrowRight, TrendingUp, TrendingDown, Info } from 'lucide-react'
import type { SimulationResult } from '@/stores/biStore'

interface Props { simulation: SimulationResult }

export default function SimulationResultView({ simulation }: Props) {
  const isPositive = simulation.impact_level === 'Positive'
  const isNegative = simulation.impact_level === 'Negative'
  const color = isPositive ? 'var(--pbi-green)' : isNegative ? 'var(--pbi-red)' : 'var(--pbi-blue)'
  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Info

  return (
    <div style={{ padding: '16px 20px', background: 'var(--neutral-10)', borderRadius: 2, border: '1px solid var(--border-light)', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <PlayCircle size={14} style={{ color: 'var(--pbi-blue)' }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{simulation.scenario} (Simulation)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 30, marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-placeholder)', marginBottom: 4, textTransform: 'uppercase' }}>Baseline</div>
          <div style={{ fontSize: 24, fontWeight: 300, color: 'var(--text-primary)' }}>
            {simulation.baseline_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        
        <ArrowRight size={20} style={{ color: 'var(--text-placeholder)', opacity: 0.5 }} />

        <div>
          <div style={{ fontSize: 10, color: 'var(--text-placeholder)', marginBottom: 4, textTransform: 'uppercase' }}>Predicted</div>
          <div style={{ fontSize: 24, fontWeight: 700, color }}>
            {simulation.simulated_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>

        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
           <div style={{ fontSize: 10, color: 'var(--text-placeholder)', marginBottom: 4, textTransform: 'uppercase' }}>Net Change</div>
           <div style={{ fontSize: 18, fontWeight: 700, color, display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
             {simulation.net_change_pct > 0 ? '+' : ''}{simulation.net_change_pct.toFixed(1)}%
             <Icon size={18} />
           </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1, padding: '8px 12px', background: 'white', border: '1px solid var(--border-light)', borderRadius: 2 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Reasoning & Assumptions</div>
          <p style={{ fontSize: 11, color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>{simulation.reasoning}</p>
        </div>
        <div style={{ width: 120, padding: '8px 12px', background: 'white', border: '1px solid var(--border-light)', borderRadius: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontSize: 10, color: 'var(--text-placeholder)', marginBottom: 2 }}>Confidence</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--pbi-blue)' }}>{(simulation.confidence * 100).toFixed(0)}%</div>
          <div style={{ width: '100%', height: 3, background: 'var(--neutral-10)', marginTop: 4 }}>
            <div style={{ width: `${simulation.confidence * 100}%`, height: '100%', background: 'var(--pbi-blue)' }} />
          </div>
        </div>
      </div>
    </div>
  )
}
