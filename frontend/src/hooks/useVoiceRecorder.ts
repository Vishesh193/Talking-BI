import { useState, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'

export type RecordingState = 'idle' | 'requesting' | 'recording' | 'processing'

export function useVoiceRecorder({ onAudio }: { onAudio: (base64: string) => void }) {
  const onAudioReady = onAudio
  const [state, setState] = useState<RecordingState>('idle')
  const [decibels, setDecibels] = useState(0)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const audioChunks = useRef<Blob[]>([])
  const analyser = useRef<AnalyserNode | null>(null)
  const animFrame = useRef<number>()
  const silenceTimer = useRef<ReturnType<typeof setTimeout>>()

  const startRecording = useCallback(async () => {
    if (state === 'recording') {
      stopRecording()
      return
    }

    setState('requesting')
    audioChunks.current = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 }
      })

      // Set up analyser for waveform visualization
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      analyser.current = audioCtx.createAnalyser()
      analyser.current.fftSize = 256
      source.connect(analyser.current)

      const trackVolume = () => {
        if (!analyser.current) return
        const data = new Uint8Array(analyser.current.frequencyBinCount)
        analyser.current.getByteFrequencyData(data)
        const avg = data.reduce((a, b) => a + b) / data.length
        setDecibels(avg)
        animFrame.current = requestAnimationFrame(trackVolume)
      }
      trackVolume()

      // Choose best supported MIME type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/ogg'

      mediaRecorder.current = new MediaRecorder(stream, { mimeType })

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data)
      }

      mediaRecorder.current.onstop = async () => {
        cancelAnimationFrame(animFrame.current!)
        setDecibels(0)
        stream.getTracks().forEach(t => t.stop())

        if (audioChunks.current.length === 0) {
          setState('idle')
          return
        }

        setState('processing')
        const blob = new Blob(audioChunks.current, { type: mimeType })
        const base64 = await blobToBase64(blob)
        onAudioReady(base64)
        setState('idle')
      }

      mediaRecorder.current.start(100) // collect chunks every 100ms
      setState('recording')

      // Auto-stop after 30 seconds
      silenceTimer.current = setTimeout(() => stopRecording(), 30000)

    } catch (err: any) {
      setState('idle')
      if (err.name === 'NotAllowedError') {
        toast.error('Microphone access denied. Please allow microphone access.')
      } else {
        toast.error(`Microphone error: ${err.message}`)
      }
    }
  }, [state, onAudioReady])

  const stopRecording = useCallback(() => {
    clearTimeout(silenceTimer.current)
    if (mediaRecorder.current?.state === 'recording') {
      mediaRecorder.current.stop()
      setState('processing')
    }
  }, [])

  return { state, decibels, startRecording, stopRecording, isRecording: state === 'recording' }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.split(',')[1]) // strip data URL prefix
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
