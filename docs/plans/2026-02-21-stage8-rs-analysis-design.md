# Stage 8: RS Line Analysis & Sector Mapping — Design Document

> **Status:** Approved
> **Date:** 2026-02-21
> **Goal:** Add RS Line institutional footprint detection and sector-based scanning alerts

---

## 1. RS Line Calculation (engine4.py)

**New file:** `backend/engines/engine4.py`

**Purpose:** Calculate daily RS ratios (ticker_price / SPY_price) and detect "Blue Dots" (52-week highs in the RS Line).

**Key functions:**
- `calculate_rs_line(ticker_df, spy_df)` — Returns array of daily RS ratios over 252 trading days (1 year)
  - Input: ticker DataFrame and SPY DataFrame (same date range)
  - Output: List of RS ratios [0.95, 0.96, 0.97, ...] aligned with dates
  - Handles NaN gracefully (forward fill or skip)

- `detect_rs_blue_dot(rs_line_values)` — Returns `True` if today's RS ratio >= max(last 252 days), `False` otherwise
  - Input: RS ratio array (last 252 values)
  - Output: Boolean indicating if current ratio is at 52-week high
  - Threshold: RS_today >= max(RS_history)

**Data structure:** RS ratio = `ticker_close / spy_close` for each trading day. A 52-week high in this ratio signals institutional accumulation.

---

## 2. Path E: RS Strength Breakout (engine2.py)

**New detection path** in `scan_vcp()` after Path D (KDE BRK):

**Trigger conditions:**
- Stock has **RS Blue Dot** (52-week high in RS ratio)
- Price is within **3% below** highest resistance zone upper boundary
- Trend filter: 8 EMA > 20 EMA AND Close > 50 SMA

**Does NOT require:**
- Volume surge (115% threshold waived)
- TR contraction (A/C shape checks waived)
- CCI conditions

**Risk math:** Entry = High × 1.001, Stop = min(Low, zone_lower) - 0.2×ATR, TP = Entry + 2×Risk

**Output:** `setup_type="VCP"`, `is_rs_lead=true`, includes:
- `rs_ratio_today`: Current ticker/SPY ratio (e.g., 0.982)
- `rs_52w_high`: Max RS ratio over last 252 days (e.g., 0.985)
- `sector`: Sector name from mapping

---

## 3. Sector Integration

**New file:** `backend/sectors.json` — Simple mapping:
```json
{
  "AAPL": "Technology",
  "GOOGL": "Technology",
  "JPM": "Financials",
  "XOM": "Energy",
  ...
}
```

**Integration:**
- Load at startup in main.py
- Attach sector to **all setups** (not just RS LEADs): `"sector": "Technology"`
- API endpoints include sector field
- Scan logs include sector summary with bold highlighting for sectors with 3+ setups

**Format in logs:**
```
Sector Summary:
  🔥 **Technology (5 setups)**
  Financials (2 setups)
  Energy (1 setup)
```

---

## 4. Frontend: RS Visualization

**SetupTable.jsx updates:**
- Add `isRsLead` boolean check
- Show cyan **"LEAD"** badge for RS setups (same styling as KDE badge)
- Add RS trend indicator next to ticker:
  - **🔵** (blue dot) if RS ratio is at/near 52-week high
  - (empty) if not in RS lead state

**WatchlistPanel.jsx updates (UI Refinement #1):**
- Add **⭐** (blue star) next to watchlist tickers that currently have RS Blue Dot
- Signals: "This ticker is approaching breakout AND institutional accumulation is happening"

**Scan logs (UI Refinement #2):**
- Highlight sectors with 3+ setups in bold: `**Technology (5 setups)**`
- Helps traders quickly identify sector rotations

---

## 5. Data Flow

```
Scan Start
├─ Fetch SPY data (full year)
├─ For each ticker:
│  ├─ Fetch ticker data (full year)
│  ├─ Calculate RS Line (ticker/SPY ratio)
│  ├─ Detect RS Blue Dot (52-week high in RS)
│  ├─ Look up sector from sectors.json
│  ├─ Run Path E check:
│  │  • RS Blue Dot = true?
│  │  • Price within 3% of resistance?
│  │  • Trend filter passes?
│  │  → If yes: Create VCP setup with is_rs_lead=true
│  │
│  ├─ Run Paths A-D (VCP, DRY, TDL, KDE)
│  └─ Run Engine 3 (strict/relaxed pullbacks)
│
├─ Aggregate sector counts
├─ Log scan summary with bold sectors (3+ setups)
└─ Save all setups to DB
```

---

## 6. Architecture Summary

| Component | Changes |
|-----------|---------|
| **engine4.py** | New: `calculate_rs_line()`, `detect_rs_blue_dot()` |
| **engine2.py** | Add Path E after Path D |
| **main.py** | Fetch SPY once; calculate RS for all tickers; integrate Path E; aggregate sector counts; log with bold formatting |
| **sectors.json** | New: Static mapping of 100 tickers → sectors |
| **SetupTable.jsx** | Add `isRsLead` flag check; show LEAD badge + 🔵 indicator |
| **WatchlistPanel.jsx** | Add ⭐ star next to tickers with RS Blue Dot (UI Refinement #1) |
| **Scan logs** | Add sector summary with bold formatting for 3+ setups (UI Refinement #2) |
| **API responses** | All setups include `sector`, `is_rs_lead`, `rs_ratio_today`, `rs_52w_high` fields |

---

## 7. Success Criteria

- ✓ RS Line calculated correctly (ticker/SPY ratio over 252 days)
- ✓ Blue Dot detection accurate (52-week high identification)
- ✓ Path E triggers only when all conditions met
- ✓ Sector mapping complete and accurate for all 100 tickers
- ✓ Scan logs show bold sector alerts for 3+ setups
- ✓ Watchlist shows ⭐ for RS Blue Dot tickers
- ✓ SetupTable displays LEAD badge with 🔵 indicator
- ✓ No performance regression (SPY fetch + RS calc under 2 seconds for 100 tickers)

---

## 8. Error Handling

- If SPY data unavailable: Skip Path E for that scan, log warning
- If RS calculation fails for a ticker: Continue to other paths, log error
- If sector missing from JSON: Use "Unknown" as fallback
- If RS ratio is NaN: Treat as not-a-blue-dot, continue

---

## Notes

- "Messy charts" tolerance: RS Blue Dots catch early institutional accumulation even when price action is choppy
- Path E is less strict than VCP/DRY but more selective than KDE BRK
- Sector alerts help traders identify sector rotations at a glance
- Blue star in watchlist bridges gap between "approaching" and "accumulating" signals
