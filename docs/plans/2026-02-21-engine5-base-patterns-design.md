# Engine 5: Base Pattern Scanner — Design Doc
**Date:** 2026-02-21
**Status:** Approved
**Scope:** Cup & Handle + Flat Base detection with quality scoring

---

## Overview

Add **Engine 5** (`engine5.py`) — a dedicated base pattern scanner that detects Cup & Handle and Flat Base setups on the daily timeframe. This fills a major gap in the current scanner, which only detects VCP/TDL breakouts and EMA pullbacks but misses longer consolidation bases that precede stage 2 breakouts.

---

## Architecture

### New Files
- `swing-trading-dashboard/backend/engines/engine5.py` — base pattern scanner

### Modified Files
- `swing-trading-dashboard/backend/main.py` — wire Engine 5 into the scan loop, add `/api/setups/base` endpoint
- `swing-trading-dashboard/frontend/src/App.jsx` — add third SetupTable instance for "Base Patterns"
- `swing-trading-dashboard/frontend/src/SetupTable.jsx` — add C&H, FLAT, Q-score badges

### Integration Point
Engine 5 runs after Engine 1 (S/R zones computed), **parallel to Engines 2 & 3** in the existing async per-ticker loop. It does not depend on Engine 2 or Engine 3 output.

---

## Detection Logic

### Cup & Handle (30–120 day lookback, daily bars)

**Filters (all must pass):**

1. **Left peak** — highest close in the lookback window
2. **Cup bottom** — lowest close after left peak; cup depth = `(left_peak − cup_bottom) / left_peak` must be **12–35%**
   - < 12% = too shallow, not meaningful
   - > 35% = damaged stock, avoid
3. **Right rim** — highest close after cup bottom; must recover to within **10% of left peak** (cup must be formed)
4. **Cup shape** — scipy parabola fit (`curve_fit`) over cup region; coefficient `a > 0` required (U-shape, reject V-shape)
5. **Handle** — price action after right rim:
   - Duration: 5–25 trading days
   - Pullback: 5–15% from right rim
   - Volume: 3-day avg vol < 50-day vol SMA (must be contracting)
   - Handle low must not undercut the cup's midpoint
6. **Signal:**
   - `DRY` — current close within 1.5% below handle high (pre-breakout coil)
   - `BRK` — close above handle high with vol ≥ 120% of 50-day vol SMA (confirmed breakout)

### Flat Base (25–60 day lookback, daily bars)

**Filters (all must pass):**

1. **Range depth** — `(range_high − range_low) / range_high ≤ 15%`
2. **Duration** — minimum 25 trading days (5 weeks)
3. **Price location** — current close in upper 75% of base range (not sagging toward lows)
4. **Volume contraction** — 10-day avg volume ≤ 85% of 50-day vol SMA
5. **Signal:**
   - `DRY` — current close within 1.5% below base high
   - `BRK` — close above base high with vol ≥ 120% of 50-day vol SMA

---

## Quality Score (0–100)

Four equally-weighted factors (25 pts each):

| Factor | Max | Logic |
|--------|-----|-------|
| **RS vs SPY** | 25 | 3-month stock return vs SPY; outperformance ≥ 5% = full 25 pts, scales linearly |
| **Base tightness** | 25 | Depth ≤ 8% = 25 pts; scales to 0 pts at 15% (flat) or 35% (cup) |
| **Volume dry-up** | 25 | Base avg vol ≤ 50% of 50-day avg = 25 pts; scales to 0 pts at 100% |
| **RS near 52-wk high** | 25 | Engine 4 blue dot logic: RS ratio within 0.5% of 52-wk high = 25 pts, else 0 |

---

## Risk Math

Consistent with Engines 2 & 3:

```
Entry      = pivot_high × 1.001
             (handle high for C&H, base high for FLAT)

Stop Loss  = min(handle_low, base_low) − 0.2 × ATR14

Take Profit= Entry + 2.0 × (Entry − Stop Loss)   [1:2 R:R]
```

Risk guard: `risk > 15% of entry` → reject setup (avoid runaway stops).

---

## Output Schema

```python
{
    "ticker":           str,
    "setup_type":       "BASE",
    "base_type":        "CUP_HANDLE" | "FLAT_BASE",
    "signal":           "DRY" | "BRK",
    "entry":            float,
    "stop_loss":        float,
    "take_profit":      float,
    "rr":               2.0,
    "quality_score":    int,          # 0–100
    "base_depth_pct":   float,        # e.g. 14.2 for 14.2%
    "base_length_days": int,          # trading days base has been forming
    "volume_dry_pct":   float,        # base avg vol as % of 50-day avg
    "rs_vs_spy":        float,        # 3-month outperformance vs SPY
    "setup_date":       str,          # "YYYY-MM-DD"
}
```

---

## API Changes

**New endpoint:**
```
GET /api/setups/base    →  List[setup] filtered by setup_type="BASE"
```

**Existing endpoint unchanged:**
```
GET /api/setups         →  returns BASE setups alongside VCP/PULLBACK
```

---

## Frontend Changes

### New "Base Patterns" Table
Third `SetupTable` instance below "Tactical Pullbacks":
- Title: `BASE PATTERNS`
- Data source: `/api/setups/base`

### New Badges (SetupTable.jsx)
| Badge | Color | Condition |
|-------|-------|-----------|
| `C&H` | green `#26a69a` | `base_type === "CUP_HANDLE"` |
| `FLAT` | blue `#42a5f5` | `base_type === "FLAT_BASE"` |
| `Q87` | white monospace | always shown — quality score |
| `BRK` | green | `signal === "BRK"` |
| `DRY` | amber | `signal === "DRY"` |
| `RS+` | cyan | `rs_vs_spy > 0` |

---

## What This Does NOT Change

- Engines 0–4 are untouched
- Existing setup types (VCP, PULLBACK, WATCHLIST) are unaffected
- DB schema gets a new row type but no new table (reuses the existing `setups` table)
- Market regime gate: Engine 5 is skipped when Engine 0 returns BEARISH (same as Engines 2 & 3)
