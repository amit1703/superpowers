# Stage 8 Optimization Roadmap

## Quick Summary

**Current Estimated Scan Time:** 4-6 minutes for 809 tickers
**Target After Phase 1:** 2-3 minutes (50% faster)
**Target After All Phases:** 90-120 seconds (4-5x faster)

---

## Phase 1: CRITICAL (1-2 hours work, 50% speedup)

### 1.1 Increase Concurrency Limit
**File:** `main.py:73`
**Change:**
```python
CONCURRENCY_LIMIT = 10  # BEFORE
CONCURRENCY_LIMIT = 25  # AFTER
```
**Impact:** 40-50% faster yfinance fetches
**Risk:** Low (yfinance allows 5+ concurrent)
**Effort:** 5 minutes

### 1.2 Consolidate SPY Fetch
**File:** `main.py:225-243`
**Current Issue:** SPY fetched twice (lines 225 and 239)
**Fix:** Combine into single fetch
```python
# BEFORE (2 fetches, 2-4 seconds wasted)
spy_df = await _fetch("SPY")  # For 3m return
spy_df_full = await _fetch("SPY")  # For RS

# AFTER (1 fetch)
spy_df_full = await _fetch("SPY")
if spy_df_full is not None and len(spy_df_full) >= 252:
    spy_3m_return = spy_close.iloc[-1] / spy_close.iloc[-64] - 1
```
**Impact:** 2-4 seconds per scan
**Risk:** None
**Effort:** 10 minutes

### 1.3 Batch Database Inserts
**File:** `database.py` (refactor `save_setup()`)
**Current Issue:** 809 database writes per scan
**Fix:** Collect all setups, insert once
```python
# BEFORE: save_setup() called 809 times
for setup in setups:
    await save_setup(DB_PATH, scan_ts, setup)

# AFTER: Single batch insert
await batch_save_setups(DB_PATH, scan_ts, setups)
```
**Implementation:**
```python
async def batch_save_setups(db_path: str, scan_ts: str, setups: List[Dict]) -> None:
    async with aiosqlite.connect(db_path) as db:
        insert_values = [(scan_ts, ...) for s in setups]
        await db.executemany(
            "INSERT INTO scan_setups (...) VALUES (?, ?, ..., ?)",
            insert_values
        )
        await db.commit()
```
**Impact:** 5-10 seconds per scan
**Risk:** Low
**Effort:** 1 hour

**Total Phase 1 Effort:** 1-2 hours
**Total Phase 1 Speedup:** 50% (2-3 min per scan)

---

## Phase 2: HIGH PRIORITY (2-3 hours work, 20% additional speedup)

### 2.1 Parallelize Independent Operations
**File:** `main.py:274-295` (_process function)
**Current:** RS → SR → VCP (sequential)
**Fix:** Parallel RS + SR, then VCP

```python
# BEFORE (sequential)
rs_line = await loop.run_in_executor(None, calculate_rs_line, df, spy_df_full)
zones = await loop.run_in_executor(None, calculate_sr_zones, ticker, df)

# AFTER (parallel)
rs_task = loop.run_in_executor(None, calculate_rs_line, df, spy_df_full)
zones_task = loop.run_in_executor(None, calculate_sr_zones, ticker, df)
rs_line, zones = await asyncio.gather(rs_task, zones_task)
```
**Impact:** 20-30% per ticker × 809 = 60-90 seconds
**Risk:** Low
**Effort:** 1 hour

### 2.2 Add Database Indexes
**File:** `database.py`
**Queries:**
```sql
CREATE INDEX IF NOT EXISTS idx_setups_scan_type 
ON scan_setups(scan_timestamp, setup_type);

CREATE INDEX IF NOT EXISTS idx_setups_ticker 
ON scan_setups(ticker);

CREATE INDEX IF NOT EXISTS idx_sr_zones_scan 
ON sr_zones(scan_timestamp);
```
**Impact:** 2-3 seconds on API queries
**Risk:** None
**Effort:** 30 minutes

### 2.3 Conditional RS Calculation
**File:** `main.py:215-220`
**Current Issue:** RS calculated even when market is bearish
**Fix:** Check regime before RS loop
```python
if regime["is_bullish"]:
    # Run RS calculation and engines
else:
    log.info("Market BEARISH - skipping engines")
    return
```
**Impact:** 0-80 seconds (depends on regime)
**Risk:** None
**Effort:** 30 minutes

**Total Phase 2 Effort:** 2-3 hours
**Total Phase 2 Speedup:** Additional 20% (90-120s total)

---

## Phase 3: MEDIUM PRIORITY (1-2 hours work, code quality)

