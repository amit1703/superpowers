/**
 * SetupTable — Reusable dense data grid for VCP / Pullback setups
 *
 * Columns: TICKER | ENTRY | STOP | TARGET | R:R | INFO
 *
 * Row highlighting:
 *   - Green background  → Volume Surge confirmed (is_vol_surge === true)
 *   - Amber border-left → Selected ticker
 *
 * Info column badges (VCP):
 *   BRK  → Confirmed breakout (is_breakout true, vol surge, RS+)
 *   DRY  → Coiled spring dry-up below resistance
 *   Vol ratio shown as "×1.8" next to badge
 *   RS+  → Stock 3m RS outperforming SPY (rs_vs_spy > 0)
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
                <th style={{ textAlign: 'left' }}>Signal</th>
              </tr>
            </thead>
            <tbody>
              {setups.map((s) => {
                const isSelected  = selectedTicker === s.ticker
                const isVolSurge  = s.is_vol_surge === true
                const isBrk       = s.is_breakout === true
                const isRsPlus    = typeof s.rs_vs_spy === 'number' && s.rs_vs_spy > 0

                // Row background: green tint for volume-surge rows
                const rowStyle = isVolSurge
                  ? { background: 'rgba(0, 200, 122, 0.06)', borderLeft: '2px solid rgba(0,200,122,0.45)' }
                  : isSelected
                  ? {}
                  : {}

                return (
                  <tr
                    key={`${s.ticker}-${s.setup_type}`}
                    className={isSelected ? 'selected' : ''}
                    style={rowStyle}
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
                    <td className="text-t-muted">{s.rr?.toFixed(1) ?? '2.0'}</td>

                    {/* Signal column */}
                    <td style={{ textAlign: 'left' }}>
                      {s.setup_type === 'VCP' ? (
                        <div className="flex items-center gap-1 flex-wrap">
                          {/* BRK / DRY badge */}
                          <span
                            className="badge"
                            style={isBrk
                              ? { background: 'rgba(0,200,122,0.18)', color: 'var(--go)', border: '1px solid rgba(0,200,122,0.4)', fontWeight: 700 }
                              : { background: 'rgba(245,166,35,0.12)', color: 'var(--accent)', border: '1px solid rgba(245,166,35,0.3)' }
                            }
                          >
                            {isBrk ? 'BRK' : 'DRY'}
                          </span>

                          {/* Volume ratio — shown for all VCP */}
                          {s.volume_ratio != null && (
                            <span
                              className="font-mono text-[8px] tabular-nums"
                              style={{ color: isVolSurge ? 'var(--go)' : 'var(--muted)' }}
                            >
                              ×{s.volume_ratio.toFixed(1)}
                            </span>
                          )}

                          {/* RS+ badge — only when outperforming SPY */}
                          {isRsPlus && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(0,200,255,0.10)', color: '#00C8FF', border: '1px solid rgba(0,200,255,0.3)', fontSize: 8 }}
                            >
                              RS+
                            </span>
                          )}
                        </div>
                      ) : (
                        /* Pullback: show CCI value */
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
