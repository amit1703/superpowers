# Stage 8: RS Line Analysis & Sector Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add RS Line institutional footprint detection (Path E: RS LEAD breakouts) and sector-based scanning alerts with UI refinements.

**Architecture:**
- New engine4.py calculates daily RS ratios (ticker/SPY) and detects 52-week highs ("Blue Dots")
- Path E in engine2.py triggers when stock has RS Blue Dot + price within 3% of resistance
- Static sectors.json maps all 100 tickers to sectors for alert aggregation
- main.py fetches SPY once, calculates RS for all tickers, runs Path E, logs bold sector alerts
- Frontend shows LEAD badge with blue dot indicator in SetupTable, star in Watchlist for RS Blue Dot tickers

**Tech Stack:** Python (pandas, numpy), React (SetupTable, WatchlistPanel), JSON (sectors mapping)

---

## Task 1: Create engine4.py with RS Line Calculations

**Files:**
- Create: `backend/engines/engine4.py`
- Modify: `backend/engines/__init__.py` (add export if needed)

**Step 1: Create engine4.py with RS Line functions**

Create file at `backend/engines/engine4.py`:

```python
"""
Engine 4: RS Line Analysis
==========================
Detects institutional accumulation through Relative Strength (RS) Line tracking.
RS Line = Ticker Close / SPY Close (daily ratio over 252 trading days).
Blue Dot = 52-week high in the RS Line.
"""

import os
import sys
from typing import Optional, List

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def calculate_rs_line(
    ticker_df: pd.DataFrame,
    spy_df: pd.DataFrame,
) -> Optional[List[float]]:
    """
    Calculate Relative Strength Line: ticker_close / spy_close for each day.

    Parameters
    ----------
    ticker_df : pd.DataFrame
        Ticker OHLCV data with 'Close' or 'Adj Close' column
    spy_df : pd.DataFrame
        SPY OHLCV data with 'Close' or 'Adj Close' column

    Returns
    -------
    List[float]
        RS ratios aligned with ticker_df dates, or None if calculation fails
    """
    try:
        if ticker_df is None or ticker_df.empty or spy_df is None or spy_df.empty:
            return None

        # Flatten MultiIndex if needed
        if isinstance(ticker_df.columns, pd.MultiIndex):
            ticker_df.columns = ticker_df.columns.get_level_values(0)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)

        # Use Adj Close if available, else Close
        ticker_close_col = "Adj Close" if "Adj Close" in ticker_df.columns else "Close"
        spy_close_col = "Adj Close" if "Adj Close" in spy_df.columns else "Close"

        ticker_close = ticker_df[ticker_close_col]
        spy_close = spy_df[spy_close_col]

        if ticker_close.empty or spy_close.empty:
            return None

        # Align dates: use intersection of both series
        common_dates = ticker_close.index.intersection(spy_close.index)
        if len(common_dates) < 252:
            return None  # Need at least 252 trading days

        ticker_aligned = ticker_close[common_dates]
        spy_aligned = spy_close[common_dates]

        # Calculate RS ratios
        rs_line = (ticker_aligned / spy_aligned).values.tolist()

        # Return only last 252 days
        return rs_line[-252:] if len(rs_line) >= 252 else None

    except Exception as exc:
        print(f"[calculate_rs_line] Error: {exc}")
        return None


def detect_rs_blue_dot(rs_line: List[float]) -> bool:
    """
    Detect if current RS ratio is at or near 52-week high.

    Blue Dot = RS_today >= max(RS_history over last 252 days)
    Signals institutional accumulation.

    Parameters
    ----------
    rs_line : List[float]
        RS ratios (last 252 days), e.g., [0.95, 0.96, 0.97, ...]

    Returns
    -------
    bool
        True if current ratio is at 52-week high, False otherwise
    """
    try:
        if rs_line is None or len(rs_line) < 252:
            return False

        rs_today = float(rs_line[-1])
        rs_52w_high = float(np.max(rs_line))

        # Blue Dot if within 0.5% of 52-week high (tolerance for rounding)
        return rs_today >= rs_52w_high * 0.995

    except Exception as exc:
        print(f"[detect_rs_blue_dot] Error: {exc}")
        return False


def get_rs_stats(rs_line: List[float]) -> dict:
    """
    Get current RS statistics for logging/debugging.

    Returns
    -------
    dict
        {'rs_today': float, 'rs_52w_high': float, 'rs_trend': str}
    """
    try:
        if rs_line is None or len(rs_line) < 2:
            return {"rs_today": None, "rs_52w_high": None, "rs_trend": "UNKNOWN"}

        rs_today = float(rs_line[-1])
        rs_prev = float(rs_line[-2])
        rs_52w_high = float(np.max(rs_line))

        # Simple trend: up if today > yesterday, down if lower
        if rs_today > rs_prev:
            trend = "UP"
        elif rs_today < rs_prev:
            trend = "DOWN"
        else:
            trend = "FLAT"

        return {
            "rs_today": round(rs_today, 4),
            "rs_52w_high": round(rs_52w_high, 4),
            "rs_trend": trend,
        }

    except Exception as exc:
        print(f"[get_rs_stats] Error: {exc}")
        return {"rs_today": None, "rs_52w_high": None, "rs_trend": "UNKNOWN"}
```

