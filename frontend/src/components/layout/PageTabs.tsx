import { useState } from 'react'
import { Plus, X, Edit2, Check } from 'lucide-react'
import { useBIStore } from '@/stores/biStore'

export default function PageTabs() {
  const { pages, activePageId, setActivePageId, addPage, removePage, renamePage } = useBIStore()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const startEdit = (id: string, name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(id)
    setEditValue(name)
  }

  const confirmEdit = () => {
    if (editingId && editValue.trim()) renamePage(editingId, editValue.trim())
    setEditingId(null)
  }

  return (
    <div
      style={{
        height: 'var(--pagetabs-h)',
        background: 'var(--neutral-20)',
        borderTop: '1px solid var(--border-light)',
        display: 'flex',
        alignItems: 'flex-end',
        padding: '0 8px',
        gap: 2,
        overflowX: 'auto',
        flexShrink: 0,
      }}
    >
      {pages.map(page => {
        const isActive = page.id === activePageId
        return (
          <div
            key={page.id}
            onClick={() => setActivePageId(page.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0 12px',
              height: 28,
              background: isActive ? 'var(--surface-card)' : 'transparent',
              borderTop: isActive ? '2px solid var(--pbi-blue)' : '2px solid transparent',
              borderLeft: isActive ? '1px solid var(--border-light)' : 'none',
              borderRight: isActive ? '1px solid var(--border-light)' : 'none',
              cursor: 'pointer',
              borderRadius: '2px 2px 0 0',
              flexShrink: 0,
              userSelect: 'none',
            }}
          >
            {editingId === page.id ? (
              <>
                <input
                  autoFocus
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' ? confirmEdit() : e.key === 'Escape' && setEditingId(null)}
                  onClick={e => e.stopPropagation()}
                  style={{
                    width: 80,
                    height: 20,
                    fontSize: 12,
                    border: '1px solid var(--pbi-blue)',
                    borderRadius: 2,
                    padding: '0 4px',
                    outlineColor: 'var(--pbi-blue)',
                  }}
                />
                <button
                  onClick={e => { e.stopPropagation(); confirmEdit() }}
                  style={{ color: 'var(--pbi-blue)', padding: 2 }}
                >
                  <Check size={11} />
                </button>
              </>
            ) : (
              <>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    whiteSpace: 'nowrap',
                    maxWidth: 120,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {page.name}
                </span>
                {isActive && pages.length > 1 && (
                  <div style={{ display: 'flex', gap: 2, marginLeft: 2 }}>
                    <button
                      onClick={e => startEdit(page.id, page.name, e)}
                      className="btn-icon"
                      style={{ width: 16, height: 16 }}
                      title="Rename"
                    >
                      <Edit2 size={9} />
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); removePage(page.id) }}
                      className="btn-icon"
                      style={{ width: 16, height: 16, color: 'var(--pbi-red)' }}
                      title="Delete page"
                    >
                      <X size={9} />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )
      })}

      {/* Add page button */}
      <button
        onClick={() => addPage()}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '0 10px',
          height: 24,
          fontSize: 12,
          color: 'var(--text-secondary)',
          borderRadius: 2,
          transition: 'background .12s',
          alignSelf: 'center',
          marginLeft: 4,
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'var(--neutral-30)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        title="Add page"
      >
        <Plus size={13} />
        <span>New Page</span>
      </button>
    </div>
  )
}
