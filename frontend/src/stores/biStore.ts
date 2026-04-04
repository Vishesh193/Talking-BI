import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ─── Core BI Types ───────────────────────────────────────────────────────────

export type ChartType =
  | 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'scatter'
  | 'grouped_bar' | 'stacked_bar' | 'stacked_area'
  | 'kpi_card' | 'table' | 'heatmap' | 'sankey' | 'geomap'
  | 'treemap' | 'waterfall' | 'gauge' | 'bullet'

export interface InsightCard {
  title: string
  body: string
  metric?: string
  change_pct?: number
  direction?: 'up' | 'down' | 'neutral'
  confidence: number
  action?: string
  is_anomaly: boolean
}

export interface StrategyRecommendation {
  title: string
  recommendation: string
  category: string
  impact: 'High' | 'Medium' | 'Low'
}

export interface SimulationResult {
  scenario: string
  baseline_value: number
  simulated_value: number
  net_change_pct: number
  confidence: number
  reasoning: string
  impact_level: 'Positive' | 'Negative' | 'Neutral'
}

export interface ChartConfig {
  type: ChartType
  title: string
  data: Record<string, any>[]
  x_key: string
  y_keys: string[]
  colors: string[]
  unit?: string
  show_legend: boolean
  show_grid: boolean
  kpi_value?: number
  kpi_label?: string
  kpi_value_key?: string
  kpi_secondary_key?: string
  kpi_delta?: number
  kpi_direction?: 'up' | 'down' | 'neutral'
}

export interface Intent {
  type: string
  metric?: string
  dimension?: string
  period_a?: string
  period_b?: string
  filters?: Record<string, any>
  data_source?: string
}

export interface DataQualityReport {
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

export interface AgentResult {
  session_id: string
  transcript: string
  intent?: Intent
  sql?: string
  data_source_used?: string
  row_count: number
  quality?: DataQualityReport
  chart?: ChartConfig
  insights: InsightCard[]
  strategies: StrategyRecommendation[]
  simulation?: SimulationResult
  suggestions: string[]
  tts_text?: string
  execution_time_ms: number
  error?: string
  needs_clarification?: boolean
  clarification_question?: string
  update_panel_id?: string  // If present, the agent wants to update this specific panel
  layout_override?: {
    w?: number
    h?: number
    x?: number
    y?: number
  }
}

// ─── Dashboard Page / Sheet ───────────────────────────────────────────────────

export interface CanvasPanel {
  id: string
  result: AgentResult
  timestamp: Date
  pinned: boolean
  // Position on canvas
  x: number
  y: number
  w: number  // grid units (1–6)
  h: number  // height category: 1=small, 2=medium, 3=large
  chartTypeOverride?: ChartType  // user can change chart type
  colorOverride?: string // user can override the primary color
}

export interface DashboardAdvancedMeta {
  dashboard_title?: string
  filter_pills?: { label: string }[]
  colors?: {
    primary: string
    secondary: string
    positive: string
    negative: string
    background?: string
  }
}

export interface DashboardPage {
  id: string
  name: string
  panels: CanvasPanel[]
  advancedMeta?: DashboardAdvancedMeta
}

// ─── File Analysis / Dashboard Suggestion Flow ───────────────────────────────

export interface DashboardSuggestion {
  id: string
  title: string
  description: string
  chart_types: string[]
  focus: string
  preview_kpis: string[]
}

export interface ClarifyingQuestion {
  id: string
  question: string
  options: string[]
  allow_custom: boolean
  skippable: boolean
}

export interface FileAnalysisResult {
  file_id: string
  filename: string
  rows: number
  columns: string[]
  column_types: Record<string, string>
  suggestions: DashboardSuggestion[]
  clarifying_questions: ClarifyingQuestion[]
}

// ─── Agent State ─────────────────────────────────────────────────────────────

export type AgentStage =
  | 'idle' | 'listening' | 'transcribing' | 'thinking'
  | 'querying' | 'rendering' | 'done' | 'error'

// ─── Zustand Store ───────────────────────────────────────────────────────────

interface BIStore {
  // Session
  sessionId: string
  resetSession: () => void

  // WebSocket
  wsConnected: boolean
  setWsConnected: (v: boolean) => void

  // Agent state
  agentStage: AgentStage
  setAgentStage: (s: AgentStage) => void
  agentMessage: string
  setAgentMessage: (m: string) => void

  // Current transcript (shown while thinking)
  currentTranscript: string
  setCurrentTranscript: (t: string) => void

  // Clarification
  clarificationQuestion: string | null
  setClarificationQuestion: (q: string | null) => void

  // TTS
  ttsEnabled: boolean
  toggleTts: () => void
  lastTtsText: string | null
  setLastTtsText: (t: string | null) => void

