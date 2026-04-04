import { Lightbulb, ArrowRight, ShieldCheck, Target, TrendingUp } from 'lucide-react'
import type { StrategyRecommendation } from '@/stores/biStore'

interface Props { strategies: StrategyRecommendation[] }

export default function StrategicActions({ strategies }: Props) {
  if (!strategies?.length) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: 0.8 }}>
        <Lightbulb size={14} style={{ color: 'var(--pbi-orange)' }} />
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.03em', color: 'var(--text-secondary)' }}>
          Strategic Recommendations
        </span>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
        {strategies.map((strat, i) => {
          const impactColor = strat.impact === 'High' ? 'var(--pbi-red)' : strat.impact === 'Medium' ? 'var(--pbi-orange)' : 'var(--pbi-green)'
          
          return (
            <div 
              key={i}
              className="fade-in"
              style={{
                background: 'linear-gradient(135deg, var(--neutral-10) 0%, white 100%)',
                border: '1px solid var(--border-light)',
                borderRadius: 4,
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                position: 'relative',
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
              }}
            >
              {/* Category chip */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-blue" style={{ fontSize: 9, padding: '2px 6px' }}>{strat.category}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: impactColor, fontWeight: 700, textTransform: 'uppercase' }}>{strat.impact} Impact</span>
                </div>
              </div>

              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                {strat.title}
              </div>
              
              <p style={{ fontSize: 11.5, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                {strat.recommendation}
              </p>

              <div style={{ 
                marginTop: 'auto',
                paddingTop: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontSize: 10,
                color: 'var(--pbi-blue)',
                fontWeight: 600,
                cursor: 'pointer'
              }}>
                Implementation Plan <ArrowRight size={10} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