### 3.1 Extract Magic Numbers
**Files:** All engines
**Create:** `backend/constants.py`
```python
# Thresholds
RS_BLUE_DOT_TOLERANCE_PCT = 0.005  # 0.5%
PRICE_RESISTANCE_PROXIMITY_PCT = 0.03  # 3%
KDE_BREAKOUT_UPPER_PCT = 0.025  # 2.5%
KDE_BREAKOUT_LOWER_PCT = 0.001  # 0.1%
DRY_RESISTANCE_PROXIMITY_PCT = 0.05  # 5%

# Periods
TRADING_DAYS_IN_YEAR = 252
VOL_SMA_PERIOD = 50
TR_WINDOW = 14
EMA_SHORT = 8
EMA_LONG = 20
SMA_LONG = 50

# Multipliers
VOL_SURGE_MULTIPLIER = 1.5  # 150%
KDE_VOL_MULTIPLIER = 1.15  # 115%
TRENDLINE_VOL_MULTIPLIER = 1.2  # 120%
ATR_STOP_MULTIPLIER = 0.2
ENTRY_MULTIPLIER = 1.001
```
**Impact:** Code maintainability, easier to test different thresholds
**Risk:** None
**Effort:** 1 hour

### 3.2 Centralize Data Validation
**Create:** `backend/validation.py`
```python
def validate_ticker_data(df: pd.DataFrame, min_rows: int = 60) -> bool:
    """Validate ticker has sufficient clean data"""
    if df is None or len(df) < min_rows:
        return False
    if df["Close"].isna().all():
        return False
    return True
```
**Impact:** Consistent error handling
**Effort:** 1 hour

### 3.3 Replace print() with Logging
**Files:** All engines
**Change:** Use `log.error()` instead of `print(f"...")`
**Impact:** Better observability
**Effort:** 30 minutes

---

## Phase 4: MONITORING & OBSERVABILITY (1 hour)

### 4.1 Add Scan Timing Instrumentation
**File:** `main.py:184-440`
```python
import time

async def _run_scan(...):
    scan_start = time.time()
    
    # Fetch phase
    fetch_start = time.time()
    # ... fetches ...
    fetch_time = time.time() - fetch_start
    log.info("METRIC fetch_time=%.1fs", fetch_time)
    
    # Processing phase
    process_start = time.time()
    # ... processing ...
    process_time = time.time() - process_start
    log.info("METRIC process_time=%.1fs", process_time)
    
    # DB phase
    db_start = time.time()
    # ... saves ...
    db_time = time.time() - db_start
    log.info("METRIC db_time=%.1fs", db_time)
    
    total_time = time.time() - scan_start
    log.info("METRIC total_scan_time=%.1f s tickers=%d", total_time, len(tickers))
```
**Impact:** Track optimization progress
**Effort:** 1 hour

---

## Implementation Priority

**Recommended Order:**
1. Phase 1.1: Concurrency limit (5 min)
2. Phase 1.2: SPY fetch (10 min)
3. Phase 1.3: Batch inserts (1 hour)
4. Phase 2.1: Parallelization (1 hour)
5. Phase 2.2: Database indexes (30 min)
6. Phase 2.3: Conditional RS (30 min)
7. Phase 4.1: Monitoring (1 hour) - do this FIRST to measure impact
8. Phase 3: Code quality (remaining)

**Suggested Timeline:**
- Day 1: Phase 1 (1-2 hours) + Phase 4 monitoring (1 hour)
  - Test concurrency limit incrementally (10 → 15 → 20 → 25)
- Day 2: Phase 2 (2-3 hours)
- Day 3: Phase 3 (1-2 hours)

---

## Rollback Strategy

All changes are reversible:
- Concurrency limit: Change constant back
- SPY fetch: Split back into two fetches
- Batch inserts: Revert to loop of individual saves
- Parallelization: Change asyncio.gather() back to sequential awaits

No database schema changes needed until Phase 2.2 indexes.

---

## Testing Checklist

After each phase:
- [ ] Scan completes without errors
- [ ] All setups recorded correctly
- [ ] Sector summary populated
- [ ] LEAD badges visible
- [ ] Blue stars visible in watchlist
- [ ] No duplicate/missing setups
- [ ] Timing metrics show improvement

---

## Expected Results

| Phase | Cumulative Time | Speedup | Effort |
|-------|-----------------|---------|--------|
| Baseline | 4-6 min | 1x | - |
| Phase 1 | 2-3 min | 2x | 1-2h |
| Phase 2 | 90-120s | 3-4x | 2-3h |
| Phase 3 | 90-120s | 3-4x | 1-2h (code quality) |
| Phase 4 | 90-120s | 3-4x | 1h (monitoring) |

**Total Implementation Time:** 5-8 hours for 4x speedup
