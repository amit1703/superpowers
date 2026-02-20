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
