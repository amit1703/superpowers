# Stage 7: Engine Relaxation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two new relaxed detection paths (KDE BRK horizontal breakout and relaxed tactical pullback) while preserving strict logic, surface them in the UI with distinct badges, and keep watchlist focused on pre-breakout proximity signals.

**Architecture:**
- Extend `scan_vcp()` in engine2.py with a new Path D (KDE BRK) that triggers after all other VCP paths fail, checking simple horizontal breakout rules (0.1%-2.5% above resistance, volume ≥115%, neutral/positive RS).
- Create new `scan_relaxed_pullback()` in engine3.py that runs only if strict pullback doesn't match, using relaxed buffer zone (0.8% from EMA-8 OR EMA-20), early CCI signal (turn from negative), and low 3-day volume.
- Integrate both into main.py's `_process()` function to call at appropriate times.
- Update SetupTable.jsx to display cyan "KDE" badge for KDE BRK setups and optional "RLX" badge for relaxed pullbacks.

**Tech Stack:** Python (engine2.py, engine3.py, main.py), React (SetupTable.jsx), pandas, numpy

---

## Task 1: Add Path D (KDE BRK) to engine2.py

**Files:**
- Modify: `backend/engines/engine2.py:375-400` (add new path after Path C)

**Step 1: Review current scan_vcp() structure**

Open `backend/engines/engine2.py` and locate the end of Path C (Trendline Breakout) around line 305. The function currently returns a setup dict if any path matches. We'll add Path D after Path C as a fallback.

**Step 2: Add KDE BRK path logic**

After the closing brace of Path C (around line 306), add this new path:

```python
        # ── PATH D — KDE Horizontal Breakout ─────────────────────────────────
        # Simple breakout: price above resistance zone with volume + RS gate
        # Only checked if no earlier paths matched

        highest_res = None
        highest_level = 0.0
        for z in resistance_zones:
            if z["level"] > highest_level:
                highest_level = z["level"]
                highest_res = z

        if highest_res is not None:
            upper = highest_res["upper"]
            pct_above_upper = (lc - upper) / upper if upper > 0 else 0.0

            # Check: 0.1% to 2.5% above resistance + volume ≥115% + RS ≥0
            is_kde_breakout = (
                0.001 <= pct_above_upper <= 0.025 and
                lvol >= 1.15 * avg_vol and
                rs_vs_spy >= 0
            )

            if is_kde_breakout:
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
                        "is_vol_surge":       lvol >= 1.5 * avg_vol,
                        "volume_ratio":       volume_ratio,
                        "resistance_level":   highest_res["level"],
                        "breakout_pct":       round(pct_above_upper * 100, 2),
                        "rs_vs_spy":          rs_vs_spy,
                        "tr_contraction_pct": None,
                        "is_trendline_breakout": False,
                        "is_kde_breakout":    True,
                        "trendline":          None,
                    }
```

**Step 3: Verify structure**

The new path should be inserted after the entire Path C block (around line 306) and before the final `except` block. Make sure indentation matches surrounding code (4 spaces per level).

**Step 4: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/engines/engine2.py
git commit -m "feat: add Path D (KDE BRK) horizontal breakout detection to engine2.py

