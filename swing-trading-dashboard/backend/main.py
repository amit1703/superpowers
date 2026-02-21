"""
Swing Trading Dashboard — FastAPI Backend
==========================================
Endpoints
─────────
  POST /api/run-scan          Trigger full background scan (non-blocking)
  GET  /api/scan-status       Poll scan progress
  GET  /api/regime            Latest SPY regime from DB
  GET  /api/setups            All setups (VCP + Pullback)
  GET  /api/setups/vcp        VCP setups only
  GET  /api/setups/pullback   Pullback setups only
  GET  /api/sr-zones/{ticker} S/R zones for one ticker (from last scan)
  GET  /api/chart/{ticker}    OHLCV + EMA8/20 + SMA50 + CCI20 (fresh fetch)
  GET  /api/health            Health-check

Architecture
────────────
  • yfinance calls run in a ThreadPoolExecutor (blocking I/O).
  • asyncio.Semaphore(5) caps concurrent yfinance requests.
  • Heavy maths (KDE, curve_fit) also run in executor threads.
  • All scan results are persisted to SQLite via aiosqlite.
  • Frontend reads only from the DB — no on-the-fly computation.

Run
───
  cd backend
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from indicators import ema as _ema, sma as _sma, cci as _cci
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    complete_scan_run,
    get_latest_regime,
    get_latest_scan_timestamp,
    get_latest_setups,
    get_sr_zones_for_ticker_from_db,
    init_db,
    save_regime,
    save_scan_run,
    save_setup,
    batch_save_setups,
    save_sr_zones,
    add_trade,
    get_trades,
    close_trade,
)
from engines.engine0 import check_market_regime
from engines.engine1 import calculate_sr_zones
from engines.engine2 import scan_vcp, detect_trendline, scan_near_breakout
from engines.engine3 import scan_pullback, scan_relaxed_pullback
from engines.engine4 import calculate_rs_line, detect_rs_blue_dot, get_rs_stats
from tickers import SCAN_UNIVERSE

# ────────────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────────────

DB_PATH = "trading.db"
CONCURRENCY_LIMIT = 25         # max simultaneous yfinance fetches (optimized from 10)
DATA_FETCH_PERIOD = "1y"       # lookback for each ticker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("swing")

# ────────────────────────────────────────────────────────────────────────────
# Sector mapping
# ────────────────────────────────────────────────────────────────────────────

SECTORS_FILE = "sectors.json"
SECTORS = {}

try:
    with open(SECTORS_FILE, 'r') as f:
        SECTORS = json.load(f)
    log.info("Loaded %d sectors from %s", len(SECTORS), SECTORS_FILE)
except Exception as e:
    log.warning("Could not load sectors.json: %s", e)

# ────────────────────────────────────────────────────────────────────────────
# Shared state (single-process; safe with asyncio event loop)
# ────────────────────────────────────────────────────────────────────────────

_scan_state: Dict = {
    "in_progress": False,
    "progress": 0,
    "total": 0,
    "started_at": None,
    "last_completed": None,
    "last_error": None,
}
_semaphore: Optional[asyncio.Semaphore] = None


# ────────────────────────────────────────────────────────────────────────────
# App lifecycle
# ────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _semaphore
    _semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    await init_db(DB_PATH)
    log.info("SQLite DB initialised at %s", DB_PATH)
    yield


app = FastAPI(
    title="Swing Trading Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────────────────────────────────────
# Data helpers
# ────────────────────────────────────────────────────────────────────────────

async def _fetch(ticker: str) -> Optional[pd.DataFrame]:
    """Download daily OHLCV for one ticker, rate-limited by the semaphore."""
    async with _semaphore:
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    ticker,
                    period=DATA_FETCH_PERIOD,
                    interval="1d",
                    auto_adjust=False,
                    prepost=False,
                    progress=False,
                    threads=False,
                ),
            )
        except Exception as exc:
            log.warning("Fetch failed %s: %s", ticker, exc)
            return None

    if df is None or df.empty:
        return None

    # Flatten MultiIndex (newer yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


# ────────────────────────────────────────────────────────────────────────────
# Background scan worker
# ────────────────────────────────────────────────────────────────────────────

async def _run_scan(scan_ts: str, tickers: List[str]) -> None:
    """
    Full scan pipeline:
      Engine 0 → (if bullish) Engine 1 → Engine 2 + Engine 3
    Results written to SQLite; frontend reads from DB.
    """
    global _scan_state
    scan_start_time = time.time()

    log.info("▶ Scan started  ts=%s  tickers=%d", scan_ts, len(tickers))
    _scan_state.update(
        in_progress=True,
        progress=0,
        total=len(tickers),
        started_at=scan_ts,
        last_error=None,
    )

    try:
        await save_scan_run(DB_PATH, scan_ts)

        # ── Engine 0: Market regime ───────────────────────────────────────
        loop = asyncio.get_event_loop()
        regime_start = time.time()
        regime = await loop.run_in_executor(None, check_market_regime)
        regime_time = time.time() - regime_start
        await save_regime(DB_PATH, scan_ts, regime)
        log.info(
            "Engine 0: %s  (SPY=%.2f  EMA20=%.2f)  [%.1fs]",
            regime["regime"],
            regime["spy_close"],
            regime["spy_20ema"],
            regime_time,
        )

        if not regime["is_bullish"]:
            log.info("Market is BEARISH — RS calculations + Engines 2 & 3 disabled (0s saved)")
            await complete_scan_run(DB_PATH, scan_ts, 0)
            _scan_state["last_completed"] = scan_ts
            return

        # ── SPY data (consolidated single fetch for 3m return + RS Line) ──
        # Only fetched when market is bullish; conditional RS calculation optimizes cycles
        spy_3m_return = 0.0
        spy_df_full = None
        spy_fetch_start = time.time()
        try:
            spy_df_full = await _fetch("SPY")
            if spy_df_full is not None and len(spy_df_full) >= 252:
                log.info("SPY data fetched: %d days for RS Line", len(spy_df_full))
                # Extract 3-month return from the consolidated fetch
                if len(spy_df_full) >= 64:
                    adj_col = "Adj Close" if "Adj Close" in spy_df_full.columns else "Close"
                    spy_close = spy_df_full[adj_col]
                    spy_3m_return = float(
                        spy_close.iloc[-1] / spy_close.iloc[-64] - 1
                    )
                    log.info("SPY 3-month return: %.2f%%", spy_3m_return * 100)
        except Exception as exc:
            log.warning("Could not fetch SPY data for RS/3m return: %s", exc)

        spy_fetch_time = time.time() - spy_fetch_start
        log.info("SPY fetch completed  [%.1fs]", spy_fetch_time)

        # ── Per-ticker processing ─────────────────────────────────────────
        # Collect setups instead of saving individually for batch optimization
        collected_setups: List[Dict] = []
        vcp_count = 0
        pb_count = 0
        process_start_time = time.time()

        async def _process(ticker: str, idx: int) -> None:
            nonlocal vcp_count, pb_count

            try:
                # ── Data Integrity Check ────────────────────────────────────
                # Skip tickers with empty/delisted data immediately
                df = await _fetch(ticker)
                if df is None or len(df) < 60:
                    log.debug("Skipped %s: insufficient data", ticker)
                    return

                # Check for empty Close column or all-NaN values
                close_col = "Adj Close" if "Adj Close" in df.columns else "Close"
                if close_col not in df.columns or df[close_col].isna().all():
                    log.debug("Skipped %s: no valid price data", ticker)
                    return

                # ── Parallelize RS + S/R zone calculations (independent operations) ──
                rs_line = None
                rs_ratio = 0.0
                rs_52w_high = 0.0
                rs_blue_dot = False
                zones: List[Dict] = []

                # Run RS and S/R zone calculations in parallel
                rs_task = None
                if spy_df_full is not None:
                    rs_task = loop.run_in_executor(None, calculate_rs_line, df, spy_df_full)

                sr_task = loop.run_in_executor(None, calculate_sr_zones, ticker, df)

                # Await both in parallel
                if rs_task:
                    try:
                        rs_line, zones = await asyncio.gather(rs_task, sr_task)
                    except Exception as exc:
                        log.warning("Parallel RS/SR calculation failed for %s: %s", ticker, exc)
                        rs_line = None
                        zones = await sr_task  # Fall back to SR-only
                else:
                    zones = await sr_task

                # Process RS results if available
                if rs_line and len(rs_line) >= 252:
                    try:
                        # Use .item() to safely convert numpy scalars to Python floats
                        rs_today = rs_line[-1]
                        rs_ratio = float(rs_today.item() if hasattr(rs_today, 'item') else rs_today)

                        rs_max = max(rs_line)
                        rs_52w_high = float(rs_max.item() if hasattr(rs_max, 'item') else rs_max)

                        rs_blue_dot = await loop.run_in_executor(
                            None, detect_rs_blue_dot, rs_line
                        )
                    except Exception as rs_exc:
                        log.warning("RS processing failed for %s: %s", ticker, rs_exc)
                        rs_ratio = 0.0
                        rs_52w_high = 0.0
                        rs_blue_dot = False
                if zones:
                    await save_sr_zones(DB_PATH, scan_ts, ticker, zones)

                # Engine 2: VCP breakout (with RS parameters for Path E)
                vcp = await loop.run_in_executor(
                    None, scan_vcp, ticker, df, zones, spy_3m_return,
                    rs_ratio, rs_52w_high, rs_blue_dot
                )
                if vcp:
                    # Sanitize VCP output: ensure all numeric fields are proper floats
                    try:
                        vcp["entry"] = float(vcp.get("entry", 0.0))
                        vcp["stop_loss"] = float(vcp.get("stop_loss", 0.0))
                        vcp["take_profit"] = float(vcp.get("take_profit", 0.0))
                        vcp["rr"] = float(vcp.get("rr", 2.0))
                    except (ValueError, TypeError) as conv_err:
                        log.warning("VCP conversion failed for %s: %s", ticker, conv_err)
                        return

                    # Add sector to setup and collect for batch save
                    vcp["sector"] = SECTORS.get(ticker, "Unknown")
                    collected_setups.append(vcp)
                    vcp_count += 1

                    setup_type = "RS LEAD" if vcp.get("is_rs_lead") else "VCP"
                    log.info("  %s      %-6s  entry=%.2f", setup_type, ticker, vcp["entry"])

                else:
                    # Only check near-breakout if not already a full setup
                    # Wrap entire near-breakout logic in try-except for robustness
                    try:
                        tl = await loop.run_in_executor(None, detect_trendline, ticker, df)
                        near = await loop.run_in_executor(
                            None, scan_near_breakout, ticker, df, zones, tl
                        )
                        if near:
                            # Sanitize near-breakout output: ensure numeric fields are proper floats
                            try:
                                near["entry"] = float(near.get("entry", 0.0))
                                near["distance_pct"] = float(near.get("distance_pct", 0.0))
                            except (ValueError, TypeError) as conv_err:
                                log.warning("Near-breakout conversion failed for %s: %s", ticker, conv_err)
                                return

                            near["sector"] = SECTORS.get(ticker, "Unknown")
                            near["rs_blue_dot"] = rs_blue_dot
                            collected_setups.append(near)
                            log.info("  NEAR     %-6s  dist=%.1f%%", ticker, near["distance_pct"])
                    except Exception as near_exc:
                        log.warning("Near-breakout check failed for %s: %s", ticker, near_exc)
                        # Continue to pullback checks even if near-breakout fails

                # Engine 3: Tactical pullback (strict, then relaxed)
                pb = await loop.run_in_executor(None, scan_pullback, ticker, df, zones)
                if pb:
                    # Sanitize pullback output
                    try:
                        pb["entry"] = float(pb.get("entry", 0.0))
                        pb["stop_loss"] = float(pb.get("stop_loss", 0.0))
                        pb["take_profit"] = float(pb.get("take_profit", 0.0))
                        pb["rr"] = float(pb.get("rr", 2.0))
                    except (ValueError, TypeError) as conv_err:
                        log.warning("Pullback conversion failed for %s: %s", ticker, conv_err)
                        return

                    pb["sector"] = SECTORS.get(ticker, "Unknown")
                    collected_setups.append(pb)
                    pb_count += 1
                    log.info("  PULLBACK %-6s  entry=%.2f", ticker, pb["entry"])
                else:
                    # Only check relaxed if no strict pullback found
                    try:
                        pb_relaxed = await loop.run_in_executor(
                            None, scan_relaxed_pullback, ticker, df, zones
                        )
                        if pb_relaxed:
                            # Sanitize relaxed pullback output
                            try:
                                pb_relaxed["entry"] = float(pb_relaxed.get("entry", 0.0))
                                pb_relaxed["stop_loss"] = float(pb_relaxed.get("stop_loss", 0.0))
                                pb_relaxed["take_profit"] = float(pb_relaxed.get("take_profit", 0.0))
                                pb_relaxed["rr"] = float(pb_relaxed.get("rr", 2.0))
                            except (ValueError, TypeError) as conv_err:
                                log.warning("Relaxed pullback conversion failed for %s: %s", ticker, conv_err)
                                return

                            pb_relaxed["sector"] = SECTORS.get(ticker, "Unknown")
                            collected_setups.append(pb_relaxed)
                            pb_count += 1
                            log.info("  PULLBACK %-6s  entry=%.2f (relaxed)", ticker, pb_relaxed["entry"])
                    except Exception as pb_rel_exc:
                        log.warning("Relaxed pullback check failed for %s: %s", ticker, pb_rel_exc)

            except Exception as exc:
                log.error("Error processing %s: %s", ticker, exc)
            finally:
                _scan_state["progress"] = idx + 1

        # Gather all ticker tasks; semaphore handles concurrency internally
        await asyncio.gather(*[_process(t, i) for i, t in enumerate(tickers)])

        process_time = time.time() - process_start_time
        log.info(
            "Per-ticker processing completed  [%.1fs]  vcp=%d  pb=%d  total_setups=%d",
            process_time,
            vcp_count,
            pb_count,
            len(collected_setups),
        )

        # ── Batch Save All Setups (5-10x faster than individual saves) ──────
        if collected_setups:
            db_save_start = time.time()
            await batch_save_setups(DB_PATH, scan_ts, collected_setups)
            db_save_time = time.time() - db_save_start
            log.info("Batch saved %d setups to database  [%.1fs]", len(collected_setups), db_save_time)

        # ── Sector Summary with Bold Highlighting ───────────────────────────
        # Sectors with 3+ setups are highlighted in bold for institutional rotation
        try:
            all_setups = await get_latest_setups(DB_PATH, scan_ts)
            sector_counts = {}

            for setup in all_setups:
                sector = setup.get("sector", "Unknown")
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

            # Sort by count descending
            sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)

            # Log with visual separator and bold for 3+ setups
            log.info("═════════════════════════════════════════════════════════")
            log.info("SECTOR SUMMARY — INSTITUTIONAL ROTATION ALERT")
            log.info("═════════════════════════════════════════════════════════")

            for sector, count in sorted_sectors:
                if count >= 3:
                    # Bold formatting with emoji for high-activity sectors
                    log.info("🔥 **%s (%d setups)**", sector, count)
                else:
                    log.info("   %s (%d setup%s)", sector, count, "s" if count != 1 else "")

            log.info("═════════════════════════════════════════════════════════")
        except Exception as exc:
            log.warning("Sector summary failed: %s", exc)

        await complete_scan_run(DB_PATH, scan_ts, len(tickers))
        _scan_state["last_completed"] = scan_ts

        total_scan_time = time.time() - scan_start_time
        log.info(
            "✔ Scan complete  VCP=%d  Pullbacks=%d  Total=%.1fs  (Regime=%.1fs, SPY=%.1fs, Process=%.1fs)",
            vcp_count,
            pb_count,
            total_scan_time,
            regime_time,
            spy_fetch_time,
            process_time,
        )

    except Exception as exc:
        log.error("Scan worker crashed: %s", exc)
        _scan_state["last_error"] = str(exc)
    finally:
        _scan_state["in_progress"] = False


# ────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/run-scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """
    Trigger a full market scan.  Returns immediately; scan runs in background.
    Poll /api/scan-status to track progress.
    """
    if _scan_state["in_progress"]:
        return {
            "status": "already_running",
            "progress": _scan_state["progress"],
            "total": _scan_state["total"],
        }

    scan_ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    background_tasks.add_task(_run_scan, scan_ts, SCAN_UNIVERSE)

    return {
        "status": "started",
        "scan_timestamp": scan_ts,
        "tickers": len(SCAN_UNIVERSE),
        "message": f"Scanning {len(SCAN_UNIVERSE)} tickers in background",
    }


@app.get("/api/scan-status")
async def scan_status():
    """Current scan progress (poll this after POST /api/run-scan)."""
    total = max(_scan_state["total"], 1)
    return {
        "in_progress": _scan_state["in_progress"],
        "progress": _scan_state["progress"],
        "total": _scan_state["total"],
        "progress_pct": round(_scan_state["progress"] / total * 100, 1),
        "started_at": _scan_state["started_at"],
        "last_completed": _scan_state["last_completed"],
        "last_error": _scan_state["last_error"],
    }


@app.get("/api/regime")
async def get_regime():
    """Latest market regime from the last completed scan."""
    regime = await get_latest_regime(DB_PATH)
    if regime is None:
        return {
            "regime": "NO_DATA",
            "is_bullish": False,
            "spy_close": 0.0,
            "spy_20ema": 0.0,
            "scan_timestamp": None,
        }
    return regime


@app.get("/api/setups")
async def get_all_setups():
    """All VCP + Pullback setups from the latest scan."""
    setups = await get_latest_setups(DB_PATH)
    return {"setups": setups, "count": len(setups)}


@app.get("/api/setups/vcp")
async def get_vcp_setups():
    """VCP breakout setups from the latest scan."""
    setups = await get_latest_setups(DB_PATH, setup_type="VCP")
    return {"setups": setups, "count": len(setups)}


@app.get("/api/setups/pullback")
async def get_pullback_setups():
    """Tactical pullback setups from the latest scan."""
    setups = await get_latest_setups(DB_PATH, setup_type="PULLBACK")
    return {"setups": setups, "count": len(setups)}


@app.get("/api/watchlist")
async def get_watchlist():
    """Near-breakout tickers from the latest scan (within 1.5% of KDE/TDL level)."""
    items = await get_latest_setups(DB_PATH, setup_type="WATCHLIST")
    # Sort by distance_pct ascending (closest first)
    items.sort(key=lambda x: x.get("distance_pct", 99))
    return {"items": items, "count": len(items)}


@app.get("/api/sr-zones/{ticker}")
async def get_sr_zones(ticker: str):
    """S/R zones for a ticker from the last scan (pre-computed, instant)."""
    zones = await get_sr_zones_for_ticker_from_db(DB_PATH, ticker.upper())
    return {"ticker": ticker.upper(), "zones": zones, "count": len(zones)}


@app.get("/api/chart/{ticker}")
async def get_chart_data(ticker: str):
    """
    Returns chart-ready payload for lightweight-charts:
      candles  – raw OHLCV (Open/High/Low/Close)
      ema8     – 8-period EMA of Adj Close
      ema20    – 20-period EMA of Adj Close
      sma50    – 50-period SMA of Adj Close
      cci      – 20-period CCI
      sr_zones – from last scan DB (pre-computed)

    The candle OHLC uses raw prices (standard charting convention).
    Indicators are calculated on Adj Close (adjusted for splits/dividends).
    """
    sym = ticker.upper()
    df = await _fetch(sym)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {sym}")
    if len(df) < 55:
        raise HTTPException(status_code=422, detail=f"Insufficient history for {sym}")

    adj = "Adj Close" if "Adj Close" in df.columns else "Close"
    close_adj = df[adj]
    high = df["High"]
    low = df["Low"]

    # Indicators on Adj Close
    ema8 = _ema(close_adj, 8)
    ema20 = _ema(close_adj, 20)
    sma50 = _sma(close_adj, 50)
    cci20 = _cci(high, low, close_adj, 20)

    def _series(idx, vals, dec=2):
        out = []
        for ts, v in zip(idx, vals):
            if pd.notna(v):
                out.append({"time": ts.strftime("%Y-%m-%d"), "value": round(float(v), dec)})
        return out

    # Raw OHLCV candles
    candles = []
    for ts, row in df.iterrows():
        o = row.get("Open", np.nan)
        h = row.get("High", np.nan)
        l = row.get("Low", np.nan)
        c = row.get("Close", np.nan)   # raw close for candle display
        v = row.get("Volume", 0)
        if all(pd.notna(x) for x in [o, h, l, c]):
            candles.append(
                {
                    "time": ts.strftime("%Y-%m-%d"),
                    "open": round(float(o), 2),
                    "high": round(float(h), 2),
                    "low": round(float(l), 2),
                    "close": round(float(c), 2),
                    "volume": int(v) if pd.notna(v) else 0,
                }
            )

    # S/R zones from latest scan (pre-computed)
    zones = await get_sr_zones_for_ticker_from_db(DB_PATH, sym)

    # Detect trendline (fresh computation for chart display)
    trendline = None
    try:
        loop = asyncio.get_event_loop()
        trendline = await loop.run_in_executor(None, detect_trendline, sym, df)
    except Exception as exc:
        log.warning("Trendline detection failed %s: %s", sym, exc)

    return {
        "ticker": sym,
        "candles": candles,
        "ema8": _series(df.index, ema8),
        "ema20": _series(df.index, ema20),
        "sma50": _series(df.index, sma50),
        "cci": _series(df.index, cci20, dec=1),
        "sr_zones": zones,
        "trendline": trendline,
    }


# ────────────────────────────────────────────────────────────────────────────
# Trade endpoints
# ────────────────────────────────────────────────────────────────────────────

class TradeIn(BaseModel):
    ticker:      str
    entry_price: float
    quantity:    float
    stop_loss:   float
    target:      float
    entry_date:  str
    notes:       str = ""


async def _enrich_trade(trade: Dict) -> Dict:
    """
    Fetch fresh market data for a trade and add:
      current_price, pl_dollar, pl_pct,
      ema8, ema20, health ('HOLD' | 'CAUTION' | 'EXIT')
    Falls back gracefully if the fetch fails.
    """
    result = {**trade, "current_price": None, "pl_dollar": None,
              "pl_pct": None, "ema8": None, "ema20": None, "health": "UNKNOWN"}
    try:
        df = await _fetch(trade["ticker"])
        if df is None or len(df) < 25:
            return result

        adj = "Adj Close" if "Adj Close" in df.columns else "Close"
        close = df[adj]
        high  = df["High"]
        low   = df["Low"]

        ema8_s  = _ema(close, 8)
        ema20_s = _ema(close, 20)
        cci20_s = _cci(high, low, close, 20)

        lc   = float(close.iloc[-1])
        l8   = float(ema8_s.iloc[-1])
        l20  = float(ema20_s.iloc[-1])

        # CCI hook below 100: was above 100, now crossed below (bearish)
        cci_hook_below = False
        if len(cci20_s.dropna()) >= 2:
            cci_prev = float(cci20_s.dropna().iloc[-2])
            cci_last = float(cci20_s.dropna().iloc[-1])
            cci_hook_below = cci_prev > 100 and cci_last < 100

        # Health signal
        if lc < l20 or cci_hook_below:
            health = "EXIT"
        elif lc < l8:          # above 20 EMA but below 8 EMA
            health = "CAUTION"
        else:
            health = "HOLD"

        ep   = trade["entry_price"]
        qty  = trade["quantity"]
        pl_d = round((lc - ep) * qty, 2)
        pl_p = round((lc / ep - 1) * 100, 2) if ep > 0 else 0.0

        # Trailing stop: rises with EMA20 when in profit; stays at original SL otherwise
        trailing_stop = max(float(trade["stop_loss"]), l20) if lc > trade["entry_price"] else float(trade["stop_loss"])
        is_risk_free = trailing_stop > trade["entry_price"]

        result.update({
            "current_price": round(lc, 2),
            "pl_dollar":     pl_d,
            "pl_pct":        pl_p,
            "ema8":          round(l8, 2),
            "ema20":         round(l20, 2),
            "health":        health,
            "trailing_stop": round(trailing_stop, 2),
            "is_risk_free":  is_risk_free,
        })
    except Exception as exc:
        log.warning("Trade enrichment failed %s: %s", trade["ticker"], exc)
    return result


@app.post("/api/trades", status_code=201)
async def create_trade(body: TradeIn):
    """Add a new active trade to the portfolio."""
    trade_id = await add_trade(DB_PATH, body.model_dump())
    return {"id": trade_id, "status": "active", **body.model_dump()}


@app.get("/api/trades")
async def list_trades():
    """
    Return all active trades enriched with live price, P/L, and health signal.
    Fetches are run concurrently (bounded by the shared semaphore).
    """
    trades = await get_trades(DB_PATH, status="active")
    if not trades:
        return {"trades": [], "count": 0}

    enriched = await asyncio.gather(*[_enrich_trade(t) for t in trades])
    return {"trades": list(enriched), "count": len(enriched)}


@app.delete("/api/trades/{trade_id}", status_code=200)
async def delete_trade(trade_id: int):
    """Close (soft-delete) an active trade by id."""
    ok = await close_trade(DB_PATH, trade_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found or already closed")
    return {"id": trade_id, "status": "closed"}
