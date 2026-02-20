/**
 * SetupTable — Reusable dense data grid for VCP / Pullback setups
 *
 * Columns: TICKER | ENTRY | STOP | TARGET | R:R | INFO
 * Clicking a row fires onSelectTicker(ticker)
 */
export default function SetupTable({ title, accentColor, setups, selectedTicker, onSelectTicker, loading }) {
  const count = setups.length

  const color = accentColor === 'blue'
    ? { badge: 'bg-t-blueDim text-t-blue border border-t-blue/30', dot: '#00C8FF', sectionDot: 'bg-t-blue' }
    : { badge: 'bg-t-accentDim text-t-accent border border-t-accent/30', dot: '#F5A623', sectionDot: 'bg-t-accent' }

  return (
    <div className="flex flex-col border-b border-t-border" style={{ background: 'var(--panel)' }}>

      {/* Section header */}
      <div className="section-label">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${color.sectionDot}`} />
        {title}
        <span className={`badge ${color.badge} ml-auto`}>
          {count} setup{count !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-2 flex flex-col gap-1">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="shimmer-row" style={{ opacity: 1 - i * 0.25 }} />
          ))}
        </div>
      ) : count === 0 ? (
        <div className="py-5 text-center text-t-muted text-[10px] tracking-widest uppercase">
          {/* Show blinking cursor if no data at all */}
          No setups <span className="terminal-cursor" />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Ticker</th>
                <th>Entry $</th>
                <th>Stop $</th>
                <th>Target $</th>
                <th>R:R</th>
                <th style={{ textAlign: 'left' }}>Info</th>
              </tr>
            </thead>
            <tbody>
              {setups.map((s) => {
                const isSelected = selectedTicker === s.ticker
                const risk = s.entry - s.stop_loss

                return (
                  <tr
                    key={`${s.ticker}-${s.setup_type}`}
                    className={isSelected ? 'selected' : ''}
                    onClick={() => onSelectTicker(s.ticker)}
                  >
                    {/* Ticker */}
                    <td>
                      <span
                        className="font-600 tracking-wide"
                        style={{ color: isSelected ? 'var(--accent)' : color.dot }}
                      >
                        {s.ticker}
                      </span>
                    </td>

                    {/* Entry */}
                    <td className="text-t-text">{fmt(s.entry)}</td>

                    {/* Stop — red */}
                    <td style={{ color: 'var(--halt)' }}>{fmt(s.stop_loss)}</td>

                    {/* Target — green */}
                    <td style={{ color: 'var(--go)' }}>{fmt(s.take_profit)}</td>

                    {/* R:R */}
                    <td className="text-t-muted">{s.rr.toFixed(1)}</td>

                    {/* Info badge */}
                    <td style={{ textAlign: 'left' }}>
                      {s.setup_type === 'VCP' ? (
                        <span className={`badge ${s.is_breakout ? 'bg-t-goDim text-t-go' : 'bg-t-accentDim text-t-accent'}`}>
                          {s.is_breakout ? 'BRK' : 'DRY'}
                        </span>
                      ) : (
                        <span className="text-t-muted text-[9px]">
                          CCI {s.cci_today?.toFixed(0) ?? '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/** Format a price number to 2 decimal places */
const fmt = (n) => (n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