**Step 2: Verify syntax**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/backend
python -m py_compile engines/engine4.py
echo "✓ engine4.py syntax check passed"
```

Expected: `✓ engine4.py syntax check passed`

**Step 3: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/engines/engine4.py
git commit -m "feat: add engine4.py with RS Line calculations

- calculate_rs_line(): Compute ticker/SPY ratio over 252 days
- detect_rs_blue_dot(): Identify 52-week high in RS ratio
- get_rs_stats(): Helper for logging RS trend and stats
- Detects institutional accumulation signals"
```

---

## Task 2: Create sectors.json Static Mapping

**Files:**
- Create: `backend/sectors.json`

**Step 1: Create sectors.json with all 100 tickers**

Create file at `backend/sectors.json`:

```json
{
  "AAPL": "Technology",
  "MSFT": "Technology",
  "GOOGL": "Technology",
  "AMZN": "Consumer",
  "NVDA": "Technology",
  "META": "Technology",
  "TSLA": "Consumer",
  "BRK.B": "Financials",
  "JPM": "Financials",
  "JNJ": "Healthcare",
  "XOM": "Energy",
  "WMT": "Consumer",
  "PG": "Consumer",
  "KO": "Consumer",
  "NFLX": "Technology",
  "COST": "Consumer",
  "DIS": "Media",
  "MCD": "Consumer",
  "BAC": "Financials",
  "GS": "Financials",
  "MS": "Financials",
  "C": "Financials",
  "BLK": "Financials",
  "INTC": "Technology",
  "AMD": "Technology",
  "QCOM": "Technology",
  "ASML": "Technology",
  "AVGO": "Technology",
  "CRM": "Technology",
  "ADBE": "Technology",
  "ORCL": "Technology",
  "IBM": "Technology",
  "CSCO": "Technology",
  "MU": "Technology",
  "TSM": "Technology",
  "PYPL": "Financials",
  "SQ": "Financials",
  "SHOP": "Technology",
  "UBER": "Consumer",
  "LYFT": "Consumer",
  "AIRB": "Consumer",
  "RBLX": "Technology",
  "ROKU": "Media",
  "ZM": "Technology",
  "NOW": "Technology",
  "SNOW": "Technology",
  "CRWD": "Technology",
  "NET": "Technology",
  "ANET": "Technology",
  "S": "Technology",
  "DDOG": "Technology",
  "FTNT": "Technology",
  "OKTA": "Technology",
  "TWLO": "Technology",
  "BILI": "Media",
  "BIDU": "Technology",
  "JD": "Consumer",
  "BABA": "Consumer",
  "PDD": "Consumer",
  "TCEHY": "Technology",
  "NIO": "Consumer",
  "XPE": "Energy",
  "COP": "Energy",
  "MPC": "Energy",
  "PSX": "Energy",
  "VLO": "Energy",
  "CVX": "Energy",
  "SLB": "Energy",
  "HAL": "Energy",
  "MRO": "Energy",
  "OKE": "Energy",
  "GIS": "Consumer",
  "MO": "Consumer",
  "PM": "Consumer",
  "MRK": "Healthcare",
  "PFE": "Healthcare",
  "LLY": "Healthcare",
  "ABBV": "Healthcare",
  "TMO": "Healthcare",
  "BIIB": "Healthcare",
  "VRTX": "Healthcare",
  "REGN": "Healthcare",
  "SYK": "Healthcare",
  "ILMN": "Healthcare",
  "TDOC": "Healthcare",
  "VEEV": "Technology",
  "ROP": "Technology",
  "APD": "Industrials",
  "NSC": "Industrials",
  "UNP": "Industrials",
  "BA": "Industrials",
  "LMT": "Industrials",
  "RTX": "Industrials",
  "GE": "Industrials",
  "CAT": "Industrials",
  "DE": "Industrials"
}
```

