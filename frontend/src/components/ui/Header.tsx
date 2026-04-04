import { useBIStore } from '@/stores/biStore'
import { Settings, Wifi, WifiOff, Volume2, VolumeX, Trash2, Pin } from 'lucide-react'
import clsx from 'clsx'

const STAGE_LABELS: Record<string, string> = {
  idle: 'Ready',
  listening: 'Listening...',
  transcribing: 'Transcribing...',
  thinking: 'Agents thinking...',
  querying: 'Querying data...',
  rendering: 'Rendering...',
  done: 'Done',
  error: 'Error',
}

const STAGE_COLORS: Record<string, string> = {
  idle: 'text-ink-dim',
  listening: 'text-accent',
  transcribing: 'text-accent4',
  thinking: 'text-accent4',
  querying: 'text-accent2',
  rendering: 'text-accent3',
  done: 'text-accent3',
  error: 'text-red-400',
}

export default function Header() {
  const {
    wsConnected, agentStage, agentMessage,
    pages, activePageId, clearPage, ttsEnabled, toggleTts,
    setShowSettings, currentTranscript,
  } = useBIStore()

  const activePage = pages.find(p => p.id === activePageId)
  const panels = activePage?.panels || []

  const isActive = !['idle', 'done', 'error'].includes(agentStage)

  return (
    <header className="border-b border-border bg-surface/60 backdrop-blur-sm px-4 lg:px-6 py-3 flex items-center gap-4 shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3 mr-4">
        <div className="w-6 h-6 rounded-sm bg-accent flex items-center justify-center">
          <span className="text-bg text-[10px] font-display font-black">BI</span>
        </div>
        <span className="font-display font-bold text-sm tracking-tight hidden sm:block">Talking BI</span>
      </div>

      {/* Agent status */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {isActive && (
          <div className="flex gap-1 items-center">
            <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-accent4 inline-block" />
            <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-accent4 inline-block" />
            <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-accent4 inline-block" />
          </div>
        )}
        <span className={clsx('text-xs font-mono truncate transition-colors', STAGE_COLORS[agentStage])}>
          {isActive ? agentMessage || STAGE_LABELS[agentStage] : (
            currentTranscript
              ? <span className="text-ink-dim">Last: "{currentTranscript}"</span>
              : <span className="text-ink-dim">{STAGE_LABELS[agentStage]}</span>
          )}
        </span>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Panel count */}
        {panels.length > 0 && (
          <span className="tag tag-blue hidden sm:inline">{panels.length} panels</span>
        )}

        {/* TTS toggle */}
        <button
          onClick={toggleTts}
          className={clsx('p-1.5 rounded-sm border transition-all', ttsEnabled
            ? 'border-accent/30 text-accent hover:bg-accent/10'
            : 'border-border text-ink-dim hover:border-accent/30'
          )}
          title={ttsEnabled ? 'Disable voice responses' : 'Enable voice responses'}
        >
          {ttsEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
        </button>

        {/* Clear panels */}
        {panels.length > 0 && (
          <button
            onClick={() => clearPage()}
            className="p-1.5 rounded-sm border border-border text-ink-dim hover:border-red-400/30 hover:text-red-400 transition-all"
            title="Clear all panels"
          >
            <Trash2 size={13} />
          </button>
        )}

        {/* Settings */}
        <button
          onClick={() => setShowSettings(true)}
          className="p-1.5 rounded-sm border border-border text-ink-dim hover:border-accent/30 hover:text-accent transition-all"
          title="Settings"
        >
          <Settings size={13} />
        </button>

        {/* Connection indicator */}
        <div className={clsx('flex items-center gap-1.5 px-2 py-1 rounded-sm border text-[10px] font-mono tracking-wider',
          wsConnected
            ? 'border-accent3/30 text-accent3 bg-accent3/5'
            : 'border-red-500/30 text-red-400 bg-red-500/5'
        )}>
          {wsConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
          <span className="hidden sm:inline">{wsConnected ? 'Live' : 'Offline'}</span>
        </div>
      </div>
    </header>
  )
}
