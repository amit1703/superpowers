# Market Expansion & Breakout Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand scan universe to S&P 500 + Russell 1000 and add confirmed breakout detection with volume surge and relative strength filters.

**Architecture:** Five files change — tickers.py (expanded universe), engine1.py (dynamic KDE bandwidth), engine2.py (two-path breakout + RS filter), main.py (semaphore → 10, SPY RS pre-fetch), SetupTable.jsx (vol-surge row highlight + badges).

**Tech Stack:** Python / FastAPI / pandas / scipy / yfinance, React / Tailwind / lightweight-charts

---

### Task 1: tickers.py — Expanded Universe

**Files:**
- Modify: `swing-trading-dashboard/backend/tickers.py`

Replace NASDAQ_100 with combined S&P 500 + Russell 1000 deduplicated list (~700 unique tickers). Remove `NASDAQ_100` constant, replace with `SP500` + `RUSSELL1000_EXTRA` lists, set `SCAN_UNIVERSE = list(dict.fromkeys(SP500 + RUSSELL1000_EXTRA))`.

---

### Task 2: engine1.py — Dynamic KDE Bandwidth

**Files:**
- Modify: `swing-trading-dashboard/backend/engines/engine1.py`

Replace fixed `bw_method="scott"` with dynamic scaling:
- Compute coefficient of variation (CV = std/mean) of price_points
- Scale Scott bandwidth: `bw_scale = max(0.4, min(1.2, cv / 0.05))`
- Result: low-vol stocks get tighter zones, high-vol stocks get wider

---

### Task 3: engine2.py — Confirmed Breakout + RS Filter

**Files:**
- Modify: `swing-trading-dashboard/backend/engines/engine2.py`

Two detection paths:
1. **DRY path** (existing): TR contraction + U-shape + volume dry-up below resistance
2. **BRK path** (new): Close 0.5–3% above resistance upper boundary + vol ≥ 150% SMA + stock 3m RS > SPY 3m RS

New parameter: `spy_3m_return: float = 0.0`
New return fields: `is_vol_surge`, `rs_vs_spy`, `breakout_pct`

---

### Task 4: main.py — Semaphore + SPY RS Pre-fetch

**Files:**
- Modify: `swing-trading-dashboard/backend/main.py`

- Change `CONCURRENCY_LIMIT = 5` → `10`
- At scan start, fetch SPY and compute 3-month return once
- Pass `spy_3m_return` to every `scan_vcp` call

---

### Task 5: SetupTable.jsx — Volume Surge Highlight + Badges

**Files:**
- Modify: `swing-trading-dashboard/frontend/src/components/SetupTable.jsx`

- Green row background when `s.is_vol_surge === true`
- BRK badge: bold green with "BRK" text
- DRY badge: amber with "DRY" text
- VOL ratio displayed in Info column as `×1.8` style
- RS badge: show "RS+" in cyan when `s.rs_vs_spy > 0`
