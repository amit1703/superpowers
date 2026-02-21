"""
Engine 0: Master Market Switch (Regime Filter)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rule: SPY Daily Close vs SPY 20-period EMA.
  - Close > 20 EMA  →  BULLISH  (Engines 2 & 3 enabled)
  - Close ≤ 20 EMA  →  BEARISH  (Engines 2 & 3 disabled — do not fight the trend)
"""

from typing import Dict

import pandas as pd
import yfinance as yf

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indicators import ema as _ema


def check_market_regime() -> Dict:
    """
    Fetch SPY daily data and determine the current market regime.

    Returns
    -------
    dict
        is_bullish : bool
        spy_close  : float
        spy_20ema  : float
        regime     : str  ("BULLISH" | "BEARISH" | "ERROR: ...")
    """
    try:
        spy = yf.download(
            "SPY",
            period="6mo",
            interval="1d",
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=False,
        )

        if spy.empty:
            return _error("No SPY data returned from yfinance")

        # Flatten MultiIndex columns (newer yfinance versions)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        close = spy["Adj Close"] if "Adj Close" in spy.columns else spy["Close"]
        close = close.dropna()

        if len(close) < 22:
            return _error(f"Insufficient SPY data: {len(close)} bars")

        ema20 = _ema(close, length=20)

        if ema20.empty or pd.isna(ema20.iloc[-1]):
            return _error("EMA-20 calculation failed")

        lc_val = close.iloc[-1]
        le_val = ema20.iloc[-1]
        latest_close = float(lc_val.item() if hasattr(lc_val, 'item') else lc_val)
        latest_ema20 = float(le_val.item() if hasattr(le_val, 'item') else le_val)
        is_bullish = latest_close > latest_ema20

        return {
            "is_bullish": is_bullish,
            "spy_close": round(latest_close, 2),
            "spy_20ema": round(latest_ema20, 2),
            "regime": "BULLISH" if is_bullish else "BEARISH",
        }

    except Exception as exc:  # noqa: BLE001
        return _error(str(exc)[:120])


def _error(msg: str) -> Dict:
    return {
        "is_bullish": False,
        "spy_close": 0.0,
        "spy_20ema": 0.0,
        "regime": f"ERROR: {msg}",
    }
