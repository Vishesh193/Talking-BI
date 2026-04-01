import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useBIStore } from '@/stores/biStore'
import { apiService } from '@/services/api'
import {
  History, Database, Upload, Zap, ChevronRight,
  CheckCircle, XCircle, Clock, Plus, FileSpreadsheet
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'

type SidebarTab = 'history' | 'connectors' | 'files' | 'kpis'

interface SidebarProps {
  ws: { sendTextQuery: (q: string) => void }
}

export default function Sidebar({ ws }: SidebarProps) {
  const [tab, setTab] = useState<SidebarTab>('history')
  const [collapsed, setCollapsed] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const { queryHistory, uploadedFiles, addUploadedFile, sessionId } = useBIStore()
  const qc = useQueryClient()

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors'],
    queryFn: apiService.getConnectors,
    refetchInterval: 30000,
  })

  const { data: kpis = [] } = useQuery({
    queryKey: ['kpis'],
    queryFn: apiService.getKPIs,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiService.uploadFile(file, sessionId),
    onSuccess: (data) => {
      addUploadedFile(data)
      toast.success(`${data.filename} uploaded — ${data.rows} rows`)
    },
    onError: () => toast.error('Upload failed'),
  })

  const seedMutation = useMutation({
    mutationFn: apiService.seedDemoKPIs,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kpis'] })
      toast.success('Demo KPIs seeded')
    },
  })

  const tabs: { id: SidebarTab; icon: any; label: string; count?: number }[] = [
    { id: 'history', icon: History, label: 'History', count: queryHistory.length },
    { id: 'connectors', icon: Database, label: 'Sources', count: connectors.filter((c: any) => c.connected).length },
    { id: 'files', icon: Upload, label: 'Files', count: uploadedFiles.length },
    { id: 'kpis', icon: Zap, label: 'KPIs', count: kpis.length },
  ]

  if (collapsed) {
    return (
      <div className="w-12 border-r border-border bg-surface shrink-0 flex flex-col items-center py-4 gap-3">
        {tabs.map(t => (
          <button key={t.id} onClick={() => { setTab(t.id); setCollapsed(false) }}
            className="p-2 text-ink-dim hover:text-accent transition-colors relative">
            <t.icon size={14} />
            {t.count ? <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-accent text-bg text-[8px] flex items-center justify-center font-bold">{t.count}</span> : null}
          </button>
        ))}
        <button onClick={() => setCollapsed(false)} className="mt-auto p-2 text-ink-dim hover:text-accent">
          <ChevronRight size={12} />
        </button>
      </div>
    )
  }

  return (
    <div className="w-56 lg:w-64 border-r border-border bg-surface shrink-0 flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-border shrink-0">
        {tabs.map(t => (
          <button key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx('flex-1 flex flex-col items-center py-2.5 gap-0.5 transition-colors relative',
              tab === t.id ? 'text-accent bg-accent/5' : 'text-ink-dim hover:text-ink'
            )}
          >
            <t.icon size={12} />
            <span className="text-[8px] tracking-wider">{t.label}</span>
            {t.count ? (
              <span className={clsx('text-[8px]', tab === t.id ? 'text-accent' : 'text-ink-dim')}>
                {t.count}
              </span>
            ) : null}
            {tab === t.id && <div className="absolute bottom-0 left-0 right-0 h-px bg-accent" />}
          </button>
        ))}
        <button onClick={() => setCollapsed(true)}
          className="px-2 text-ink-dim hover:text-ink border-l border-border">
          <ChevronRight size={10} className="rotate-180" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">

        {/* HISTORY */}
        {tab === 'history' && (
          <div className="p-2 space-y-1">
            <div className="section-label px-2 py-1">Recent Queries</div>
            {queryHistory.length === 0 && (
              <div className="text-ink-dim text-[11px] px-2 py-4 text-center">No queries yet.<br />Try asking something!</div>
            )}
            {queryHistory.map((h, i) => (
              <button key={i}
                onClick={() => ws.sendTextQuery(h.transcript)}
                className="w-full text-left px-2 py-1.5 rounded-sm hover:bg-surface2 transition-colors group"
              >
                <div className="flex items-start gap-1.5">
                  {h.success
                    ? <CheckCircle size={10} className="text-accent3 mt-0.5 shrink-0" />
                    : <XCircle size={10} className="text-red-400 mt-0.5 shrink-0" />
                  }
                  <div className="min-w-0">
                    <div className="text-[11px] text-ink truncate group-hover:text-accent transition-colors">{h.transcript}</div>
                    <div className="text-[9px] text-ink-dim flex items-center gap-1 mt-0.5">
                      <Clock size={8} />
                      {h.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* CONNECTORS */}
        {tab === 'connectors' && (
          <div className="p-2 space-y-2">
            <div className="section-label px-2 py-1">Data Sources</div>
            {connectors.map((c: any, i: number) => (
              <div key={i} className={clsx('px-3 py-2.5 rounded-sm border', c.connected ? 'border-accent3/20 bg-accent3/5' : 'border-border bg-surface2')}>
                <div className="flex items-center gap-2 mb-1">
                  <div className={clsx('w-1.5 h-1.5 rounded-full', c.connected ? 'bg-accent3' : 'bg-ink-dim')} />
                  <span className="text-xs font-display font-bold">{c.name}</span>
                  <span className={clsx('tag ml-auto', c.connected ? 'tag-green' : 'text-ink-dim border-border')}>{c.connected ? 'Live' : 'Off'}</span>
                </div>
                {c.error && <div className="text-[10px] text-ink-dim mt-1 leading-relaxed">{c.error}</div>}
                {c.tables_or_endpoints?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {c.tables_or_endpoints.slice(0, 4).map((t: string) => (
                      <span key={t} className="text-[9px] px-1.5 py-0.5 bg-surface rounded-sm text-ink-dim border border-border">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* FILES */}
        {tab === 'files' && (
          <div className="p-2 space-y-2">
            <div className="section-label px-2 py-1">Uploaded Files</div>
            <button
              onClick={() => fileInput.current?.click()}
              disabled={uploadMutation.isPending}
              className="w-full border border-dashed border-border hover:border-accent/40 text-ink-dim hover:text-accent text-[11px] rounded-sm py-3 flex flex-col items-center gap-1 transition-all"
            >
              <Upload size={14} />
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Excel / CSV'}
            </button>
            <input ref={fileInput} type="file" accept=".csv,.xlsx,.xls" className="hidden"
              onChange={e => e.target.files?.[0] && uploadMutation.mutate(e.target.files[0])} />

            {uploadedFiles.length === 0 && (
              <div className="text-ink-dim text-[11px] px-2 py-2 text-center">No files uploaded yet</div>
            )}
            {uploadedFiles.map((f, i) => (
              <div key={i} className="px-3 py-2 rounded-sm border border-border bg-surface2">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet size={12} className="text-accent3 shrink-0" />
                  <span className="text-[11px] font-mono truncate">{f.filename}</span>
                </div>
                <div className="text-[9px] text-ink-dim mt-1">{f.rows.toLocaleString()} rows · {f.columns.length} columns</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {f.columns.slice(0, 4).map((c: string) => (
                    <span key={c} className="text-[8px] px-1 py-0.5 bg-surface border border-border rounded-sm text-ink-dim">{c}</span>
                  ))}
                  {f.columns.length > 4 && <span className="text-[8px] text-ink-dim">+{f.columns.length - 4}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* KPI REGISTRY */}
        {tab === 'kpis' && (
          <div className="p-2 space-y-2">
            <div className="section-label px-2 py-1">KPI Registry</div>
            {kpis.length === 0 && (
              <button onClick={() => seedMutation.mutate()}
                className="w-full border border-dashed border-border hover:border-accent/40 text-ink-dim hover:text-accent text-[11px] rounded-sm py-3 flex flex-col items-center gap-1 transition-all">
                <Plus size={14} />
                Seed Demo KPIs
              </button>
            )}
            {kpis.map((k: any) => (
              <div key={k.id} className="px-3 py-2 rounded-sm border border-border bg-surface2 hover:border-accent/20 transition-colors cursor-pointer"
                onClick={() => ws.sendTextQuery(`Show me ${k.display_name}`)}>
                <div className="flex items-center gap-2">
                  <span className={clsx('tag', k.direction === 'up_good' ? 'tag-green' : 'tag-orange')}>
                    {k.direction === 'up_good' ? '↑' : '↓'}
                  </span>
                  <span className="text-[11px] font-display font-bold text-ink">{k.display_name}</span>
                </div>
                {k.description && <div className="text-[10px] text-ink-dim mt-1">{k.description}</div>}
                <div className="flex gap-1 mt-1">
                  <span className="tag tag-blue">{k.category}</span>
                  <span className="tag" style={{ color: '#6b8399', borderColor: '#1e2c3a' }}>{k.unit}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
