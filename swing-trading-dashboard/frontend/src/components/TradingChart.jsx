/**
 * TradingChart — lightweight-charts v4 component
 *
 * Layout  (top → bottom):
 *   ┌──────────────────────────────────┐
 *   │  Chart legend (HTML overlay)     │
 *   │  Candlestick + EMA8/EMA20/SMA50  │  ← mainContainer
 *   │  S/R bands (SRBandPrimitive)     │
 *   ├──────────────────────────────────┤
 *   │  CCI (20) line chart             │  ← cciContainer
 *   │  ─100 / 0 / +100 ref lines       │
 *   └──────────────────────────────────┘
 *
 * Charts are destroyed + re-created when chartData changes (ticker click).
 * Time ranges are kept in sync via subscribeVisibleTimeRangeChange.
 */

import { useEffect, useRef, useState } from 'react'
import { createChart, CrosshairMode, LineStyle, PriceScaleMode } from 'lightweight-charts'
import { SRBandPrimitive } from '../sr-band-primitive.js'

// ── Design tokens (match index.css variables) ──────────────────────────────
const COLORS = {
  bg:           '#000000',
  surface:      '#080c12',
  border:       '#1a2535',
  text:         '#c8cdd6',
  muted:        '#4a5a72',
  accent:       '#F5A623',
  go:           '#00c87a',
  halt:         '#ff2d55',
  ema8:         '#00C8FF',
  ema20:        '#F5A623',
  sma50:        '#FF6EC7',
  cci:          '#9B6EFF',
  cciOb:        'rgba(255, 45, 85, 0.12)',
  cciOs:        'rgba(0, 200, 122, 0.10)',
  trendline:    '#FFFFFF',
}

const SHARED_CHART_OPTS = {
  layout: {
    background: { color: COLORS.bg },
    textColor: COLORS.muted,
    fontFamily: '"IBM Plex Mono", monospace',
    fontSize: 10,
  },
  grid: {
    vertLines: { color: '#0d1520', style: LineStyle.Solid },
    horzLines: { color: '#0d1520', style: LineStyle.Solid },
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: { color: 'rgba(245, 166, 35, 0.4)', labelBackgroundColor: '#1a2535' },
    horzLine: { color: 'rgba(245, 166, 35, 0.25)', labelBackgroundColor: '#1a2535' },
  },
  rightPriceScale: {
    borderColor: COLORS.border,
    textColor: COLORS.muted,
    scaleMargins: { top: 0.08, bottom: 0.05 },
  },
  timeScale: {
    borderColor: COLORS.border,
    timeVisible: true,
    secondsVisible: false,
  },
  handleScale: true,
  handleScroll: true,
}

// ─────────────────────────────────────────────────────────────────────────────

