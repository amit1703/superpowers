"""
Native technical indicator implementations.
No external TA library required — pure pandas / numpy.
"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential Moving Average (Wilder/standard EWM)."""
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=length, min_periods=length).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """
    Average True Range (Wilder smoothing = EWM with alpha=1/length).
    Returns NaN for the first `length` bars.
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # Wilder smoothing
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Raw (un-smoothed) True Range."""
    prev_close = close.shift(1)
    return pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 20,
    constant: float = 0.015,
) -> pd.Series:
    """
    Commodity Channel Index.
    CCI = (Typical Price − SMA(TP, n)) / (constant × Mean Deviation)
    """
    tp = (high + low + close) / 3.0
    tp_sma = tp.rolling(window=length, min_periods=length).mean()
    mean_dev = tp.rolling(window=length, min_periods=length).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    # Avoid division by zero
    denom = constant * mean_dev
    denom = denom.replace(0, np.nan)
    return (tp - tp_sma) / denom