- Detect simple breakouts: 0.1%-2.5% above highest resistance zone
- Volume gate: >=115% of 50-day SMA
- RS filter: neutral or positive (rs_vs_spy >= 0)
- Output: is_kde_breakout=true flag in VCP setup"
```

---

## Task 2: Create scan_relaxed_pullback() in engine3.py

**Files:**
- Modify: `backend/engines/engine3.py` (add new function after scan_pullback())

**Step 1: Locate insertion point**

Open `backend/engines/engine3.py`. Find the end of `scan_pullback()` function (around line 130-140). After its final `except` block, we'll add the new `scan_relaxed_pullback()` function.

**Step 2: Add new function**

After the closing of `scan_pullback()`, add:

```python
def scan_relaxed_pullback(
    ticker: str,
    df: pd.DataFrame,
    sr_zones: List[Dict],
) -> Optional[Dict]:
    """
    Relaxed tactical pullback: triggers when no strict pullback found.

    Criteria:
    1. Trend: 8 EMA > 20 EMA AND Close > 50 SMA
    2. Buffer Zone: Close within 0.8% of EMA-8 OR EMA-20 (either, not both)
    3. CCI Early Signal: CCI[today] > CCI[yesterday] AND CCI[yesterday] < 0
    4. Low Volume: 3-day avg volume <= 100% of 50-day SMA
    """
    try:
        data = _prep(df)
        if data is None or len(data) < 60:
            return None

        adj = _adj_col(data)
        close = data[adj]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]

        if close.dropna().shape[0] < 55:
            return None

        # ── Indicators ───────────────────────────────────────────────────
        ema8 = _ema(close, 8)
        ema20 = _ema(close, 20)
        sma50 = _sma(close, 50)
        cci20 = _cci(high, low, close, 20)
        atr14 = _atr(high, low, close, 14)

        cci_clean = cci20.dropna()
        if len(cci_clean) < 2:
            return None

        lc = float(close.iloc[-1])
        lh = float(high.iloc[-1])
        ll = float(low.iloc[-1])
        l8 = float(ema8.iloc[-1])
        l20 = float(ema20.iloc[-1])
        l50 = float(sma50.iloc[-1])
        latr = float(atr14.iloc[-1])
        cci_today = float(cci20.iloc[-1])
        cci_prev = float(cci20.iloc[-2])

        if any(np.isnan(v) for v in [lc, lh, ll, l8, l20, l50, latr, cci_today, cci_prev]):
            return None

        # ── 1. Trend filter ───────────────────────────────────────────────
        if not (l8 > l20 and lc > l50):
            return None

        # ── 2. Buffer Zone: within 0.8% of EMA-8 OR EMA-20 ───────────────
        dist_to_8 = abs(lc - l8) / l8 if l8 > 0 else float("inf")
        dist_to_20 = abs(lc - l20) / l20 if l20 > 0 else float("inf")

        near_8 = dist_to_8 <= 0.008
        near_20 = dist_to_20 <= 0.008

        if not (near_8 or near_20):
            return None

        # ── 3. CCI Early Signal: turning from negative ────────────────────
        cci_turning = cci_today > cci_prev and cci_prev < 0
        if not cci_turning:
            return None

        # ── 4. Low Volume: 3-day avg <= 100% of 50-day SMA ────────────────
        vol_sma50 = volume.rolling(50).mean()
        if pd.isna(vol_sma50.iloc[-1]) or float(vol_sma50.iloc[-1]) <= 0:
            return None

        avg_vol = float(vol_sma50.iloc[-1])
        last3_vol = float(volume.iloc[-3:].mean())

        if last3_vol > avg_vol:
            return None

        # ── Risk Math ─────────────────────────────────────────────────────
        entry      = round(lh * 1.001, 2)

        support_zones = [z for z in sr_zones if z["type"] == "SUPPORT"]
        support_level = min([z["level"] for z in support_zones]) if support_zones else l50

        stop_base  = min(ll, support_level)
        stop_loss  = round(stop_base - 0.2 * latr, 2)
        risk       = entry - stop_loss

        if risk <= 0 or risk > entry * 0.15:
            return None

        take_profit = round(entry + 2.0 * risk, 2)

        return {
            "ticker":        ticker,
            "setup_type":    "PULLBACK",
            "entry":         entry,
            "stop_loss":     stop_loss,
            "take_profit":   take_profit,
            "rr":            2.0,
            "setup_date":    str(data.index[-1].date()),
            "cci_today":     round(cci_today, 1),
            "cci_yesterday": round(cci_prev, 1),
            "is_relaxed":    True,
        }

    except Exception as exc:  # noqa: BLE001
        print(f"[scan_relaxed_pullback] {ticker}: {exc}")
        return None