export default function TradingChart({ ticker, chartData, loading }) {
  const mainRef = useRef(null)
  const cciRef  = useRef(null)
  const wrapRef = useRef(null)

  // Legend state — updated on crosshair move
  const [legend, setLegend] = useState(null)

  useEffect(() => {
    if (!chartData || !mainRef.current || !cciRef.current) return

    const mainEl = mainRef.current
    const cciEl  = cciRef.current

    // ── Create charts ──────────────────────────────────────────────────────
    const mainChart = createChart(mainEl, {
      ...SHARED_CHART_OPTS,
      height: mainEl.clientHeight || 440,
      width:  mainEl.clientWidth  || 800,
      timeScale: {
        ...SHARED_CHART_OPTS.timeScale,
        visible: true,
      },
    })

    const cciChart = createChart(cciEl, {
      ...SHARED_CHART_OPTS,
      height: cciEl.clientHeight || 160,
      width:  cciEl.clientWidth  || 800,
      rightPriceScale: {
        ...SHARED_CHART_OPTS.rightPriceScale,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      layout: {
        ...SHARED_CHART_OPTS.layout,
        fontSize: 9,
      },
    })

    // ── Candlestick series ─────────────────────────────────────────────────
    const candleSeries = mainChart.addCandlestickSeries({
      upColor:          COLORS.go,
      downColor:        COLORS.halt,
      borderUpColor:    COLORS.go,
      borderDownColor:  COLORS.halt,
      wickUpColor:      'rgba(0, 200, 122, 0.6)',
      wickDownColor:    'rgba(255, 45, 85, 0.6)',
      priceLineVisible: true,
      priceLineColor:   COLORS.accent,
      priceLineStyle:   LineStyle.Dashed,
      priceLineWidth:   1,
      lastValueVisible: true,
    })
    if (chartData.candles?.length) candleSeries.setData(chartData.candles)

    // ── S/R Band primitives (attached to candle series) ────────────────────
    if (chartData.sr_zones?.length) {
      chartData.sr_zones.forEach((zone) => {
        try {
          candleSeries.attachPrimitive(new SRBandPrimitive(zone))
        } catch (e) {
          // Fallback: draw two price lines if primitive API unavailable
          const c = zone.type === 'RESISTANCE' ? COLORS.halt : COLORS.go
          candleSeries.createPriceLine({ price: zone.upper, color: c, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: '' })
          candleSeries.createPriceLine({ price: zone.lower, color: c, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: `${zone.type[0]} ${zone.level}` })
        }
      })
    }

    // ── EMA 8 (electric blue, thin solid) ─────────────────────────────────
    const ema8Series = mainChart.addLineSeries({
      color:            COLORS.ema8,
      lineWidth:        1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    if (chartData.ema8?.length) ema8Series.setData(chartData.ema8)

    // ── EMA 20 (amber, thin solid) ─────────────────────────────────────────
    const ema20Series = mainChart.addLineSeries({
      color:            COLORS.ema20,
      lineWidth:        1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    if (chartData.ema20?.length) ema20Series.setData(chartData.ema20)

    // ── SMA 50 (pink, dashed) ──────────────────────────────────────────────
    const sma50Series = mainChart.addLineSeries({
      color:            COLORS.sma50,
      lineWidth:        1.5,
      lineStyle:        LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    if (chartData.sma50?.length) sma50Series.setData(chartData.sma50)

    // ── Trendline (bright white diagonal line) ────────────────────────────
    let trendlineSeries = null
    if (chartData.trendline?.series?.length) {
      trendlineSeries = mainChart.addLineSeries({
        color:            COLORS.trendline,
        lineWidth:        1.5,
        lineStyle:        LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      trendlineSeries.setData(chartData.trendline.series)
    }

    // ── CCI line series ────────────────────────────────────────────────────
    const cciSeries = cciChart.addLineSeries({
      color:            COLORS.cci,
      lineWidth:        1,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 3,
    })
    if (chartData.cci?.length) cciSeries.setData(chartData.cci)

    // CCI reference lines
    const cciRefLines = [
      { price: 100,  title: '+100', color: 'rgba(255, 45, 85, 0.45)',   lineStyle: LineStyle.Dashed },
      { price: -100, title: '-100', color: 'rgba(0, 200, 122, 0.45)',  lineStyle: LineStyle.Dashed },
      { price: 0,    title: '  0',  color: 'rgba(200, 205, 214, 0.15)', lineStyle: LineStyle.Solid  },
    ]
    cciRefLines.forEach((rl) => {
      cciSeries.createPriceLine({
        price:              rl.price,
        color:              rl.color,
        lineWidth:          1,
        lineStyle:          rl.lineStyle,
        axisLabelVisible:   true,
        title:              rl.title,
      })
    })

    // ── Fit content ────────────────────────────────────────────────────────
    mainChart.timeScale().fitContent()

    // ── Sync time ranges ───────────────────────────────────────────────────
    let mainSyncing = false
    let cciSyncing  = false

    mainChart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (cciSyncing || !range) return
      mainSyncing = true
      cciChart.timeScale().setVisibleRange(range)
      mainSyncing = false
    })

    cciChart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (mainSyncing || !range) return
      cciSyncing = true
      mainChart.timeScale().setVisibleRange(range)
      cciSyncing = false
    })

    // ── Crosshair legend ───────────────────────────────────────────────────
    mainChart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData) {
        setLegend(null)
        return
      }
      const candle = param.seriesData.get(candleSeries)
      const e8     = param.seriesData.get(ema8Series)
      const e20    = param.seriesData.get(ema20Series)
      const s50    = param.seriesData.get(sma50Series)
      const tl     = trendlineSeries ? param.seriesData.get(trendlineSeries) : null

      setLegend({
        time:      param.time,
        open:      candle?.open,
        high:      candle?.high,
        low:       candle?.low,
        close:     candle?.close,
        ema8:      e8?.value,
        ema20:     e20?.value,
        sma50:     s50?.value,
        trendline: tl?.value,
      })
    })

    // ── Resize observer ────────────────────────────────────────────────────
    const wrap = wrapRef.current
    const observer = new ResizeObserver(() => {
      if (!wrap) return
      const w = wrap.clientWidth
      mainChart.applyOptions({ width: w })
      cciChart.applyOptions({ width: w })
    })
    if (wrap) observer.observe(wrap)

    // ── Cleanup ────────────────────────────────────────────────────────────
    return () => {
      observer.disconnect()
      try { mainChart.remove() } catch (_) {}
      try { cciChart.remove()  } catch (_) {}
      setLegend(null)
    }
  }, [chartData]) // re-create charts whenever data changes

  // ── Empty states ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="terminal-placeholder">
        <span className="text-t-accent text-[13px] tracking-widest font-600 uppercase terminal-cursor">
          LOADING {ticker}
        </span>
        <span className="text-[10px] text-t-muted tracking-widest">fetching market data…</span>
      </div>
    )
  }

  if (!chartData) {
    return (
      <div className="terminal-placeholder">
        <div className="flex flex-col items-center gap-3">
          {/* ASCII chart placeholder */}
          <pre className="text-t-border text-[10px] leading-tight select-none">
{`  ┌──────────────────────────┐
  │  no ticker selected      │
  │                          │
  │  click any row to load   │
  │  a chart                 │
  │                          │
  └──────────────────────────┘`}
          </pre>
          <span className="text-[10px] text-t-muted tracking-widest uppercase">
            Select a ticker from the tables
          </span>
        </div>
      </div>
    )
  }

  return (
    <div ref={wrapRef} className="flex flex-col h-full overflow-hidden">

      {/* Chart info bar */}
      <div className="flex items-center gap-4 px-3 py-1.5 border-b border-t-border flex-shrink-0"
           style={{ background: 'var(--surface)' }}>
        <span className="text-t-accent font-600 text-[13px] tracking-widest">{ticker}</span>
        <span className="text-t-muted text-[9px] uppercase tracking-widest">Daily</span>

        {/* Indicator legend labels */}
        <div className="flex items-center gap-4 ml-2">
          <LegendItem dot={COLORS.ema8}  label="EMA-8"  value={legend?.ema8}  />
          <LegendItem dot={COLORS.ema20} label="EMA-20" value={legend?.ema20} />
          <LegendItem dot={COLORS.sma50} label="SMA-50" value={legend?.sma50} dashed />
          {chartData.trendline?.series?.length > 0 && (
            <LegendItem dot={COLORS.trendline} label="TDL" value={legend?.trendline} />
          )}
        </div>

        {/* OHLC from crosshair */}
        {legend?.open != null && (
          <div className="flex items-center gap-3 ml-auto font-mono tabular-nums text-[10px]">
            <span className="text-t-muted">O<span className="ml-1 text-t-text">{pf(legend.open)}</span></span>
            <span className="text-t-muted">H<span className="ml-1 text-t-go">{pf(legend.high)}</span></span>
            <span className="text-t-muted">L<span className="ml-1 text-t-halt">{pf(legend.low)}</span></span>
            <span className="text-t-muted">C<span className={`ml-1 font-600 ${legend.close >= legend.open ? 'text-t-go' : 'text-t-halt'}`}>{pf(legend.close)}</span></span>
          </div>
        )}
      </div>

      {/* S/R zone legend */}
      {chartData.sr_zones?.length > 0 && (
        <div className="flex items-center gap-3 px-3 py-1 border-b border-t-border flex-shrink-0 overflow-x-auto"
             style={{ background: 'var(--bg)' }}>
          <span className="text-[9px] tracking-widest uppercase text-t-muted flex-shrink-0">S/R Zones:</span>
          {chartData.sr_zones.map((z, i) => (
            <span key={i}
              className="text-[9px] font-mono tabular-nums flex-shrink-0 flex items-center gap-1"
              style={{ color: z.type === 'RESISTANCE' ? COLORS.halt : COLORS.go }}>
              <span className="opacity-60">{z.type[0]}</span>{z.level.toFixed(2)}
            </span>
          ))}
        </div>
      )}

      {/* Main price chart */}
      <div
        ref={mainRef}
        className="flex-1 chart-container min-h-0"
        style={{ minHeight: 0 }}
      />

      {/* CCI sub-chart */}
      <div className="flex-shrink-0 border-t border-t-border" style={{ height: 160 }}>
        <div className="section-label" style={{ padding: '4px 10px' }}>
          <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: COLORS.cci }} />
          CCI (20)
          <span className="ml-auto text-[9px] text-t-muted">
            OB&nbsp;+100 &nbsp;/&nbsp; OS&nbsp;-100
          </span>
        </div>
        <div ref={cciRef} style={{ height: 'calc(100% - 24px)' }} />
      </div>

    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function LegendItem({ dot, label, value, dashed }) {
  return (
    <div className="flex items-center gap-1.5">
      {dashed ? (
        <svg width="14" height="6" className="flex-shrink-0">
          <line x1="0" y1="3" x2="14" y2="3" stroke={dot} strokeWidth="1.5" strokeDasharray="4 2" />
        </svg>
      ) : (
        <span className="inline-block w-2 h-0.5 rounded flex-shrink-0" style={{ background: dot }} />
      )}
      <span className="text-t-muted text-[9px] uppercase tracking-wide">{label}</span>
      {value != null && (
        <span className="font-mono text-[10px] tabular-nums" style={{ color: dot }}>
          {value.toFixed(2)}
        </span>
      )}
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────
const pf = (n) => n?.toFixed(2) ?? '—'