**Step 2: Verify JSON syntax**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
node -e "const s = JSON.parse(require('fs').readFileSync('swing-trading-dashboard/backend/sectors.json')); console.log('✓ sectors.json valid, ' + Object.keys(s).length + ' tickers')"
```

Expected: `✓ sectors.json valid, 100 tickers`

**Step 3: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/sectors.json
git commit -m "feat: add sectors.json static mapping

- Maps all 100 tickers to sectors (Technology, Financials, etc.)
- Loaded at startup for efficient sector alerts
- Supports sector-based scanning summaries"
```

---

## Task 3: Add Path E to engine2.py

**Files:**
- Modify: `backend/engines/engine2.py:425-475` (add after Path D)

**Step 1: Add Path E code after Path D**

In `engine2.py`, after the closing of Path D (around line 425), add:

```python
        # ── PATH E — RS Strength Breakout ────────────────────────────────────
        # Institutional accumulation signal: RS Blue Dot + proximity to resistance
        # Less strict than VCP/DRY, focuses on early institutional moves

        if highest_res is not None and rs_blue_dot:
            upper = highest_res["upper"]
            pct_below_upper = (upper - lc) / upper if upper > 0 else 1.0

            # Check: within 3% below resistance + RS Blue Dot (no volume requirement)
            is_rs_lead = (
                pct_below_upper <= 0.03 and
                lc < upper and
                l8 > l20 and
                lc > l50
            )

            if is_rs_lead:
                entry      = round(lh * 1.001, 2)
                stop_base  = min(ll, highest_res["lower"])
                stop_loss  = round(stop_base - 0.2 * latr, 2)
                risk       = entry - stop_loss

                if risk > 0 and risk <= entry * 0.15:
                    take_profit = round(entry + 2.0 * risk, 2)
                    return {
                        "ticker":             ticker,
                        "setup_type":         "VCP",
                        "entry":              entry,
                        "stop_loss":          stop_loss,
                        "take_profit":        take_profit,
                        "rr":                 2.0,
                        "setup_date":         str(data.index[-1].date()),
                        "is_breakout":        True,
                        "is_vol_surge":       False,
                        "volume_ratio":       volume_ratio,
                        "resistance_level":   highest_res["level"],
                        "breakout_pct":       round(pct_below_upper * 100, 2),
                        "rs_vs_spy":          rs_vs_spy,
                        "tr_contraction_pct": None,
                        "is_trendline_breakout": False,
                        "is_kde_breakout":    False,
                        "is_rs_lead":         True,
                        "rs_ratio_today":     rs_ratio,
                        "rs_52w_high":        rs_52w_high,
                        "trendline":          None,
                    }
```

