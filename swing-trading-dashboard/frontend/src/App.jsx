/**
 * App.jsx — root layout and state orchestrator
 *
 * Layout (CSS Grid):
 *  ┌────────────────────────── Header (full-width, 62px) ──────────────────┐
 *  │ Left panel (380px)        │  Right panel (flex-1)                     │
 *  │  VCP SetupTable           │   TradingChart (candles + indicators +    │
 *  │  Pullback SetupTable      │   S/R bands + CCI sub-pane)               │
 *  └───────────────────────────┴───────────────────────────────────────────┘
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import {
  fetchRegime,
  fetchSetups,
  fetchChartData,
  triggerScan,
  fetchScanStatus,
} from './api.js'

import Header       from './components/Header.jsx'
import SetupTable   from './components/SetupTable.jsx'
import TradingChart from './components/TradingChart.jsx'

// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_SCAN_STATUS = {
  in_progress:    false,
  progress:       0,
  total:          0,
  progress_pct:   0,
  started_at:     null,
  last_completed: null,
  last_error:     null,
}

export default function App() {
  const [regime,         setRegime        ] = useState(null)
  const [vcpSetups,      setVcpSetups     ] = useState([])
  const [pullbackSetups, setPullbackSetups] = useState([])
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [chartData,      setChartData     ] = useState(null)
  const [loadingSetups,  setLoadingSetups ] = useState(false)
  const [loadingChart,   setLoadingChart  ] = useState(false)
  const [scanStatus,     setScanStatus    ] = useState(DEFAULT_SCAN_STATUS)

  const pollTimerRef = useRef(null)

  // ── Load regime + setups from DB ─────────────────────────────────────────
  const loadAllData = useCallback(async () => {
    setLoadingSetups(true)
    try {
      const [reg, vcp, pb] = await Promise.all([
        fetchRegime(),
        fetchSetups('vcp'),
        fetchSetups('pullback'),
      ])
      setRegime(reg)
      setVcpSetups(vcp.setups     ?? [])
      setPullbackSetups(pb.setups ?? [])
    } catch (err) {
      console.error('[App] loadAllData:', err)
    } finally {
      setLoadingSetups(false)
    }
  }, [])

  // ── Ticker click → load chart data ───────────────────────────────────────
  const handleTickerClick = useCallback(async (ticker) => {
    setSelectedTicker(ticker)
    setChartData(null)
    setLoadingChart(true)
    try {
      const data = await fetchChartData(ticker)
      setChartData(data)
    } catch (err) {
      console.error('[App] fetchChartData:', err)
      setChartData(null)
    } finally {
      setLoadingChart(false)
    }
  }, [selectedTicker])

  // ── Run scan ──────────────────────────────────────────────────────────────
  const handleRunScan = useCallback(async () => {
    try {
      await triggerScan()
      setScanStatus((s) => ({ ...s, in_progress: true, progress: 0 }))
    } catch (err) {
      console.error('[App] triggerScan:', err)
    }
  }, [])

  // ── Poll scan status while running ────────────────────────────────────────
  useEffect(() => {
    if (!scanStatus.in_progress) return

    pollTimerRef.current = setInterval(async () => {
      try {
        const status = await fetchScanStatus()
        setScanStatus(status)

        if (!status.in_progress) {
          clearInterval(pollTimerRef.current)
          // Reload all data once scan finishes
          loadAllData()
        }
      } catch (err) {
        console.warn('[App] poll error:', err)
      }
    }, 2000)

    return () => clearInterval(pollTimerRef.current)
  }, [scanStatus.in_progress, loadAllData])

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    // Load existing DB data immediately on mount
    loadAllData()

    // Auto-load ticker from URL param (?ticker=AAPL)
    const params = new URLSearchParams(window.location.search)
    const t = params.get('ticker')
    if (t) handleTickerClick(t.toUpperCase())

    // Also check if a scan is already running
    fetchScanStatus()
      .then((s) => setScanStatus(s))
      .catch(() => {})
  }, [loadAllData])

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="flex flex-col"
      style={{ height: '100vh', background: 'var(--bg)', overflow: 'hidden' }}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <Header
        regime={regime}
        scanStatus={scanStatus}
        onRunScan={handleRunScan}
        onSearchTicker={handleTickerClick}
      />

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* Left panel — setup tables */}
        <aside
          className="flex flex-col overflow-y-auto flex-shrink-0"
          style={{
            width: 400,
            borderRight: '1px solid var(--border)',
            background: 'var(--panel)',
          }}
        >
          {/* VCP */}
          <SetupTable
            title="VCP Breakouts"
            accentColor="blue"
            setups={vcpSetups}
            selectedTicker={selectedTicker}
            onSelectTicker={handleTickerClick}
            loading={loadingSetups}
          />

          {/* Pullback */}
          <SetupTable
            title="Tactical Pullbacks"
            accentColor="accent"
            setups={pullbackSetups}
            selectedTicker={selectedTicker}
            onSelectTicker={handleTickerClick}
            loading={loadingSetups}
          />

          {/* Footer — last scan info */}
          <div className="mt-auto px-3 py-3 border-t border-t-border">
            <ScanFooter
              vcpCount={vcpSetups.length}
              pbCount={pullbackSetups.length}
              scanTimestamp={scanStatus.last_completed}
            />
          </div>
        </aside>

        {/* Right panel — chart */}
        <main className="flex-1 min-w-0 overflow-hidden" style={{ background: 'var(--bg)' }}>
          <TradingChart
            ticker={selectedTicker}
            chartData={chartData}
            loading={loadingChart}
          />
        </main>

      </div>
    </div>
  )
}

// ── Scan footer ───────────────────────────────────────────────────────────

function ScanFooter({ vcpCount, pbCount, scanTimestamp }) {
  const fmtTs = (ts) => {
    if (!ts) return 'Never'
    try {
      const d = new Date(ts + 'Z')
      return d.toLocaleString('en-US', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false,
      })
    } catch { return ts }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-[9px] text-t-muted uppercase tracking-widest">
        <span>Last scan</span>
        <span className="text-t-text">{fmtTs(scanTimestamp)}</span>
      </div>
      <div className="flex gap-3 text-[9px] text-t-muted">
        <span><span className="text-t-blue font-600">{vcpCount}</span> VCP</span>
        <span><span className="text-t-accent font-600">{pbCount}</span> Pullback</span>
        <span className="ml-auto text-t-border">v1.0</span>
      </div>
    </div>
  )
}