  // ── Multi-page Dashboard ────────────────────────────────────────────
  pages: DashboardPage[]
  activePageId: string | null
  setActivePageId: (id: string) => void
  addPage: (name?: string) => string  // returns new page id
  removePage: (id: string) => void
  renamePage: (id: string, name: string) => void
  setPageAdvancedMeta: (pageId: string, meta: DashboardAdvancedMeta) => void

  // Panels (within active page)
  // Panels (within active page)
  addPanel: (result: AgentResult, pageId?: string) => void
  updatePanelResult: (panelId: string, result: AgentResult, pageId?: string) => void
  removePanel: (panelId: string, pageId?: string) => void
  pinPanel: (panelId: string, pageId?: string) => void
  updatePanelChart: (panelId: string, chartType: ChartType, pageId?: string) => void
  updatePanelColor: (panelId: string, color: string, pageId?: string) => void
  movePanelLayout: (panelId: string, updates: Partial<Pick<CanvasPanel,'x'|'y'|'w'|'h'>>, pageId?: string) => void
  clearPage: (pageId?: string) => void

  // ── File Upload / Analysis Flow ──────────────────────────────────────
  uploadedFiles: { file_id: string; filename: string; rows: number; columns: string[] }[]
  addUploadedFile: (f: any) => void

  // Dashboard suggestion modal
  fileAnalysis: FileAnalysisResult | null
  setFileAnalysis: (r: FileAnalysisResult | null) => void

  // ── Connectors ───────────────────────────────────────────────────────
  connectors: any[]
  setConnectors: (c: any[]) => void

  // ── UI State ─────────────────────────────────────────────────────────
  showSettings: boolean
  setShowSettings: (v: boolean) => void
  showFieldsPanel: boolean
  toggleFieldsPanel: () => void
  showVizPanel: boolean
  toggleVizPanel: () => void
  showConnectorsPanel: boolean
  toggleConnectorsPanel: () => void
  activeRibbonTab: 'home' | 'insert' | 'view' | 'data'
  setActiveRibbonTab: (t: 'home' | 'insert' | 'view' | 'data') => void

  // Selected panel for editing
  selectedPanelId: string | null
  setSelectedPanelId: (id: string | null) => void

