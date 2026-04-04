import { useState } from 'react'
import { Lightbulb, ChevronRight, Zap } from 'lucide-react'

interface Props {
  suggestions: string[]
  onSuggestionClick: (query: string) => void
}

export default function SuggestionChips({ suggestions, onSuggestionClick }: Props) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set())

  if (!suggestions || suggestions.length === 0) return null

  const visible = suggestions.filter((_, i) => !dismissed.has(i))
  if (visible.length === 0) return null

  return (
    <div
      style={{
        padding: '10px 14px',
        borderTop: '1px solid var(--border-light)',
        background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 8,
        }}
      >
        <Lightbulb size={11} style={{ color: '#8764B8' }} />
        <span style={{ fontSize: 10, color: '#8764B8', fontWeight: 600, letterSpacing: '0.04em' }}>
          SUGGESTED FOLLOW-UPS
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {suggestions.map((s, i) => {
          if (dismissed.has(i)) return null
          const isSimulation = s.toLowerCase().startsWith('what if')
          return (
            <button
              key={i}
              onClick={() => {
                onSuggestionClick(s)
                setDismissed(prev => new Set([...prev, i]))
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 10px',
                borderRadius: 20,
                border: `1px solid ${isSimulation ? '#8764B8' : 'var(--pbi-blue)'}`,
                background: isSimulation ? 'rgba(135,100,184,0.08)' : 'rgba(0,120,212,0.06)',
                color: isSimulation ? '#8764B8' : 'var(--pbi-blue)',
                fontSize: 11,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
                fontFamily: 'inherit',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.background = isSimulation ? 'rgba(135,100,184,0.18)' : 'rgba(0,120,212,0.14)'
                ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)'
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.background = isSimulation ? 'rgba(135,100,184,0.08)' : 'rgba(0,120,212,0.06)'
                ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'
              }}
            >
              {isSimulation
                ? <Zap size={10} style={{ flexShrink: 0 }} />
                : <ChevronRight size={10} style={{ flexShrink: 0 }} />}
              {s}
            </button>
          )
        })}
      </div>
    </div>
  )
}
