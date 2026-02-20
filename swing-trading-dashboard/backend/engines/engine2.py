"""
Engine 2: VCP Breakout Scanner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detects Volatility Contraction Pattern setups near Engine 1 resistance.

Filter chain (all must pass):
  1. Trend      : 8 EMA > 20 EMA  AND  Close > 50 SMA
  2. Contraction: Mean True Range of last 5 bars < Mean TR of prior 20 bars
  3. U-shape    : scipy curve_fit parabola over last 15 bars →  a > 0
                  (U-shape accumulation, reject V-shape drops)
  4. Volume     : Dry-up phase  (last 3 days avg < 50-day Vol SMA)
                  OR Breakout   (at/above resistance + vol ≥ 150 % of SMA)
  5. Location   : Price is consolidating strictly just below an Engine 1
                  resistance zone (within 5 % below zone level)

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
from scipy.optimize import curve_fit

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indicators import ema as _ema, sma as _sma, atr as _atr, true_range as _tr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_vcp(
    ticker: str,
    df: pd.DataFrame,
    sr_zones: List[Dict],
) -> Optional[Dict]:
    """
    Returns a setup dict if a valid VCP is found, else None.
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
        atr14 = _atr(high, low, close, 14)

        lc = float(close.iloc[-1])
        lh = float(high.iloc[-1])
        ll = float(low.iloc[-1])
        l8 = float(ema8.iloc[-1])
        l20 = float(ema20.iloc[-1])
        l50 = float(sma50.iloc[-1])
        latr = float(atr14.iloc[-1])
        lvol = float(volume.iloc[-1])

        if any(np.isnan(v) for v in [lc, lh, ll, l8, l20, l50, latr]):
            return None

        # ── 1. Trend filter ───────────────────────────────────────────────
        if not (l8 > l20 and lc > l50):
            return None

        # ── 2. True Range contraction ────────────────────────────────────
        tr = _tr(high, low, close).dropna()

        if len(tr) < 26:
            return None

        last5_tr = float(tr.iloc[-5:].mean())
        prev20_tr = float(tr.iloc[-25:-5].mean())

        if last5_tr >= prev20_tr:
            return None

        # ── 3. U-shape parabolic check (curve_fit) ───────────────────────
        lb = min(15, len(close) - 5)
        recent = close.values[-lb:].astype(float)
        if np.any(np.isnan(recent)):
            return None

        xv = np.arange(lb, dtype=float)
        mean_p, std_p = recent.mean(), recent.std()
        if std_p < 1e-8:
            return None

        yn = (recent - mean_p) / std_p
        is_u = False
        try:
            popt, _ = curve_fit(_parabola, xv, yn, maxfev=2000)
            a, b, _ = popt
            vertex_x = -b / (2.0 * a) if abs(a) > 1e-8 else -1.0
            # U-shape: parabola opens upward, vertex inside the window
            is_u = a > 0.005 and 0.0 <= vertex_x <= float(lb)
        except Exception:
            is_u = False

        if not is_u:
            return None

        # ── 4. Volume check ──────────────────────────────────────────────
        vol_sma50 = volume.rolling(50).mean()
        if pd.isna(vol_sma50.iloc[-1]) or float(vol_sma50.iloc[-1]) <= 0:
            return None

        avg_vol = float(vol_sma50.iloc[-1])
        last3_vol = float(volume.iloc[-3:].mean())
        is_dry = last3_vol < avg_vol
        is_breakout_vol = lvol >= 1.5 * avg_vol

        # ── 5. Engine 1 resistance proximity ────────────────────────────
        resistance_zones = [z for z in sr_zones if z["type"] == "RESISTANCE"]
        if not resistance_zones:
            return None

        nearest_res = None
        best_dist = float("inf")
        for z in resistance_zones:
            dist = z["level"] - lc
            # Within 5 % below resistance level, price hasn't broken through
            if 0.0 <= dist <= z["level"] * 0.05 and dist < best_dist:
                best_dist = dist
                nearest_res = z

        if nearest_res is None:
            return None

        # Volume gate: in dry-up phase below resistance, OR actual breakout
        at_breakout = lc >= nearest_res["lower"] and is_breakout_vol
        in_dry_up = lc < nearest_res["lower"] and is_dry

        if not (at_breakout or in_dry_up):
            return None

        # ── Risk math ────────────────────────────────────────────────────
        entry = round(lh * 1.001, 2)

        # Stop: min(candle low, zone lower bound) − 0.2 × ATR
        stop_base = min(ll, nearest_res["lower"])
        stop_loss = round(stop_base - 0.2 * latr, 2)

        risk = entry - stop_loss
        if risk <= 0 or risk > entry * 0.15:
            return None

        take_profit = round(entry + 2.0 * risk, 2)

        return {
            "ticker": ticker,
            "setup_type": "VCP",
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr": 2.0,
            "setup_date": str(data.index[-1].date()),
            "is_breakout": at_breakout,
            "resistance_level": nearest_res["level"],
            "volume_ratio": round(lvol / avg_vol, 2),
            "tr_contraction_pct": round((1 - last5_tr / prev20_tr) * 100, 1),
        }

    except Exception as exc:  # noqa: BLE001
        print(f"[Engine2] {ticker}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parabola(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    return a * x**2 + b * x + c


def _prep(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    data = df.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = {"High", "Low", "Volume"}
    if not required.issubset(data.columns):
        return None
    return data


def _adj_col(df: pd.DataFrame) -> str:
    return "Adj Close" if "Adj Close" in df.columns else "Close"
