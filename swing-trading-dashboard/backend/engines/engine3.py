"""
Engine 3: Tactical Pullback Scanner — The 8/20 Value Zone
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detects high-quality pullbacks to the 8/20 EMA value zone that
coincide with an Engine 1 support zone, confirming a pin-bar
rejection AND a CCI momentum hook.

Filter chain (all must pass):
  1. Trend        : 8 EMA > 20 EMA  AND  Close > 50 SMA
  2. Value Zone   : Daily Low penetrates 8 EMA or 20 EMA (enters value zone)
  3. Support Touch: Low touches an Engine 1 SUPPORT zone
  4. Rejection    : Daily Close ≥ 20 EMA (pin bar — closed back above)
  5. CCI Hook     : CCI[yesterday] < −100  AND  CCI[today] > CCI[yesterday]
                    (momentum turning from oversold)

Risk Math:
  Entry      = High of setup candle + 0.1 %
  Stop Loss  = min(Low, zone_lower) − 0.2 × ATR
  Take Profit= Entry + 2 × Risk   (1:2 R:R)
"""

import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indicators import ema as _ema, sma as _sma, atr as _atr, cci as _cci


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_pullback(
    ticker: str,
    df: pd.DataFrame,
    sr_zones: List[Dict],
) -> Optional[Dict]:
    """
    Returns a setup dict if a valid tactical pullback is found, else None.
    """
    try:
        data = _prep(df)
        if data is None or len(data) < 60:
            return None

        adj = _adj_col(data)
        close = data[adj]
        high = data["High"]
        low = data["Low"]

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

        # ── 2. Value zone retest ──────────────────────────────────────────
        # Low must penetrate 8 EMA or 20 EMA to be "in the value zone"
        if not (ll <= l8 or ll <= l20):
            return None

        # ── 3. Engine 1 support zone touch ───────────────────────────────
        support_zones = [z for z in sr_zones if z["type"] == "SUPPORT"]
        nearest_sup = None

        for z in support_zones:
            # Low dips into the zone (with a tiny 0.5 % tolerance)
            low_in_zone = z["lower"] * 0.995 <= ll <= z["upper"] * 1.005
            close_in_zone = z["lower"] <= lc <= z["upper"]
            if low_in_zone or close_in_zone:
                nearest_sup = z
                break

        if nearest_sup is None:
            return None

        # ── 4. Rejection (pin bar) ────────────────────────────────────────
        # Close must be at or above 20 EMA — price closed back into the trend
        if lc < l20:
            return None

        # ── 5. CCI momentum hook ─────────────────────────────────────────
        if not (cci_prev < -100.0 and cci_today > cci_prev):
            return None

        # ── Risk math ────────────────────────────────────────────────────
        entry = round(lh * 1.001, 2)

        # Stop: min(candle low, zone bottom) − 0.2 × ATR
        stop_base = min(ll, nearest_sup["lower"])
        stop_loss = round(stop_base - 0.2 * latr, 2)

        risk = entry - stop_loss
        if risk <= 0 or risk > entry * 0.15:
            return None

        take_profit = round(entry + 2.0 * risk, 2)

        return {
            "ticker": ticker,
            "setup_type": "PULLBACK",
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr": 2.0,
            "setup_date": str(data.index[-1].date()),
            "cci_today": round(cci_today, 2),
            "cci_yesterday": round(cci_prev, 2),
            "support_level": nearest_sup["level"],
            "ema8": round(l8, 2),
            "ema20": round(l20, 2),
        }

    except Exception as exc:  # noqa: BLE001
        print(f"[Engine3] {ticker}: {exc}")
        return None


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
        entry = round(lh * 1.001, 2)

        support_zones = [z for z in sr_zones if z["type"] == "SUPPORT"]
        # Use lowest (most defensive) support level for relaxed pullbacks
        support_level = min([z["level"] for z in support_zones]) if support_zones else l50

        # Validate support level is actually below current price
        if support_level >= lc:
            return None

        stop_base = min(ll, support_level)
        stop_loss = round(stop_base - 0.2 * latr, 2)
        risk = entry - stop_loss

        if risk <= 0 or risk > entry * 0.15:
            return None

        take_profit = round(entry + 2.0 * risk, 2)

        return {
            "ticker": ticker,
            "setup_type": "PULLBACK",
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr": 2.0,
            "setup_date": str(data.index[-1].date()),
            "cci_today": round(cci_today, 2),
            "cci_yesterday": round(cci_prev, 2),
            "support_level": support_level,
            "ema8": round(l8, 2),
            "ema20": round(l20, 2),
            "is_relaxed": True,
        }

    except Exception as exc:  # noqa: BLE001
        print(f"[scan_relaxed_pullback] {ticker}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prep(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    data = df.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"High", "Low"}
    if not required.issubset(data.columns):
        return None
    return data


def _adj_col(df: pd.DataFrame) -> str:
    return "Adj Close" if "Adj Close" in df.columns else "Close"
