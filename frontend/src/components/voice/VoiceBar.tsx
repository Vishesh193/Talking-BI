import { useRef, useState } from 'react'
import {
  Mic, MicOff, Send, X, MessageSquare, ChevronUp,
} from 'lucide-react'
import { useBIStore } from '@/stores/biStore'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'

interface VoiceBarProps {
  ws: {
    sendTextQuery: (q: string) => void
    sendVoiceAudio: (b64: string) => void
    sendClarification: (r: string) => void
  }
}

const QUICK_QUERIES = [
  'Show revenue by product',
  'Compare this month vs last month',
  'Top 5 salespeople by revenue',
  'Revenue trend over time',
  'Show me key insights',
]

export default function VoiceBar({ ws }: VoiceBarProps) {
  const [text, setText] = useState('')
  const [showQuick, setShowQuick] = useState(false)
  const [clarifyInput, setClarifyInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const {
    agentStage, wsConnected, clarificationQuestion, setClarificationQuestion,
  } = useBIStore()

  const voice = useVoiceRecorder({
    onAudio: (b64) => ws.sendVoiceAudio(b64),
  })

  const handleSend = () => {
    const q = text.trim()
    if (!q || agentStage !== 'idle') return
    ws.sendTextQuery(q)
    setText('')
    setShowQuick(false)
  }

  const handleClarify = () => {
    const r = clarifyInput.trim()
    if (!r) return
    ws.sendClarification(r)
    setClarifyInput('')
    setClarificationQuestion(null)
  }

  const isThinking = agentStage !== 'idle' && agentStage !== 'error' && agentStage !== 'done'

  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderTop: '1px solid var(--border-light)',
        padding: '8px 16px',
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      {/* Clarification prompt */}
      {clarificationQuestion && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 12px',
            background: 'var(--pbi-blue-light)',
            border: '1px solid var(--pbi-blue-mid)',
            borderRadius: 2,
            marginBottom: 8,
          }}
          className="fade-in"
        >
          <MessageSquare size={14} style={{ color: 'var(--pbi-blue)', flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: 'var(--text-primary)', flex: 1 }}>
            {clarificationQuestion}
          </span>
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <input
              className="input-field"
              style={{ width: 200, height: 28, fontSize: 12 }}
              placeholder="Type your answer..."
              value={clarifyInput}
              onChange={e => setClarifyInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleClarify()}
            />
            <button className="btn-primary" style={{ height: 28, padding: '0 12px', fontSize: 12 }} onClick={handleClarify}>
              Reply
            </button>
            <button className="btn-icon" onClick={() => setClarificationQuestion(null)} title="Dismiss">
              <X size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Quick queries */}
      {showQuick && (
        <div
          style={{
            display: 'flex',
            gap: 6,
            marginBottom: 8,
            flexWrap: 'wrap',
          }}
          className="fade-in"
        >
          {QUICK_QUERIES.map(q => (
            <button
              key={q}
              onClick={() => { ws.sendTextQuery(q); setShowQuick(false) }}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                color: 'var(--pbi-blue)',
                background: 'var(--pbi-blue-light)',
                border: '1px solid var(--pbi-blue-mid)',
                borderRadius: 12,
                cursor: 'pointer',
                transition: 'background .12s',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--pbi-blue-mid)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--pbi-blue-light)')}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Main input row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Quick queries toggle */}
        <button
          className="btn-icon"
          onClick={() => setShowQuick(v => !v)}
          title="Quick queries"
          style={{ color: showQuick ? 'var(--pbi-blue)' : undefined }}
        >
          <ChevronUp size={16} style={{ transform: showQuick ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
        </button>

        {/* Text input */}
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            ref={inputRef}
            className="input-field"
            style={{
              height: 38,
              paddingLeft: 14,
              paddingRight: 14,
              fontSize: 13,
              borderRadius: 2,
              background: isThinking ? 'var(--neutral-10)' : 'var(--surface-card)',
            }}
            placeholder={
              isThinking
                ? 'Processing...'
                : !wsConnected
                ? 'Connecting to server...'
                : 'Ask a question about your data...'
            }
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={isThinking || !wsConnected}
          />
        </div>

        {/* Send button */}
        <button
          className="btn-primary"
          style={{ height: 38, width: 38, padding: 0, justifyContent: 'center', borderRadius: 2 }}
          onClick={handleSend}
          disabled={!text.trim() || isThinking || !wsConnected}
          title="Send (Enter)"
        >
          <Send size={15} />
        </button>

        {/* Mic button */}
        <button
          onClick={voice.isRecording ? voice.stopRecording : voice.startRecording}
          disabled={isThinking || !wsConnected}
          style={{
            height: 38,
            width: 38,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 2,
            border: voice.isRecording ? '2px solid var(--pbi-red)' : '1px solid var(--border-default)',
            background: voice.isRecording ? '#FDE7E9' : 'transparent',
            color: voice.isRecording ? 'var(--pbi-red)' : 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all .15s',
            animation: voice.isRecording ? 'pulse 1s infinite' : 'none',
          }}
          title={voice.isRecording ? 'Stop recording' : 'Voice query'}
        >
          {voice.isRecording ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
      </div>
    </div>
  )
}