**Step 2: Update scan_vcp() signature to accept RS parameters**

Change line 151 from:
```python
def scan_vcp(
    ticker: str,
    df: pd.DataFrame,
    sr_zones: List[Dict],
    spy_3m_return: float = 0.0,
) -> Optional[Dict]:
```

To:
```python
def scan_vcp(
    ticker: str,
    df: pd.DataFrame,
    sr_zones: List[Dict],
    spy_3m_return: float = 0.0,
    rs_ratio: float = 0.0,
    rs_52w_high: float = 0.0,
    rs_blue_dot: bool = False,
) -> Optional[Dict]:
```

**Step 3: Verify syntax**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/backend
python -m py_compile engines/engine2.py
echo "✓ engine2.py syntax check passed"
```

Expected: `✓ engine2.py syntax check passed`

**Step 4: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/engines/engine2.py
git commit -m "feat: add Path E (RS LEAD) to scan_vcp() in engine2.py

- New path detects: RS Blue Dot + price within 3% of resistance
- Trend filter still applies (8 EMA > 20, close > 50 SMA)
- No volume surge requirement (institutional accumulation signal)
- Output: is_rs_lead=true with rs_ratio and rs_52w_high fields
- Less strict than VCP/DRY, catches early institutional moves"
```

---

## Task 4: Integrate RS Line and Path E into main.py

**Files:**
- Modify: `backend/main.py:40-65` (imports and engine4 integration)
- Modify: `backend/main.py:220-280` (SPY fetch and RS calculation)
- Modify: `backend/main.py:238-260` (_process function to use RS)
- Modify: `backend/main.py:280-320` (sector aggregation and logging)

**Step 1: Add imports**

At line 40, add:
```python
import json
```

At line 63, change:
```python
from engines.engine2 import scan_vcp, detect_trendline, scan_near_breakout
```

To:
```python
from engines.engine2 import scan_vcp, detect_trendline, scan_near_breakout
from engines.engine4 import calculate_rs_line, detect_rs_blue_dot
```

**Step 2: Load sectors.json at startup**

After line 79 (after log setup), add:
```python
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
```

**Step 3: Modify _run_scan to fetch SPY and calculate RS**

After line 206 (SPY 3-month return calculation), add SPY full fetch and RS calculation:

```python
        # ── SPY full data (for RS Line calculations) ─────────────────────
        spy_df_full = None
        try:
            spy_df_full = await _fetch("SPY")
            if spy_df_full is not None and len(spy_df_full) >= 252:
                log.info("SPY data fetched: %d days", len(spy_df_full))
        except Exception as exc:
            log.warning("Could not fetch full SPY data for RS: %s", exc)
```

**Step 4: Update _process() to calculate RS and call Path E**

Modify the _process function (around line 223-260) to add RS calculations:

