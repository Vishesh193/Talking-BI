import { useEffect, useRef, useCallback } from 'react'
import { useBIStore } from '@/stores/biStore'
import toast from 'react-hot-toast'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  const {
    sessionId, setWsConnected, setAgentStage, setAgentMessage,
    addPanel, addToHistory, setClarificationQuestion, setLastTtsText,
  } = useBIStore()

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return
    ws.current = new WebSocket(`${WS_URL}/ws/${sessionId}`)

    ws.current.onopen = () => {
      setWsConnected(true)
      setAgentStage('idle')
    }

    ws.current.onclose = () => {
      setWsConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.current.onerror = () => {
      setWsConnected(false)
    }

    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch (e) {
        console.error('WS message parse failed:', e)
      }
    }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleMessage = useCallback((msg: any) => {
    // Read live state to avoid stale closures
    const { ttsEnabled } = useBIStore.getState()

    switch (msg.type) {
      case 'connected':
        setAgentStage('idle')
        break

      case 'agent_thinking':
        setAgentStage(msg.stage || 'thinking')
        setAgentMessage(msg.message || 'Processing...')
        break

      case 'transcription':
        setAgentStage('thinking')
        setAgentMessage(`Heard: "${msg.transcript}"`)
        useBIStore.getState().setCurrentTranscript(msg.transcript)
        break

      case 'transcription_failed':
        setAgentStage('error')
        setAgentMessage(msg.message || 'Could not transcribe audio')
        toast.error(msg.message || 'Transcription failed')
        setTimeout(() => setAgentStage('idle'), 3000)
        break

      case 'agent_result': {
        const result = msg.data
        setAgentStage('done')
        setAgentMessage(`Done in ${result.execution_time_ms?.toFixed(0)}ms`)
        if (result.error) {
          setAgentStage('error')
          toast.error(result.error)
          addToHistory(result.transcript, false)
          setTimeout(() => setAgentStage('idle'), 3000)
          return
        }
        // Add to active page
        addPanel(result)
        addToHistory(result.transcript, true)
        setClarificationQuestion(null)
        if (result.tts_text && ttsEnabled) {
          setLastTtsText(result.tts_text)
          speakText(result.tts_text)
        }
        setTimeout(() => setAgentStage('idle'), 2000)
        break
      }

      case 'clarification_needed':
        setAgentStage('idle')
        setClarificationQuestion(msg.question)
        setAgentMessage(msg.question || 'Need clarification')
        if (msg.tts_text && ttsEnabled) speakText(msg.tts_text)
        break

      case 'error':
        setAgentStage('error')
        setAgentMessage(msg.message || 'An error occurred')
        toast.error(msg.message || 'An error occurred')
        setTimeout(() => setAgentStage('idle'), 3000)
        break

      case 'pong':
        break

      default:
        break
    }
  }, [addPanel, addToHistory, setClarificationQuestion, setAgentStage, setAgentMessage, setLastTtsText])

  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    } else {
      toast.error('Not connected — retrying...')
    }
  }, [])

  const sendTextQuery = useCallback((query: string) => {
    if (!query.trim()) return
    const { selectedPanelId } = useBIStore.getState()
    setAgentStage('thinking')
    setAgentMessage('Analyzing your query...')
    send({ type: 'text_query', query, selected_panel_id: selectedPanelId })
  }, [send, setAgentStage, setAgentMessage])

  const sendVoiceAudio = useCallback((audioBase64: string) => {
    const { selectedPanelId } = useBIStore.getState()
    setAgentStage('transcribing')
    setAgentMessage('Transcribing audio...')
    send({ type: 'voice_audio', audio: audioBase64, selected_panel_id: selectedPanelId })
  }, [send, setAgentStage, setAgentMessage])

  const sendClarification = useCallback((response: string) => {
    if (!response.trim()) return
    const { selectedPanelId } = useBIStore.getState()
    setClarificationQuestion(null)
    setAgentStage('thinking')
    setAgentMessage('Processing your answer...')
    send({ type: 'clarification', response, selected_panel_id: selectedPanelId })
  }, [send, setClarificationQuestion, setAgentStage, setAgentMessage])

  useEffect(() => {
    connect()
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 25000)
    return () => {
      clearInterval(pingInterval)
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  return { send, sendTextQuery, sendVoiceAudio, sendClarification }
}

// ─── Browser TTS ────────────────────────────────────────────────────────────
function speakText(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 0.95
  utterance.pitch = 1.0
  utterance.volume = 0.9

  const applyVoiceAndSpeak = () => {
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      v.name.includes('Samantha') ||
      v.name.includes('Google UK English Female') ||
      v.name.includes('Karen') ||
      v.name.includes('Moira')
    )
    if (preferred) utterance.voice = preferred
    window.speechSynthesis.speak(utterance)
  }

  if (window.speechSynthesis.getVoices().length > 0) {
    applyVoiceAndSpeak()
  } else {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.onvoiceschanged = null
      applyVoiceAndSpeak()
    }
  }
}
