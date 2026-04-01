import { BarChart2, Upload, Zap, TrendingUp, PieChart, Table2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { useBIStore } from '@/stores/biStore'
import { apiService } from '@/services/api'
import toast from 'react-hot-toast'

interface Props {
  onQuery: (q: string) => void
}

const EXAMPLE_TILES = [
  { icon: TrendingUp, label: 'Revenue trend', query: 'Show revenue trend over time as a line chart' },
  { icon: BarChart2, label: 'Top products',   query: 'Show top 5 products by revenue as a bar chart' },
  { icon: PieChart,  label: 'By region',      query: 'Show revenue breakdown by region as a pie chart' },
  { icon: Table2,    label: 'Full summary',   query: 'Give me a full summary of the data' },
  { icon: Zap,       label: 'Key insights',   query: 'What are the key insights and anomalies?' },
]

export default function EmptyCanvas({ onQuery }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const { sessionId, setFileAnalysis, addUploadedFile } = useBIStore()

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await apiService.analyzeFile(file, sessionId)
      addUploadedFile({ file_id: result.file_id, filename: result.filename, rows: result.rows, columns: result.columns })
      setFileAnalysis(result)
      toast.success(`"${result.filename}" ready — choose your dashboard layout`)
    } catch {
      toast.error('Failed to analyze file')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
        background: 'var(--surface-page)',
        gap: 32,
      }}
    >
      {/* Hero */}
      <div style={{ textAlign: 'center', maxWidth: 500 }}>
        <div
          style={{
            width: 64,
            height: 64,
            background: 'linear-gradient(135deg, #0078D4, #00B7C3)',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 4px 16px rgba(0,120,212,.25)',
          }}
        >
          <BarChart2 size={30} color="#fff" />
        </div>
        <h1
          style={{
            fontSize: 26,
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: 10,
            letterSpacing: '-0.5px',
          }}
        >
          Welcome to Talking BI
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Upload your data and instantly get AI-generated dashboards with charts,
          insights, and voice control — powered by natural language.
        </p>
      </div>

      {/* Upload card */}
      <div
        onClick={() => fileRef.current?.click()}
        style={{
          width: '100%',
          maxWidth: 440,
          border: '2px dashed var(--pbi-blue-mid)',
          borderRadius: 4,
          padding: '28px 24px',
          textAlign: 'center',
          cursor: uploading ? 'wait' : 'pointer',
          background: uploading ? 'var(--pbi-blue-light)' : 'var(--surface-card)',
          transition: 'background .15s, border-color .15s',
        }}
        onMouseEnter={e => !uploading && ((e.currentTarget.style.background = 'var(--pbi-blue-light)'), (e.currentTarget.style.borderColor = 'var(--pbi-blue)'))}
        onMouseLeave={e => !uploading && ((e.currentTarget.style.background = 'var(--surface-card)'), (e.currentTarget.style.borderColor = 'var(--pbi-blue-mid)'))}
      >
        <Upload size={32} style={{ color: 'var(--pbi-blue)', marginBottom: 12 }} />
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)', marginBottom: 6 }}>
          {uploading ? 'Analyzing your data...' : 'Upload your data file'}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          CSV, Excel (.xlsx, .xls) · up to 50 MB
        </div>
        <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile} style={{ display: 'none' }} />
      </div>

      {/* Divider */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, width: '100%', maxWidth: 440 }}>
        <div style={{ flex: 1, height: 1, background: 'var(--border-light)' }} />
        <span style={{ fontSize: 12, color: 'var(--text-placeholder)' }}>or try demo data</span>
        <div style={{ flex: 1, height: 1, background: 'var(--border-light)' }} />
      </div>

      {/* Example queries */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          justifyContent: 'center',
          maxWidth: 600,
        }}
      >
        {EXAMPLE_TILES.map(({ icon: Icon, label, query }) => (
          <button
            key={label}
            onClick={() => onQuery(query)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              background: 'var(--surface-card)',
              border: '1px solid var(--border-light)',
              borderRadius: 2,
              fontSize: 13,
              color: 'var(--text-primary)',
              cursor: 'pointer',
              transition: 'all .12s',
              boxShadow: 'var(--shadow-card)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--pbi-blue-light)'
              e.currentTarget.style.borderColor = 'var(--pbi-blue-mid)'
              e.currentTarget.style.color = 'var(--pbi-blue)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'var(--surface-card)'
              e.currentTarget.style.borderColor = 'var(--border-light)'
              e.currentTarget.style.color = 'var(--text-primary)'
            }}
          >
            <Icon size={15} style={{ flexShrink: 0 }} />
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
