"""
universe_builder.py — SEC fetch + pattern filter + save/load

Builds a tradeable universe by fetching tickers from SEC,
filtering out warrants/preferred/ETFs, and persisting results.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

UNIVERSE_FILE = "active_universe.json"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_USER_AGENT = "SwingTradingDashboard admin@example.com"
DEFAULT_MIN_PRICE = 10.0
DEFAULT_MIN_AVG_VOLUME = 500_000
BATCH_SIZE = 100
BATCH_DELAY = 2.0
SECTOR_BATCH_SIZE = 50
SECTOR_BATCH_DELAY = 3.0

KNOWN_ETFS = frozenset({
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "IVV", "VEA", "VWO", "EFA",
    "AGG", "BND", "TLT", "GLD", "SLV", "USO", "XLF", "XLK", "XLE", "XLV",
    "XLY", "XLP", "XLI", "XLB", "XLRE", "XLU", "XLC", "ARKK", "ARKW",
    "ARKF", "ARKG", "ARKQ", "SQQQ", "TQQQ", "SPXU", "SOXL", "SOXS",
    "UVXY", "SVXY", "VXX", "VIXY", "HYG", "LQD", "IEMG", "EEM",
})

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SEC fetch helpers
# ---------------------------------------------------------------------------


def _fetch_sec_json() -> dict:
    """Fetch company tickers JSON from the SEC EDGAR API.

    Returns a dict with ``fields`` and ``data`` arrays as provided by the SEC.
    """
    req = urllib.request.Request(
        SEC_TICKERS_URL,
        headers={"User-Agent": SEC_USER_AGENT},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_sec_tickers() -> pd.DataFrame:
    """Return a DataFrame of NYSE/Nasdaq tickers from the SEC.

    Columns: ``[cik, name, ticker, exchange]``.
    On any failure an empty DataFrame with those columns is returned.
    """
    columns = ["cik", "name", "ticker", "exchange"]
    try:
        raw = _fetch_sec_json()
        df = pd.DataFrame(raw["data"], columns=raw["fields"])
        # Rename columns to our standard names if needed
        # SEC JSON fields are: [cik, name, ticker, exchange]
        df.columns = columns
        df = df[df["exchange"].isin({"NYSE", "Nasdaq"})]
        df = df.drop_duplicates(subset="ticker", keep="first")
        df = df.reset_index(drop=True)
        return df
    except Exception:
        logger.exception("Failed to fetch SEC tickers")
        return pd.DataFrame(columns=columns)


# ---------------------------------------------------------------------------
# Ticker pattern filtering
# ---------------------------------------------------------------------------


def filter_ticker_patterns(tickers: List[str]) -> List[str]:
    """Filter out warrants, preferred shares, rights/units, ETFs, and long tickers.

    Also normalises dots to dashes (e.g. ``BRK.B`` becomes ``BRK-B``).
    """
    # Regex for preferred shares: contains -P optionally followed by one letter
    preferred_re = re.compile(r"-P[A-Z]?$")
    # Regex for rights/units: ends with -R, -RT, or -U
    rights_units_re = re.compile(r"-(R|RT|U)$")

    result: List[str] = []
    for raw_ticker in tickers:
        # Normalise dots to dashes
        ticker = raw_ticker.replace(".", "-")

        # Exclude known ETFs
        if ticker in KNOWN_ETFS:
            continue

        # Exclude warrants: multi-char tickers ending with W or WS
        if len(ticker) > 1 and (ticker.endswith("WS") or ticker.endswith("W")):
            # But check WS first so that e.g. "FOOWS" is caught by WS branch
            # and "FOOW" is caught by W branch.  Single-letter "W" is preserved.
            continue

        # Exclude preferred shares
        if preferred_re.search(ticker):
            continue

        # Exclude rights / units
        if rights_units_re.search(ticker):
            continue

        # Exclude long tickers: base length (without dashes) > 5
        base = ticker.replace("-", "")
        if len(base) > 5:
            continue

        result.append(ticker)
    return result


# ---------------------------------------------------------------------------
# Universe persistence
# ---------------------------------------------------------------------------


def save_universe(universe: dict, filepath: str = UNIVERSE_FILE) -> None:
    """Write *universe* dict to *filepath* as pretty-printed JSON."""
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(universe, fh, indent=2)


def load_universe(
    filepath: str = UNIVERSE_FILE,
) -> Optional[Tuple[List[str], Dict[str, str]]]:
    """Load a previously saved universe file.

    Returns ``(tickers, sectors)`` on success, or ``None`` when the file is
    missing or contains invalid JSON.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return (data["tickers"], data["sectors"])
    except FileNotFoundError:
        logger.warning("Universe file not found: %s", filepath)
        return None
    except json.JSONDecodeError:
        logger.warning("Corrupt universe file: %s", filepath)
        return None


# ---------------------------------------------------------------------------
# Stub functions (to be implemented in later tasks)
# ---------------------------------------------------------------------------


def filter_price_volume(
    tickers: List[str],
    min_price: float = DEFAULT_MIN_PRICE,
    min_avg_volume: int = DEFAULT_MIN_AVG_VOLUME,
) -> List[str]:
    """Filter tickers by minimum price and average volume.

    Stub — returns an empty list.  Full implementation in a later task.
    """
    return []


def build_sector_map(tickers: List[str]) -> Dict[str, str]:
    """Build a mapping of ticker -> GICS sector.

    Stub — returns an empty dict.  Full implementation in a later task.
    """
    return {}


def build_universe() -> Optional[dict]:
    """Orchestrate the full universe-building pipeline.

    Stub — returns ``None``.  Full implementation in a later task.
    """
    return None