```python
        async def _process(ticker: str, idx: int) -> None:
            nonlocal vcp_count, pb_count

            try:
                df = await _fetch(ticker)
                if df is None or len(df) < 60:
                    return

                # ── RS Line Calculation ────────────────────────────────────
                rs_line = None
                rs_ratio = 0.0
                rs_52w_high = 0.0
                rs_blue_dot = False

                if spy_df_full is not None:
                    rs_line = await loop.run_in_executor(
                        None, calculate_rs_line, df, spy_df_full
                    )
                    if rs_line and len(rs_line) >= 252:
                        rs_ratio = float(rs_line[-1])
                        rs_52w_high = float(max(rs_line))
                        rs_blue_dot = await loop.run_in_executor(
                            None, detect_rs_blue_dot, rs_line
                        )

                # Engine 1: S/R zones
                zones: List[Dict] = await loop.run_in_executor(
                    None, calculate_sr_zones, ticker, df
                )
                if zones:
                    await save_sr_zones(DB_PATH, scan_ts, ticker, zones)

                # Engine 2: VCP breakout (with RS parameters for Path E)
                vcp = await loop.run_in_executor(
                    None, scan_vcp, ticker, df, zones, spy_3m_return,
                    rs_ratio, rs_52w_high, rs_blue_dot
                )
                if vcp:
                    # Add sector to setup
                    vcp["sector"] = SECTORS.get(ticker, "Unknown")
                    await save_setup(DB_PATH, scan_ts, vcp)
                    vcp_count += 1

                    setup_type = "RS LEAD" if vcp.get("is_rs_lead") else "VCP"
                    log.info("  %s      %-6s  entry=%.2f", setup_type, ticker, vcp["entry"])

                else:
                    # Only check near-breakout if not already a full setup
                    tl = await loop.run_in_executor(None, detect_trendline, ticker, df)
                    near = await loop.run_in_executor(
                        None, scan_near_breakout, ticker, df, zones, tl
                    )
                    if near:
                        near["sector"] = SECTORS.get(ticker, "Unknown")
                        near["rs_blue_dot"] = rs_blue_dot
                        await save_setup(DB_PATH, scan_ts, near)
                        log.info("  NEAR     %-6s  dist=%.1f%%", ticker, near["distance_pct"])

                # Engine 3: Tactical pullback (strict, then relaxed)
                pb = await loop.run_in_executor(None, scan_pullback, ticker, df, zones)
                if pb:
                    pb["sector"] = SECTORS.get(ticker, "Unknown")
                    await save_setup(DB_PATH, scan_ts, pb)
                    pb_count += 1
                    log.info("  PULLBACK %-6s  entry=%.2f", ticker, pb["entry"])
                else:
                    # Only check relaxed if no strict pullback found
                    pb_relaxed = await loop.run_in_executor(
                        None, scan_relaxed_pullback, ticker, df, zones
                    )
                    if pb_relaxed:
                        pb_relaxed["sector"] = SECTORS.get(ticker, "Unknown")
                        await save_setup(DB_PATH, scan_ts, pb_relaxed)
                        pb_count += 1
                        log.info("  PULLBACK %-6s  entry=%.2f (relaxed)", ticker, pb_relaxed["entry"])

            except Exception as exc:
                log.error("Error processing %s: %s", ticker, exc)
            finally:
                _scan_state["progress"] = idx + 1
```

**Step 5: Add sector aggregation and logging before complete_scan_run**

After line 308 (after all tickers processed), add:

```python
        # ── Sector Summary ─────────────────────────────────────────────────
        # Count setups by sector and log with bold formatting for 3+ setups
        try:
            all_setups = await get_latest_setups(DB_PATH, scan_ts)
            sector_counts = {}
            for setup in all_setups:
                sector = setup.get("sector", "Unknown")
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

            # Sort by count descending
            sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)

            log.info("═════════════════════════════════════════════")
            log.info("SECTOR SUMMARY:")
            for sector, count in sorted_sectors:
                if count >= 3:
                    log.info("  🔥 **%s (%d setups)**", sector, count)
                else:
                    log.info("  %s (%d setup%s)", sector, count, "s" if count != 1 else "")
            log.info("═════════════════════════════════════════════")
        except Exception as exc:
            log.warning("Sector summary failed: %s", exc)
```

**Step 6: Verify syntax and commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/backend
python -m py_compile main.py
echo "✓ main.py syntax check passed"
```

Expected: `✓ main.py syntax check passed`

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/main.py swing-trading-dashboard/backend/sectors.json
git commit -m "feat: integrate RS Line and Path E into main.py scan pipeline

- Load sectors.json at startup for sector-based alerts
- Fetch SPY full data for RS Line calculation
- Calculate RS ratio and detect Blue Dots for all tickers
- Pass RS data to Path E detection in scan_vcp()
- Attach sector to all setups (VCP, Watchlist, Pullback)
- Aggregate and log sector summary with bold for 3+ setups
- Includes institutional lead detection in main scan loop"
```

---

## Task 5: Update SetupTable.jsx with LEAD Badge