  // Query history
  queryHistory: { transcript: string; timestamp: Date; success: boolean }[]
  addToHistory: (transcript: string, success: boolean) => void
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const DEFAULT_PAGE: DashboardPage = {
  id: 'page-1',
  name: 'Page 1',
  panels: [],
}

export const useBIStore = create<BIStore>()(
  persist(
    (set, get) => ({
      sessionId: `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,

      wsConnected: false,
      setWsConnected: (v) => set({ wsConnected: v }),

      agentStage: 'idle',
      setAgentStage: (s) => set({ agentStage: s }),
      agentMessage: '',
      setAgentMessage: (m) => set({ agentMessage: m }),

      currentTranscript: '',
      setCurrentTranscript: (t) => set({ currentTranscript: t }),

      clarificationQuestion: null,
      setClarificationQuestion: (q) => set({ clarificationQuestion: q }),

      ttsEnabled: true,
      toggleTts: () => set((s) => ({ ttsEnabled: !s.ttsEnabled })),
      lastTtsText: null,
      setLastTtsText: (t) => set({ lastTtsText: t }),
      resetSession: () => {
        const newSessionId = crypto.randomUUID()
        set({
          sessionId: newSessionId,
          queryHistory: [],
          pages: [{ id: 'page-1', name: 'Sales Summary', panels: [] }],
          activePageId: 'page-1',
          uploadedFiles: [],
          selectedPanelId: null,
          lastTtsText: null,
          clarificationQuestion: null,
        })
        console.log('[Store] Session reset. New ID:', newSessionId)
      },

      // ── Multi-page Dashboard ──────────────────────────────────────────
      pages: [{ ...DEFAULT_PAGE }],
      activePageId: 'page-1',

      setActivePageId: (id) => set({ activePageId: id }),

      addPage: (name) => {
        const id = `page-${generateId()}`
        const count = get().pages.length + 1
        set((s) => ({
          pages: [...s.pages, { id, name: name || `Page ${count}`, panels: [] }],
          activePageId: id,
        }))
        return id
      },

      removePage: (id) => set((s) => {
        if (s.pages.length <= 1) return {}
        const newPages = s.pages.filter(p => p.id !== id)
        return {
          pages: newPages,
          activePageId: s.activePageId === id ? newPages[0].id : s.activePageId,
        }
      }),

      renamePage: (id, name) => set((s) => ({
        pages: s.pages.map(p => p.id === id ? { ...p, name } : p),
      })),

      setPageAdvancedMeta: (pageId, meta) => set((s) => ({
        pages: s.pages.map(p => p.id === pageId ? { ...p, advancedMeta: meta } : p),
      })),

      // ── Panel operations ──────────────────────────────────────────────
      addPanel: (result, pageId) => set((s) => {
        const targetId = pageId || s.activePageId || 'page-1'
        
        // If result explicitly targets a panel, update it instead
        if (result.update_panel_id) {
          const page = s.pages.find(p => p.id === targetId)
          if (page?.panels.find(pan => pan.id === result.update_panel_id)) {
             return {
              pages: s.pages.map(p =>
                p.id === targetId
                  ? { ...p, panels: p.panels.map(pan => pan.id === result.update_panel_id ? { ...pan, result } : pan) }
                  : p
              ),
            }
          }
        }

        const id = `panel-${generateId()}`

        // Auto-layout: place in next available slot
        const page = s.pages.find(p => p.id === targetId)
        const existingCount = page?.panels.length || 0
        const col = existingCount % 2  // 0 or 1
        const row = Math.floor(existingCount / 2)

        const newPanel: CanvasPanel = {
          id,
          result,
          timestamp: new Date(),
          pinned: false,
          x: result.layout_override?.x ?? (col * 3),
          y: result.layout_override?.y ?? row,
          w: result.layout_override?.w ?? (result.chart?.type === 'kpi_card' ? 1 : 3),
          h: result.layout_override?.h ?? (result.chart?.type === 'kpi_card' ? 1 : 2),
        }

        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: [newPanel, ...p.panels.slice(0, 19)] }
              : p
          ),
          selectedPanelId: id,
        }
      }),

      updatePanelResult: (panelId, result, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.map(pan => pan.id === panelId ? { ...pan, result } : pan) }
              : p
          ),
        }
      }),

      removePanel: (panelId, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.filter(pan => pan.id !== panelId) }
              : p
          ),
          selectedPanelId: s.selectedPanelId === panelId ? null : s.selectedPanelId,
        }
      }),

      pinPanel: (panelId, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.map(pan => pan.id === panelId ? { ...pan, pinned: !pan.pinned } : pan) }
              : p
          ),
        }
      }),

      updatePanelChart: (panelId, chartType, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.map(pan => pan.id === panelId ? { ...pan, chartTypeOverride: chartType } : pan) }
              : p
          ),
        }
      }),

      updatePanelColor: (panelId, color, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.map(pan => pan.id === panelId ? { ...pan, colorOverride: color } : pan) }
              : p
          ),
        }
      }),

      movePanelLayout: (panelId, updates, pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p =>
            p.id === targetId
              ? { ...p, panels: p.panels.map(pan => pan.id === panelId ? { ...pan, ...updates } : pan) }
              : p
          ),
        }
      }),

      clearPage: (pageId) => set((s) => {
        const targetId = pageId || s.activePageId
        return {
          pages: s.pages.map(p => p.id === targetId ? { ...p, panels: [] } : p),
          selectedPanelId: null,
        }
      }),

      // ── File upload / analysis ────────────────────────────────────────
      uploadedFiles: [],
      addUploadedFile: (f) => set((s) => ({ uploadedFiles: [...s.uploadedFiles, f] })),

      fileAnalysis: null,
      setFileAnalysis: (r) => set({ fileAnalysis: r }),

      // ── Connectors ───────────────────────────────────────────────────
      connectors: [],
      setConnectors: (c) => set({ connectors: c }),

      // ── UI State ────────────────────────────────────────────────────
      showSettings: false,
      setShowSettings: (v) => set({ showSettings: v }),

      showFieldsPanel: true,
      toggleFieldsPanel: () => set((s) => ({ showFieldsPanel: !s.showFieldsPanel })),

      showVizPanel: true,
      toggleVizPanel: () => set((s) => ({ showVizPanel: !s.showVizPanel })),

      showConnectorsPanel: false,
      toggleConnectorsPanel: () => set((s) => ({ showConnectorsPanel: !s.showConnectorsPanel })),

      activeRibbonTab: 'home',
      setActiveRibbonTab: (t) => set({ activeRibbonTab: t }),

      selectedPanelId: null,
      setSelectedPanelId: (id) => set({ selectedPanelId: id }),

      queryHistory: [],
      addToHistory: (transcript, success) => set((s) => ({
        queryHistory: [
          { transcript, timestamp: new Date(), success },
          ...s.queryHistory.slice(0, 49),
        ],
      })),
    }),
    {
      name: 'talking-bi-store',
      // Only persist non-session data
      partialize: (s) => ({
        pages: s.pages,
        ttsEnabled: s.ttsEnabled,
        showFieldsPanel: s.showFieldsPanel,
        showVizPanel: s.showVizPanel,
        uploadedFiles: s.uploadedFiles,
        queryHistory: s.queryHistory,
        activePageId: s.activePageId,
        activeRibbonTab: s.activeRibbonTab,
        sessionId: s.sessionId,
      }),
    }
  )
)
