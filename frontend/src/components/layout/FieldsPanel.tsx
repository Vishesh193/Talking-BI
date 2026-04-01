import { useState } from 'react'
import { ChevronRight, ChevronDown, Hash, Type, Calendar, Search } from 'lucide-react'
import { useBIStore } from '@/stores/biStore'

interface Props {
  onQuery: (q: string) => void
}

export default function FieldsPanel({ onQuery }: Props) {
  const { uploadedFiles, pages, activePageId, selectedPanelId } = useBIStore()
  const [search, setSearch] = useState('')
  const [expandedFile, setExpandedFile] = useState<string | null>(null)

  const activePage = pages.find(p => p.id === activePageId)
  const usedColumns = new Set(
    activePage?.panels.flatMap(p => [
      p.result.intent?.metric,
      p.result.intent?.dimension,
    ].filter(Boolean)) || []
  )

  const filteredFiles = uploadedFiles.map(f => ({
    ...f,
    columns: f.columns.filter(c =>
      !search || c.toLowerCase().includes(search.toLowerCase())
    ),
  }))

  const handleFieldClick = (col: string) => {
    if (selectedPanelId) {
      onQuery(`Update current chart to show ${col}`)
    } else {
      onQuery(`Show me ${col} across the data`)
    }
  }

  const getColIcon = (col: string) => {
    const lc = col.toLowerCase()
    if (['id','count','qty','quantity','total','revenue','price','amount','profit','sales'].some(k => lc.includes(k)))
      return <Hash size={12} style={{ color: 'var(--pbi-blue)', flexShrink: 0 }} />
    if (['date','time','year','month','day','period'].some(k => lc.includes(k)))
      return <Calendar size={12} style={{ color: 'var(--pbi-purple)', flexShrink: 0 }} />
    return <Type size={12} style={{ color: 'var(--neutral-100)', flexShrink: 0 }} />
  }

  return (
    <div
      style={{
        width: 'var(--fields-w)',
        background: 'var(--surface-panel)',
        borderRight: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '10px 12px 8px',
          borderBottom: '1px solid var(--border-light)',
          background: 'var(--neutral-10)',
        }}
      >
        <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.5px', textTransform: 'uppercase', marginBottom: 8 }}>
          Fields
        </div>
        <div style={{ position: 'relative' }}>
          <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-placeholder)' }} />
          <input
            className="input-field"
            style={{ paddingLeft: 26, height: 28, fontSize: 12 }}
            placeholder="Search fields..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Field list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
        {filteredFiles.length === 0 ? (
          <div
            style={{
              padding: '24px 16px',
              textAlign: 'center',
              color: 'var(--text-placeholder)',
              fontSize: 12,
            }}
          >
            <div style={{ marginBottom: 8, fontSize: 24 }}>📂</div>
            Upload a CSV or Excel file to see fields
          </div>
        ) : (
          filteredFiles.map(file => (
            <div key={file.file_id}>
              {/* File header */}
              <button
                onClick={() => setExpandedFile(expandedFile === file.file_id ? null : file.file_id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 12px',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  transition: 'background .12s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--neutral-20)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {expandedFile === file.file_id
                  ? <ChevronDown size={12} style={{ flexShrink: 0 }} />
                  : <ChevronRight size={12} style={{ flexShrink: 0 }} />
                }
                <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.filename}
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-placeholder)', flexShrink: 0 }}>
                  {file.rows.toLocaleString()} rows
                </span>
              </button>

              {/* Columns */}
              {(expandedFile === file.file_id || expandedFile === null) && file.columns.map(col => (
                <div
                  key={col}
                  title={`Ask: "Show ${col} by category"`}
                  onClick={() => handleFieldClick(col)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '4px 12px 4px 28px',
                    cursor: 'pointer',
                    fontSize: 12,
                    color: usedColumns.has(col) ? 'var(--pbi-blue)' : 'var(--text-secondary)',
                    fontWeight: usedColumns.has(col) ? 500 : 400,
                    borderLeft: usedColumns.has(col) ? '2px solid var(--pbi-blue)' : '2px solid transparent',
                    background: usedColumns.has(col) ? 'var(--pbi-blue-light)' : 'transparent',
                    transition: 'background .12s',
                  }}
                  onMouseEnter={e => { if (!usedColumns.has(col)) e.currentTarget.style.background = 'var(--neutral-20)' }}
                  onMouseLeave={e => { if (!usedColumns.has(col)) e.currentTarget.style.background = 'transparent' }}
                >
                  {getColIcon(col)}
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {col.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          ))
        )}

        {/* Demo fields when no file */}
        {filteredFiles.length === 0 && (
          <>
            <div style={{ padding: '8px 12px 4px', fontSize: 11, color: 'var(--text-placeholder)', fontWeight: 600, textTransform: 'uppercase' }}>
              Demo Data
            </div>
            {['revenue','orders','profit','category','region','salesperson','order_date','product_name'].map(col => (
              <div
                key={col}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '4px 12px 4px 16px',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: 'var(--text-secondary)',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--neutral-20)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {getColIcon(col)}
                <span>{col.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