**Files:**
- Modify: `frontend/src/components/SetupTable.jsx:66-68` (add flags)
- Modify: `frontend/src/components/SetupTable.jsx:106-130` (update VCP badge logic)

**Step 1: Add isRsLead flag**

After line 67 (after `isRelaxed` flag), add:
```javascript
                const isRsLead          = s.is_rs_lead === true
```

**Step 2: Update VCP badge section to show LEAD**

In the VCP signal section (around lines 106-130), update to show LEAD badge:

```jsx
                      {s.setup_type === 'VCP' ? (
                        <div className="flex items-center gap-1 flex-wrap">
                          {/* LEAD badge (RS) — only if RS lead */}
                          {isRsLead && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(0,200,255,0.10)', color: '#00C8FF', border: '1px solid rgba(0,200,255,0.3)', fontWeight: 700 }}
                            >
                              LEAD
                            </span>
                          )}

                          {/* KDE badge — only if KDE breakout and NOT RS lead */}
                          {!isRsLead && isKdeBreakout && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(0,200,255,0.10)', color: '#00C8FF', border: '1px solid rgba(0,200,255,0.3)', fontWeight: 700 }}
                            >
                              KDE
                            </span>
                          )}

                          {/* BRK / DRY badge — only if NOT KDE and NOT RS lead */}
                          {!isRsLead && !isKdeBreakout && (
                            <span
                              className="badge"
                              style={isBrk
                                ? { background: 'rgba(0,200,122,0.18)', color: 'var(--go)', border: '1px solid rgba(0,200,122,0.4)', fontWeight: 700 }
                                : { background: 'rgba(245,166,35,0.12)', color: 'var(--accent)', border: '1px solid rgba(245,166,35,0.3)' }
                              }
                            >
                              {isBrk ? 'BRK' : 'DRY'}
                            </span>
                          )}

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

                          {/* TDL badge — trendline breakout */}
                          {isTrendlineBreakout && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(255,255,255,0.08)', color: '#FFFFFF', border: '1px solid rgba(255,255,255,0.25)', fontSize: 8 }}
                            >
                              TDL
                            </span>
                          )}
                        </div>
```

**Step 3: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/frontend/src/components/SetupTable.jsx
git commit -m "feat: add LEAD badge to SetupTable for RS LEADs

