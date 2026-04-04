import { useState } from 'react'
import { X, BarChart2, TrendingUp, PieChart, Table2, CreditCard, ChevronRight, CheckCircle2, Check } from 'lucide-react'
import { useBIStore, DashboardSuggestion, ClarifyingQuestion } from '@/stores/biStore'
import { apiService } from '@/services/api'
import toast from 'react-hot-toast'

interface Props {
  ws: { sendTextQuery: (q: string) => void }
}

type Step = 'suggestions' | 'questions' | 'generating'

const CHART_ICON_MAP: Record<string, React.ComponentType<any>> = {
  bar:          BarChart2,
  line:         TrendingUp,
  area:         TrendingUp,
  grouped_bar:  BarChart2,
  stacked_area: TrendingUp,
  pie:          PieChart,
  kpi_card:     CreditCard,
  table:        Table2,
}

export default function DashboardSuggestionsModal({ ws }: Props) {
  const { fileAnalysis, setFileAnalysis, addPage, setActivePageId, setPageAdvancedMeta } = useBIStore()
  const [step, setStep] = useState<Step>('suggestions')
  const [selectedSuggestion, setSelectedSuggestion] = useState<DashboardSuggestion | null>(null)
  const [answers, setAnswers] = useState<Record<string, string[]>>({})
  const [generating, setGenerating] = useState(false)

  if (!fileAnalysis) return null

  const { suggestions, clarifying_questions, filename, rows, columns } = fileAnalysis
  const pendingQuestions = clarifying_questions.filter(q => (answers[q.id]?.length || 0) === 0)
  const answeredCount = clarifying_questions.filter(q => answers[q.id]?.length > 0 && !answers[q.id]?.includes('__skip__')).length

  const handleSelectSuggestion = (s: DashboardSuggestion) => {
    setSelectedSuggestion(s)
    if (clarifying_questions.length > 0) {
      setStep('questions')
    } else {
      handleGenerate(s, {})
    }
  }

  const handleAnswer = (qId: string, answer: string) => {
    setAnswers(prev => {
      const current = prev[qId] || []
      if (answer === '__skip__') return { ...prev, [qId]: ['__skip__'] }
      
      const filtered = current.filter(a => a !== '__skip__')
      if (filtered.includes(answer)) {
        return { ...prev, [qId]: filtered.filter(a => a !== answer) }
      } else {
        return { ...prev, [qId]: [...filtered, answer] }
      }
    })
  }

  const handleSelectAll = (qId: string, options: string[]) => {
    setAnswers(prev => ({ ...prev, [qId]: options }))
  }

  const handleSkipQuestion = (qId: string) => {
    setAnswers(prev => ({ ...prev, [qId]: ['__skip__'] }))
  }

  const allAnswered = clarifying_questions.every(q => (answers[q.id]?.length || 0) > 0)

  const handleGenerate = async (suggestion: DashboardSuggestion | null = selectedSuggestion, ans: Record<string, string[]> = answers) => {
    if (!suggestion) return
    setGenerating(true)
    setStep('generating')

    let queries: { query: string, x?: number, y?: number, w?: number, h?: number, type?: string, kpi_label?: string, kpi_delta?: number, kpi_direction?: string }[] = []
    let paletteColors: string[] = []
    
    let isAdvancedFallback = false;
    
    // Add new page for this dashboard
    const pageId = addPage(`${suggestion.title}`)
    setActivePageId(pageId)

    if (suggestion.id === 'S0_ADVANCED') {
      try {
        const { sessionId } = useBIStore.getState()
        // Format answers for backend if it expects strings, but backend route will also be updated to handle lists
        const res = await apiService.generateAdvancedDashboard({ session_id: sessionId, answers: ans })
        
        // Extract professional palette colors
        if (res.colors) {
          paletteColors = [res.colors.primary, res.colors.secondary, res.colors.positive, res.colors.negative].filter(Boolean)
        }

        // Store advanced meta on the page so DashboardCanvas can render header + filter pills
        setPageAdvancedMeta(pageId, {
          dashboard_title: res.dashboard_title,
          filter_pills: res.filter_pills || [],
          colors: res.colors,
        })
        
        queries = res.panels || []
      } catch (err) {
        toast.error('Advanced generation failed — falling back to legacy')
        isAdvancedFallback = true;
        queries = buildQueriesForSuggestion(suggestion, fileAnalysis, '').map(q => ({ query: q }))
      }
    } else {
      // Build context from answers
      const answerContext = Object.entries(ans)
        .filter(([, v]) => v && v.length > 0 && !v.includes('__skip__'))
        .map(([qId, v]) => {
          const q = clarifying_questions.find(q => q.id === qId)
          return q ? `${q.question}: ${v.join(', ')}` : ''
        })
        .filter(Boolean)
        .join('. ')
      queries = buildQueriesForSuggestion(suggestion, fileAnalysis, answerContext).map(q => ({ query: q }))
    }

    // If this was a legacy flow or a fallback, trigger queries from the frontend sequentially
    if (suggestion.id !== 'S0_ADVANCED' || isAdvancedFallback) {
      const fireSequential = async () => {
        for (const q of queries) {
          ws.sendTextQuery(q.query)
          await new Promise(r => setTimeout(r, 4000)) // 4s throttle to respect LLM rate limits
        }
      }
      fireSequential()
    }

    toast.success(`"${suggestion.title}" dashboard created!`)
    setGenerating(false)
    setFileAnalysis(null)
  }

  return (
    <div className="modal-backdrop">
      <div
        className="modal-box"
        style={{ width: 780, maxWidth: '95vw' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-light)',
          }}
        >
          <div
            style={{
              width: 32, height: 32,
              background: 'linear-gradient(135deg, #0078D4, #00B7C3)',
              borderRadius: 4,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <BarChart2 size={18} color="#fff" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)' }}>
              {step === 'suggestions' && 'Choose Your Dashboard'}
              {step === 'questions' && 'Customize Your Dashboard'}
              {step === 'generating' && 'Building Your Dashboard...'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              {filename} · {rows.toLocaleString()} rows · {columns.length} columns
            </div>
          </div>

          {/* Step indicator */}
          {step !== 'generating' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <StepDot active={step === 'suggestions'} done={step !== 'suggestions'} label="1" />
              {clarifying_questions.length > 0 && (
                <>
                  <div style={{ width: 20, height: 1, background: 'var(--border-default)' }} />
                  <StepDot active={step === 'questions'} done={false} label="2" />
                </>
              )}
            </div>
          )}

          <button
            className="btn-icon"
            onClick={() => setFileAnalysis(null)}
            style={{ flexShrink: 0 }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px', minHeight: 300 }}>

          {/* ── Step 1: Suggestions ── */}
          {step === 'suggestions' && (
            <div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Based on your data, here are the best dashboard layouts. Pick one to get started:
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                {suggestions.map(s => (
                  <SuggestionCard
                    key={s.id}
                    suggestion={s}
                    onSelect={() => handleSelectSuggestion(s)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ── Step 2: Clarifying questions ── */}
          {step === 'questions' && (
            <div>
              <div
                style={{
                  padding: '10px 14px',
                  background: 'var(--pbi-blue-light)',
                  border: '1px solid var(--pbi-blue-mid)',
                  borderRadius: 2,
                  marginBottom: 20,
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                }}
              >
                <CheckCircle2 size={15} style={{ color: 'var(--pbi-blue)', flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                  You selected: <strong>{selectedSuggestion?.title}</strong>
                </span>
              </div>

              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Personalize your dashboard. Select one or more options for each question:
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {clarifying_questions.map((q, idx) => {
                  const qAnswers = answers[q.id] || []
                  const answered = qAnswers.length > 0 && !qAnswers.includes('__skip__')
                  const skipped  = qAnswers.includes('__skip__')
                  return (
                    <QuestionBlock
                      key={q.id}
                      question={q}
                      idx={idx + 1}
                      answer={qAnswers}
                      answered={!!answered}
                      skipped={!!skipped}
                      onAnswer={handleAnswer}
                      onSelectAll={() => handleSelectAll(q.id, q.options)}
                      onSkip={handleSkipQuestion}
                    />
                  )
                })}
              </div>
            </div>
          )}

          {/* ── Step 3: Generating ── */}
          {step === 'generating' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, padding: '32px 0' }}>
              <div
                style={{
                  width: 64, height: 64,
                  background: 'linear-gradient(135deg, #0078D4, #00B7C3)',
                  borderRadius: 12,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  animation: 'pulse 1.5s infinite',
                }}
              >
                <BarChart2 size={30} color="#fff" />
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
                  Building "{selectedSuggestion?.title}"
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  Analyzing data and generating charts...
                </p>
              </div>
              {/* Animated loading bars */}
              <div style={{ display: 'flex', gap: 4 }}>
                {[0,1,2,3,4].map(i => (
                  <div
                    key={i}
                    style={{
                      width: 8, borderRadius: 4,
                      background: 'var(--pbi-blue)',
                      animation: `pulse 1s ${i * 0.15}s infinite`,
                      opacity: 0.7 + i * 0.06,
                      height: 8 + i * 6,
                      alignSelf: 'flex-end',
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'questions' && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 20px',
              borderTop: '1px solid var(--border-light)',
              background: 'var(--neutral-10)',
            }}
          >
            <button
              className="btn-ghost"
              onClick={() => setStep('suggestions')}
              style={{ gap: 6 }}
            >
              ← Back
            </button>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text-placeholder)' }}>
                {answeredCount}/{clarifying_questions.length} answered
              </span>
              <button
                className="btn-secondary"
                onClick={() => handleGenerate()}
                style={{ gap: 6 }}
              >
                Skip all & generate <ChevronRight size={13} />
              </button>
              <button
                className="btn-primary"
                onClick={() => handleGenerate()}
                style={{ gap: 6 }}
              >
                Generate Dashboard <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StepDot({ active, done, label }: { active: boolean; done: boolean; label: string }) {
  return (
    <div
      style={{
        width: 24, height: 24,
        borderRadius: 12,
        background: done ? 'var(--pbi-green)' : active ? 'var(--pbi-blue)' : 'var(--neutral-40)',
        color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700,
      }}
    >
      {done ? <Check size={12} /> : label}
    </div>
  )
}

function SuggestionCard({
  suggestion, onSelect,
}: {
  suggestion: DashboardSuggestion
  onSelect: () => void
}) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        border: `1.5px solid ${hovered ? 'var(--pbi-blue)' : 'var(--border-light)'}`,
        borderRadius: 4,
        padding: '16px',
        cursor: 'pointer',
        background: hovered ? 'var(--pbi-blue-light)' : 'var(--surface-card)',
        transition: 'all .15s',
        boxShadow: hovered ? '0 2px 8px rgba(0,120,212,.15)' : 'var(--shadow-card)',
      }}
    >
      {/* Chart type icons */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {suggestion.chart_types.slice(0, 3).map((type, i) => {
          const Icon = CHART_ICON_MAP[type] || BarChart2
          return (
            <div
              key={i}
              style={{
                width: 28, height: 28,
                background: hovered ? 'var(--pbi-blue)' : 'var(--pbi-blue-light)',
                borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <Icon size={14} color={hovered ? '#fff' : 'var(--pbi-blue)'} />
            </div>
          )
        })}
      </div>

      <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', marginBottom: 6 }}>
        {suggestion.title}
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
        {suggestion.description}
      </p>

      {suggestion.preview_kpis.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 10 }}>
          {suggestion.preview_kpis.map(kpi => (
            <span key={kpi} className="badge badge-blue" style={{ fontSize: 10 }}>
              {kpi.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function QuestionBlock({
  question, idx, answer, answered, skipped, onAnswer, onSelectAll, onSkip,
}: {
  question: ClarifyingQuestion
  idx: number
  answer: string[]
  answered: boolean
  skipped: boolean
  onAnswer: (id: string, v: string) => void
  onSelectAll: () => void
  onSkip: (id: string) => void
}) {
  const [customText, setCustomText] = useState('')

  return (
    <div
      style={{
        padding: '14px 16px',
        border: `1px solid ${answered ? 'var(--pbi-green)' : skipped ? 'var(--border-light)' : 'var(--border-default)'}`,
        borderRadius: 2,
        background: answered ? '#E3FBE3' : skipped ? 'var(--neutral-10)' : 'var(--surface-card)',
        transition: 'all .15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div
          style={{
            width: 22, height: 22,
            background: answered ? 'var(--pbi-green)' : 'var(--pbi-blue)',
            borderRadius: 11,
            color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 700, flexShrink: 0,
          }}
        >
          {answered ? <Check size={11} /> : idx}
        </div>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
          {question.question}
        </span>
        {skipped && <span className="badge badge-gray" style={{ marginLeft: 'auto', fontSize: 10 }}>Skipped</span>}
      </div>

      {!skipped && (
        <>
          {/* Option chips */}
          {question.options.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {/* Select All button */}
              <button
                onClick={onSelectAll}
                style={{
                  padding: '5px 12px',
                  fontSize: 12,
                  borderRadius: 14,
                  border: '1.5px solid var(--pbi-blue)',
                  background: 'var(--surface-card)',
                  color: 'var(--pbi-blue)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                Select All
              </button>
              
              {question.options.map(opt => {
                const isSelected = answer.includes(opt)
                return (
                  <button
                    key={opt}
                    onClick={() => onAnswer(question.id, opt)}
                    style={{
                      padding: '5px 12px',
                      fontSize: 12,
                      borderRadius: 14,
                      border: `1.5px solid ${isSelected ? 'var(--pbi-blue)' : 'var(--border-default)'}`,
                      background: isSelected ? 'var(--pbi-blue)' : 'var(--surface-card)',
                      color: isSelected ? '#fff' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all .12s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                    }}
                  >
                    {isSelected && <Check size={10} />}
                    {opt}
                  </button>
                )
              })}
            </div>
          )}

          {/* Custom text input */}
          {question.allow_custom && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                className="input-field"
                style={{ flex: 1, height: 32, fontSize: 12 }}
                placeholder="Or type your own answer..."
                value={customText}
                onChange={e => setCustomText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && customText.trim() && onAnswer(question.id, customText.trim())}
              />
              {customText && (
                <button
                  className="btn-primary"
                  style={{ height: 32, padding: '0 12px', fontSize: 12 }}
                  onClick={() => { onAnswer(question.id, customText.trim()); setCustomText('') }}
                >
                  OK
                </button>
              )}
            </div>
          )}
        </>
      )}

      {/* Skip */}
      {!answered && !skipped && question.skippable && (
        <button
          onClick={() => onSkip(question.id)}
          style={{ marginTop: 8, fontSize: 11, color: 'var(--text-placeholder)', cursor: 'pointer' }}
        >
          Skip this question →
        </button>
      )}
      {skipped && (
        <button
          onClick={() => onAnswer(question.id, '')}
          style={{ marginTop: 4, fontSize: 11, color: 'var(--pbi-blue)', cursor: 'pointer' }}
        >
          Answer this question
        </button>
      )}
    </div>
  )
}

// ─── Query builder ────────────────────────────────────────────────────────────

function buildQueriesForSuggestion(
  suggestion: DashboardSuggestion,
  fileAnalysis: { columns: string[]; column_types: Record<string, string>; filename: string },
  answerContext: string,
): string[] {
  const { columns, column_types } = fileAnalysis
  const numericCols = columns.filter(c => column_types[c] === 'numeric').slice(0, 4)
  const catCols     = columns.filter(c => column_types[c] === 'categorical').slice(0, 3)
  const dateCols    = columns.filter(c => column_types[c] === 'date').slice(0, 2)
  const context     = answerContext ? ` Context: ${answerContext}.` : ''
  const metric      = numericCols[0] || 'value'
  const dimension   = catCols[0] || 'category'

  switch (suggestion.focus.toLowerCase()) {
    case 'kpi summary':
    case 'summary':
      return [
        `Show total ${metric} as KPI card${context}`,
        numericCols[1] ? `Show total ${numericCols[1]} as KPI card` : 'Show count of records as KPI card',
        `Show ${metric} by ${dimension} as a bar chart${context}`,
        dateCols[0] ? `Show ${metric} trend over ${dateCols[0]} as a line chart` : `Show ${metric} trend over time as a line chart`,
        catCols[1] ? `Show breakdown by ${catCols[1]} as a pie chart` : `Show top items by ${metric} as a pie chart`,
      ]
    case 'trend analysis':
    case 'trends':
      return [
        dateCols[0] ? `Show ${metric} trend over ${dateCols[0]} as a line chart${context}` : `Show ${metric} trend over time as a line chart${context}`,
        `Show total ${metric} as KPI card`,
        catCols[0] ? `Show month over month ${metric} by ${catCols[0]} as a grouped bar chart` : `Show monthly ${metric} comparison as a grouped bar chart`,
        numericCols[1] ? `Show ${metric} vs ${numericCols[1]} as an area chart` : `Show ${metric} as area chart`,
      ]
    case 'comparison':
      return [
        `Compare ${metric} across ${dimension} as a bar chart${context}`,
        catCols[1] ? `Compare ${metric} by ${catCols[1]} as a grouped bar chart` : `Show top 10 by ${metric} as a bar chart`,
        `Show distribution of ${dimension} as a pie chart`,
        numericCols[1] ? `Compare ${numericCols[0]} vs ${numericCols[1]} by ${dimension}` : `Show ${metric} ranked by ${dimension}`,
      ]
    case 'distribution':
      return [
        `Show ${metric} distribution by ${dimension} as a pie chart${context}`,
        catCols[1] ? `Show breakdown by ${catCols[1]} as a bar chart` : `Show ${dimension} breakdown as a bar chart`,
        `Show top 10 records with highest ${metric} as a table`,
        numericCols[1] ? `Show ${numericCols[1]} distribution as a pie chart` : `Show ${metric} summary`,
      ]
    default:
      return [
        `Show ${metric} by ${dimension} as a bar chart${context}`,
        `Show total ${metric} as KPI card`,
        dateCols[0] ? `Show ${metric} over ${dateCols[0]} as a line chart` : `Show ${metric} trend over time`,
        `Show top 5 ${dimension} by ${metric}`,
        `Give me key insights from the data`,
      ]
  }
}
