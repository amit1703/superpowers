"""Tests for Engine 5: Base Pattern Scanner."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import pytest

from engines.engine5 import (
    _find_cup,
    _is_u_shaped,
    _find_handle,
    _quality_score,
    scan_cup_handle,
    scan_flat_base,
    scan_base_pattern,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_cup_handle_df(n_total=110, cup_depth=0.20, handle_pct=0.08):
    """
    Build a synthetic DataFrame with a clear cup & handle pattern.
    Structure: 30 bars uptrend → 40-bar cup → 40-bar recovery → 20-bar handle → 20 bars near pivot
    """
    dates = pd.date_range("2025-01-01", periods=n_total, freq="B")

    close = np.ones(n_total) * 100.0
    # Uptrend into left peak
    for i in range(30):
        close[i] = 90 + i * 0.5          # ramp from 90 to 104.5
    left_peak = close[29]                 # ~104.5

    # Cup: half-sine dip
    for i in range(40):
        angle = np.pi * i / 39
        close[30 + i] = left_peak - cup_depth * left_peak * np.sin(angle)

    right_rim = close[69]                 # should be close to left_peak

    # Handle: small drift down
    for i in range(20):
        t = i / 19
        close[70 + i] = right_rim - handle_pct * right_rim * np.sin(np.pi * t)

    # Near pivot (last 20 bars drift up toward right_rim)
    for i in range(20):
        close[90 + i] = right_rim * 0.99 + i * 0.01

    high = close * 1.01
    low = close * 0.99
    volume = np.full(n_total, 1_000_000.0)
    volume[70:90] = 600_000.0   # dry-up in handle
    volume[-1] = 1_000_000.0

    df = pd.DataFrame({
        "Close": close,
        "High": high,
        "Low": low,
        "Open": close * 0.995,
        "Volume": volume,
    }, index=dates)
    return df


def make_flat_base_df(n_total=100, base_depth=0.08, base_days=35):
    """Build a synthetic DataFrame with a flat base at the end."""
    dates = pd.date_range("2025-01-01", periods=n_total, freq="B")

    close = np.ones(n_total) * 100.0
    trend_bars = n_total - base_days
    for i in range(trend_bars):
        close[i] = 80 + i * (20.0 / trend_bars)

    base_start = close[trend_bars - 1]
    for i in range(base_days):
        t = i / base_days
        close[trend_bars + i] = base_start * (1 - base_depth * 0.25 * np.sin(2 * np.pi * t))

    close[-1] = base_start * 0.996

    high = close * 1.005
    low = close * 0.995
    volume = np.full(n_total, 1_000_000.0)
    volume[trend_bars:] = 700_000.0   # contraction in base

    df = pd.DataFrame({
        "Close": close,
        "High": high,
        "Low": low,
        "Open": close * 0.998,
        "Volume": volume,
    }, index=dates)
    return df
