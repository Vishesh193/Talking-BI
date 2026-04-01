import type { ChartConfig } from '@/stores/biStore'

interface Props { config: ChartConfig }

export default function DataTable({ config }: Props) {
  const { data, x_key, y_keys } = config
  if (!data?.length) return null

  const headers = [x_key, ...y_keys].filter(Boolean)

  return (
    <div style={{ overflowX: 'auto', maxHeight: 260 }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 12,
          fontFamily: 'var(--font-ui)',
        }}
      >
        <thead>
          <tr>
            {headers.map(h => (
              <th
                key={h}
                style={{
                  padding: '7px 10px',
                  background: 'var(--neutral-20)',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  textAlign: 'left',
                  borderBottom: '1px solid var(--border-default)',
                  whiteSpace: 'nowrap',
                  position: 'sticky',
                  top: 0,
                  textTransform: 'capitalize',
                }}
              >
                {h.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 100).map((row, i) => (
            <tr
              key={i}
              style={{
                background: i % 2 === 0 ? 'var(--surface-card)' : 'var(--neutral-10)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--pbi-blue-light)')}
              onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? 'var(--surface-card)' : 'var(--neutral-10)')}
            >
              {headers.map(h => {
                const val = row[h]
                const isNum = typeof val === 'number'
                return (
                  <td
                    key={h}
                    style={{
                      padding: '6px 10px',
                      borderBottom: '1px solid var(--border-light)',
                      color: isNum ? 'var(--pbi-blue)' : 'var(--text-primary)',
                      fontWeight: isNum ? 500 : 400,
                      textAlign: isNum ? 'right' : 'left',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {isNum ? val.toLocaleString() : String(val ?? '-')}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <div style={{ padding: '6px 10px', fontSize: 11, color: 'var(--text-placeholder)', textAlign: 'center', borderTop: '1px solid var(--border-light)' }}>
          Showing 100 of {data.length} rows
        </div>
      )}
    </div>
  )
}
