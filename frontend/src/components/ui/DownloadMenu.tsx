import { saveAs } from 'file-saver'
import toast from 'react-hot-toast'
import { FileText, FileDown, Image } from 'lucide-react'
import { useBIStore } from '@/stores/biStore'

interface Props { onClose: () => void }

export default function DownloadMenu({ onClose }: Props) {
  const { pages, activePageId } = useBIStore()
  const activePage = pages.find(p => p.id === activePageId)

  const downloadJSON = () => {
    const data = JSON.stringify({ pages, exportedAt: new Date().toISOString() }, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    saveAs(blob, 'talking-bi-dashboard.json')
    toast.success('Dashboard exported as JSON')
    onClose()
  }

  const downloadCSV = () => {
    const panels = activePage?.panels || []
    if (!panels.length) { toast.error('No data to export'); return }
    const allRows: any[] = panels.flatMap(p => p.result.chart?.data || [])
    if (!allRows.length) { toast.error('No chart data to export'); return }
    const headers = Object.keys(allRows[0])
    const csv = [
      headers.join(','),
      ...allRows.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(',')),
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    saveAs(blob, `${activePage?.name || 'dashboard'}.csv`)
    toast.success('Data exported as CSV')
    onClose()
  }

  const downloadPDF = async () => {
    try {
      toast('Generating PDF...')
      const { default: html2canvas } = await import('html2canvas')
      const { jsPDF } = await import('jspdf')
      const canvas = document.getElementById('dashboard-canvas')
      if (!canvas) { toast.error('No dashboard to export'); return }
      const img = await html2canvas(canvas, { scale: 2, backgroundColor: '#F3F2F1', useCORS: true })
      const pdf = new jsPDF('landscape', 'pt', 'a4')
      const w = pdf.internal.pageSize.getWidth()
      const h = (img.height / img.width) * w
      pdf.addImage(img.toDataURL('image/png'), 'PNG', 0, 0, w, h)
      pdf.save(`${activePage?.name || 'dashboard'}.pdf`)
      toast.success('Dashboard exported as PDF')
    } catch (e) {
      toast.error('PDF export failed')
    }
    onClose()
  }

  const downloadPNG = async () => {
    try {
      toast('Generating image...')
      const { default: html2canvas } = await import('html2canvas')
      const canvas = document.getElementById('dashboard-canvas')
      if (!canvas) { toast.error('No dashboard to capture'); return }
      const img = await html2canvas(canvas, { scale: 2, backgroundColor: '#F3F2F1', useCORS: true })
      img.toBlob(blob => {
        if (blob) saveAs(blob, `${activePage?.name || 'dashboard'}.png`)
      })
      toast.success('Dashboard saved as PNG')
    } catch {
      toast.error('PNG export failed')
    }
    onClose()
  }

  const items = [
    { icon: FileText, label: 'Export as PDF',  sub: 'Full-page PDF snapshot',  action: downloadPDF },
    { icon: Image,    label: 'Export as PNG',  sub: 'High-res image',          action: downloadPNG },
    { icon: FileDown, label: 'Export data (CSV)', sub: 'All chart data as CSV', action: downloadCSV },
    { icon: FileDown, label: 'Export BI Project (.json)', sub: 'Full project with pages & data', action: downloadJSON },
  ]

  return (
    <div
      style={{
        background: 'var(--surface-card)',
        border: '1px solid var(--border-light)',
        borderRadius: 2,
        boxShadow: 'var(--shadow-panel)',
        minWidth: 220,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '8px 12px',
          fontSize: 11,
          fontWeight: 600,
          color: 'var(--text-placeholder)',
          borderBottom: '1px solid var(--border-light)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        Export
      </div>
      {items.map(({ icon: Icon, label, sub, action }) => (
        <button
          key={label}
          onClick={action}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 14px',
            background: 'transparent',
            cursor: 'pointer',
            transition: 'background .12s',
            textAlign: 'left',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--neutral-10)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <Icon size={15} style={{ color: 'var(--pbi-blue)', flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>{label}</div>
            <div style={{ fontSize: 11, color: 'var(--text-placeholder)' }}>{sub}</div>
          </div>
        </button>
      ))}
    </div>
  )
}