```

**Step 3: Verify imports**

Check that the function has access to required helpers (`_prep`, `_adj_col`, `_ema`, `_sma`, `_cci`, `_atr`). These should already be imported at the top of engine3.py from the indicators module.

**Step 4: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/engines/engine3.py
git commit -m "feat: add scan_relaxed_pullback() function to engine3.py

- Relaxed buffer zone: 0.8% from EMA-8 OR EMA-20 (either)
- CCI early signal: turn positive when CCI_yesterday < 0
- Low 3-day volume: <= 100% of 50-day SMA
- Output: is_relaxed=true flag in PULLBACK setup"
```

---

## Task 3: Integrate scan_relaxed_pullback into main.py

**Files:**
- Modify: `backend/main.py:62` (update imports)
- Modify: `backend/main.py:248-253` (integrate into _process())

**Step 1: Update engine3 import**

At line 62-63 in main.py, change:

```python
from engines.engine3 import scan_pullback
```

To:

```python
from engines.engine3 import scan_pullback, scan_relaxed_pullback
```

**Step 2: Integrate into _process() function**

Find the pullback scan section in `_process()` (around line 248-253). Currently it looks like:

```python
                # Engine 3: Tactical pullback
                pb = await loop.run_in_executor(None, scan_pullback, ticker, df, zones)
                if pb:
                    await save_setup(DB_PATH, scan_ts, pb)
                    pb_count += 1
                    log.info("  PULLBACK %-6s  entry=%.2f", ticker, pb["entry"])
```

Replace with:

```python
                # Engine 3: Tactical pullback (strict, then relaxed)
                pb = await loop.run_in_executor(None, scan_pullback, ticker, df, zones)
                if pb:
                    await save_setup(DB_PATH, scan_ts, pb)
                    pb_count += 1
                    log.info("  PULLBACK %-6s  entry=%.2f", ticker, pb["entry"])
                else:
                    # Only check relaxed if no strict pullback found
                    pb_relaxed = await loop.run_in_executor(
                        None, scan_relaxed_pullback, ticker, df, zones
                    )
                    if pb_relaxed:
                        await save_setup(DB_PATH, scan_ts, pb_relaxed)
                        pb_count += 1
                        log.info("  PULLBACK %-6s  entry=%.2f (relaxed)", ticker, pb_relaxed["entry"])
```

**Step 3: Verify indentation and structure**

Make sure the new code block aligns with surrounding code (same indentation as the VCP block above it).

**Step 4: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/backend/main.py
git commit -m "feat: integrate scan_relaxed_pullback into main.py _process()

- Import scan_relaxed_pullback from engine3
- Call relaxed scan only if strict pullback doesn't match
- Log with '(relaxed)' tag for visibility"
```

---

## Task 4: Update SetupTable.jsx with KDE and RLX badges

**Files:**
- Modify: `frontend/src/components/SetupTable.jsx:60-147` (add badge logic)

**Step 1: Add isKdeBreakout and isRelaxed flags**

In the `setups.map()` section (around line 60-66), add two new boolean checks after the existing flags:

```javascript
                const isSelected        = selectedTicker === s.ticker
                const isVolSurge        = s.is_vol_surge === true
                const isBrk             = s.is_breakout === true
                const isRsPlus          = typeof s.rs_vs_spy === 'number' && s.rs_vs_spy > 0
                const isTrendlineBreakout = s.is_trendline_breakout === true
                const isKdeBreakout     = s.is_kde_breakout === true
                const isRelaxed         = s.is_relaxed === true