- Add isRsLead flag check
- Show cyan 'LEAD' badge for RS Blue Dot setups (is_rs_lead=true)
- LEAD badge takes priority (shows instead of KDE/BRK/DRY)
- Maintains all other badges (volume ratio, RS+, TDL)"
```

---

## Task 6: Update WatchlistPanel.jsx with Blue Star

**Files:**
- Modify: `frontend/src/components/WatchlistPanel.jsx:35-60` (add blue star indicator)

**Step 1: Update watchlist item rendering**

In the watchlist items map (around lines 35-60), update the ticker display to add blue star:

```jsx
                {items.map((item) => {
                  const isSelected = selectedTicker === item.ticker
                  const isTdl = item.pattern_type === 'TDL'
                  const hasRsBlueDot = item.rs_blue_dot === true

                  return (
                    <div
                      key={item.ticker}
                      onClick={() => onSelectTicker(item.ticker)}
                      className="flex items-center justify-between px-2 py-1.5 cursor-pointer"
                      style={{
                        borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
                        background: isSelected ? 'rgba(245,166,35,0.06)' : 'transparent',
                        borderBottom: '1px solid var(--border)',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                      onMouseLeave={e => e.currentTarget.style.background = isSelected ? 'rgba(245,166,35,0.06)' : 'transparent'}
                    >
                      {/* Ticker with RS Blue Dot indicator */}
                      <div className="flex items-center gap-1">
                        <span className="font-600 text-[10px] tracking-wide"
                              style={{ color: isSelected ? 'var(--accent)' : 'var(--text)' }}>
                          {item.ticker}
                        </span>
                        {hasRsBlueDot && (
                          <span style={{ color: '#00C8FF', fontSize: '8px' }}>⭐</span>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        {/* Distance */}
                        <span className="font-mono text-[9px] tabular-nums"
                              style={{ color: item.distance_pct < 0.8 ? 'var(--go)' : 'var(--accent)' }}>
                          {item.distance_pct?.toFixed(1)}%
                        </span>

                        {/* Pattern badge */}
                        <span className="badge text-[7px]"
                              style={isTdl
                                ? { background: 'rgba(255,255,255,0.08)', color: '#FFF', border: '1px solid rgba(255,255,255,0.25)' }
                                : { background: 'rgba(0,200,255,0.10)', color: '#00C8FF', border: '1px solid rgba(0,200,255,0.3)' }
                              }>
                          {item.pattern_type}
                        </span>
                      </div>
                    </div>
                  )
                })}
```

**Step 2: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/frontend/src/components/WatchlistPanel.jsx
git commit -m "feat: add blue star indicator to watchlist for RS Blue Dots

- Show ⭐ (blue star) next to tickers with current RS Blue Dot
- Signals: approaching breakout + institutional accumulation
- UI refinement: helps traders spot early institutional moves"
```

---

## Task 7: Final Verification and Testing

**Files:**
- Check: All backend Python files (syntax)
- Check: Frontend JSX files (readability)
- Verify: All commits created

**Step 1: Verify all Python syntax**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/backend
python -m py_compile engines/engine4.py engines/engine2.py main.py
echo "✓ All Python files syntax check passed"
```

Expected: `✓ All Python files syntax check passed`

**Step 2: Verify frontend files**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/frontend
node -e "const fs = require('fs'); const files = ['src/components/SetupTable.jsx', 'src/components/WatchlistPanel.jsx']; files.forEach(f => { try { fs.readFileSync(f, 'utf8'); console.log('✓', f); } catch(e) { console.error('✗', f); } })"
```

Expected:
```
✓ src/components/SetupTable.jsx
✓ src/components/WatchlistPanel.jsx
```

**Step 3: Verify sectors.json**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
node -e "const s = JSON.parse(require('fs').readFileSync('swing-trading-dashboard/backend/sectors.json')); console.log('✓ sectors.json valid, ' + Object.keys(s).length + ' tickers mapped')"
```

Expected: `✓ sectors.json valid, 100 tickers mapped`

**Step 4: Check git log for all commits**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git log --oneline -7
```

Expected: See commits for engine4, sectors, engine2 Path E, main integration, SetupTable LEAD badge, WatchlistPanel star, plus 1 verification commit

---

## Summary

**7 tasks, ~7 commits:**
1. ✓ Create engine4.py with RS Line calculations
2. ✓ Create sectors.json static mapping
3. ✓ Add Path E (RS LEAD) to engine2.py
4. ✓ Integrate RS Line and Path E into main.py
5. ✓ Add LEAD badge to SetupTable.jsx
6. ✓ Add blue star to WatchlistPanel.jsx
7. ✓ Final verification and testing

**Test plan (manual):**
- Run `POST /api/run-scan` to trigger full scan with RS calculations
- Verify `/api/setups/vcp` returns setups with `is_rs_lead: true` for qualifying stocks
- Check logs for sector summary with bold formatting for 3+ setups
- Load dashboard and confirm cyan LEAD badges appear on RS LEADs
- Confirm blue ⭐ stars appear in watchlist for RS Blue Dot tickers
- Verify no performance regression (full scan including RS < 30 seconds)

---

## Data Fields Added to Setups

All setups now include:
- `sector`: Sector name from mapping (e.g., "Technology")
- `is_rs_lead`: Boolean (true for Path E setups)
- `rs_ratio_today`: Current ticker/SPY ratio (Path E only)
- `rs_52w_high`: 52-week high RS ratio (Path E only)
- `rs_blue_dot`: Boolean indicating RS Blue Dot status (Watchlist items)
