"""
Engine 5: Base Pattern Scanner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detects two classic O'Neil/Minervini base patterns on the daily timeframe.

PATTERN A — Cup & Handle (C&H):
  1. Cup     : U-shaped consolidation, 12–35% depth, 30–120 bars
  2. Right rim: recovers to within 10% of left peak
  3. Handle  : 5–25 day pullback 5–15%, volume contracting
  4. Signal  : DRY (within 1.5% of handle high) or BRK (above, vol ≥ 120%)

PATTERN B — Flat Base (FLAT):
  1. Duration: ≥ 25 trading days
  2. Depth   : ≤ 15% from high to low of range
  3. Location: Close in upper 75% of range
  4. Volume  : 10-day avg ≤ 85% of 50-day avg
  5. Signal  : DRY (within 1.5% of base high) or BRK (above, vol ≥ 120%)

Quality Score (0–100):
  25 pts: RS vs SPY (3-month outperformance)
  25 pts: Base tightness (depth)
  25 pts: Volume dry-up (vs 50-day avg)
  25 pts: RS near 52-week high (blue dot signal)

Risk Math:
  Entry      = pivot_high × 1.001
  Stop Loss  = handle_low (C&H) or base_low (FLAT) − 0.2 × ATR14
  Take Profit= Entry + 2 × Risk   (1:2 R:R)
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indicators import atr as _atr


def scan_base_pattern(
    ticker: str,
    df: pd.DataFrame,
    spy_3m_return: float = 0.0,
    rs_ratio: float = 0.0,
    rs_52w_high: float = 0.0,
    rs_blue_dot: bool = False,
) -> Optional[Dict]:
    """Main entry point. Tries Cup & Handle first, then Flat Base.
    Returns the highest-quality setup found, or None."""
    raise NotImplementedError


def scan_cup_handle(
    ticker: str,
    df: pd.DataFrame,
    spy_3m_return: float = 0.0,
    rs_ratio: float = 0.0,
    rs_52w_high: float = 0.0,
    rs_blue_dot: bool = False,
) -> Optional[Dict]:
    """Scan for a Cup & Handle pattern. Returns setup dict or None."""
    raise NotImplementedError


def scan_flat_base(
    ticker: str,
    df: pd.DataFrame,
    spy_3m_return: float = 0.0,
    rs_ratio: float = 0.0,
    rs_52w_high: float = 0.0,
    rs_blue_dot: bool = False,
) -> Optional[Dict]:
    """Scan for a Flat Base pattern. Returns setup dict or None."""
    raise NotImplementedError


def _find_cup(close: np.ndarray, lookback: int = 120) -> Optional[Dict]:
    """Locate cup: left peak → cup bottom → right rim."""
    n = len(close)
    data = close[-lookback:] if n >= lookback else close
    if len(data) < 30:
        return None

    # Left peak: highest close in first 2/3 of window
    two_thirds = len(data) * 2 // 3
    left_search = data[:two_thirds]
    if len(left_search) < 10:
        return None

    left_peak_idx = int(np.argmax(left_search))
    left_peak = float(left_search[left_peak_idx])

    # Cup bottom: lowest close after left peak
    after_peak = data[left_peak_idx:]
    if len(after_peak) < 5:
        return None

    cup_bottom_rel = int(np.argmin(after_peak))
    cup_bottom_idx = left_peak_idx + cup_bottom_rel
    cup_bottom = float(data[cup_bottom_idx])

    # Cup depth validation: 12–35%
    depth = (left_peak - cup_bottom) / left_peak
    if depth < 0.12 or depth > 0.35:
        return None

    # Right rim: highest close after cup bottom
    after_bottom = data[cup_bottom_idx:]
    if len(after_bottom) < 5:
        return None

    right_rim_rel = int(np.argmax(after_bottom))
    right_rim_idx = cup_bottom_idx + right_rim_rel
    right_rim = float(data[right_rim_idx])

    # Right rim must recover to within 10% of left peak
    if (left_peak - right_rim) / left_peak > 0.10:
        return None

    # Cup must span at least 20 bars
    cup_length = right_rim_idx - left_peak_idx
    if cup_length < 20:
        return None

    return {
        "left_peak_idx": left_peak_idx,
        "left_peak": left_peak,
        "cup_bottom_idx": cup_bottom_idx,
        "cup_bottom": cup_bottom,
        "right_rim_idx": right_rim_idx,
        "right_rim": right_rim,
        "depth": depth,
        "cup_length": cup_length,
    }


def _is_u_shaped(close: np.ndarray, cup: Dict) -> bool:
    """Return True if cup region fits parabola with a > 0 (U-shape)."""
    try:
        start = cup["left_peak_idx"]
        end = cup["right_rim_idx"] + 1
        segment = close[start:end].astype(float)
        if len(segment) < 6:
            return False

        x = np.arange(len(segment), dtype=float)
        y = segment

        def parabola(x, a, b, c):
            return a * x ** 2 + b * x + c

        popt, _ = curve_fit(parabola, x, y, maxfev=3000)
        return float(popt[0]) > 0
    except Exception:
        return False


def _find_handle(
    close: np.ndarray,
    volume: np.ndarray,
    cup: Dict,
    vol_sma50: float,
) -> Optional[Dict]:
    """Find a valid 5–25 day handle after the cup rim."""
    rim_idx = cup["right_rim_idx"]
    right_rim = cup["right_rim"]
    cup_midpoint = (cup["left_peak"] + cup["cup_bottom"]) / 2.0

    after_rim = close[rim_idx:]
    if len(after_rim) < 6:
        return None

    # Search up to 25 days after the rim
    handle_window = after_rim[:26]
    handle_vols = volume[rim_idx: rim_idx + 26] if rim_idx + 26 <= len(volume) else volume[rim_idx:]

    # Find the lowest point in handle (skip the rim bar itself)
    search = handle_window[1:]
    if len(search) < 4:
        return None

    handle_low_rel = int(np.argmin(search))
    handle_low = float(search[handle_low_rel])
    handle_length = len(search)

    # Pullback: 5–15% from rim
    pullback = (right_rim - handle_low) / right_rim
    if pullback < 0.05 or pullback > 0.15:
        return None

    # Handle low must not undercut cup midpoint
    if handle_low < cup_midpoint:
        return None

    # Volume must contract in handle vs 50-day avg
    if vol_sma50 > 0 and len(handle_vols) >= 4:
        handle_avg_vol = float(np.mean(handle_vols[1:4]))
        if handle_avg_vol >= vol_sma50:
            return None

    return {
        "handle_high": right_rim,
        "handle_low": handle_low,
        "pullback_pct": pullback,
        "handle_length": handle_length,
    }


def _quality_score(
    depth_pct: float,
    max_depth_pct: float,
    vol_dry_pct: float,
    rs_vs_spy: float,
    rs_blue_dot: bool,
) -> int:
    """Compute quality score 0–100 from four equally-weighted factors."""
    raise NotImplementedError


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