```

**Step 2: Add KDE badge in VCP signal section**

Inside the `s.setup_type === 'VCP'` block (around line 105-147), find the BRK/DRY badge section and add the KDE badge logic. Update to:

```jsx
                      ) : s.setup_type === 'VCP' ? (
                        <div className="flex items-center gap-1 flex-wrap">
                          {/* KDE badge — only if KDE breakout */}
                          {isKdeBreakout && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(0,200,255,0.10)', color: '#00C8FF', border: '1px solid rgba(0,200,255,0.3)', fontWeight: 700 }}
                            >
                              KDE
                            </span>
                          )}

                          {/* BRK / DRY badge — only if NOT KDE breakout */}
                          {!isKdeBreakout && (
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

**Step 3: Add RLX badge for pullbacks**

In the pullback section (currently around line 149-153), replace:

```jsx
                      ) : (
                        /* Pullback: show CCI value */
                        <span className="text-t-muted text-[9px]">
                          CCI {s.cci_today?.toFixed(0) ?? '—'}
                        </span>
                      )
```

With:

```jsx
                      ) : (
                        /* Pullback: show CCI value + RLX badge */
                        <div className="flex items-center gap-1">
                          <span className="text-t-muted text-[9px]">
                            CCI {s.cci_today?.toFixed(0) ?? '—'}
                          </span>
                          {isRelaxed && (
                            <span
                              className="badge"
                              style={{ background: 'rgba(245,166,35,0.12)', color: 'var(--accent)', border: '1px solid rgba(245,166,35,0.3)', fontSize: 7 }}
                            >
                              RLX
                            </span>
                          )}
                        </div>
                      )
```

**Step 4: Commit**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git add swing-trading-dashboard/frontend/src/components/SetupTable.jsx
git commit -m "feat: add KDE and RLX badges to SetupTable.jsx

- Show cyan 'KDE' badge for KDE BRK setups (is_kde_breakout=true)
- Hide BRK/DRY badge when KDE is shown (avoid clutter)
- Show amber 'RLX' badge for relaxed pullbacks (is_relaxed=true)
- Maintain existing styling for all other badges"
```

---

## Task 5: Final verification and test

**Files:**
- Check: `backend/engines/engine2.py`, `backend/engines/engine3.py`, `backend/main.py`, `frontend/src/components/SetupTable.jsx`

**Step 1: Verify Python syntax**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/backend
python -m py_compile engines/engine2.py engines/engine3.py main.py
echo "✓ Python syntax check passed"
```

Expected: No errors, "✓ Python syntax check passed"

**Step 2: Verify frontend files are readable**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest/swing-trading-dashboard/frontend
node -e "const fs = require('fs'); fs.readFileSync('src/components/SetupTable.jsx', 'utf8'); console.log('✓ SetupTable.jsx is valid')"
```

Expected: "✓ SetupTable.jsx is valid"

**Step 3: Check git log**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git log --oneline -5
```

Expected: See 5 recent commits including the Stage 7 commits

**Step 4: Final commit message**

```bash
cd /c/Users/1/OneDrive/Desktop/claudeSkillsTest
git log --oneline -4 | head -4
```

Should show:
- feat: add KDE and RLX badges to SetupTable.jsx
- feat: integrate scan_relaxed_pullback into main.py _process()
- feat: add scan_relaxed_pullback() function to engine3.py
- feat: add Path D (KDE BRK) horizontal breakout detection to engine2.py

---

# Summary

**5 focused tasks, 4 commits:**
1. ✓ Add KDE BRK path to engine2.py
2. ✓ Create scan_relaxed_pullback() in engine3.py
3. ✓ Integrate into main.py
4. ✓ Update SetupTable badges
5. ✓ Verify all changes

**Test plan:**
- Run `POST /api/run-scan` to trigger a full scan
- Verify `/api/setups/vcp` returns setups with `is_kde_breakout: true`
- Verify `/api/setups/pullback` returns setups with `is_relaxed: true`
- Load dashboard and confirm cyan "KDE" badges appear on horizontal breakouts
- Confirm amber "RLX" badges appear on relaxed pullbacks
