"""Tests for universe_builder.py — SEC fetch, pattern filter, save/load, price/volume filter."""

import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from universe_builder import (
    fetch_sec_tickers,
    filter_price_volume,
    filter_ticker_patterns,
    load_universe,
    save_universe,
)


# ---------------------------------------------------------------------------
# TestFetchSecTickers
# ---------------------------------------------------------------------------


class TestFetchSecTickers:
    """Tests for fetch_sec_tickers (uses mocked _fetch_sec_json)."""

    @patch("universe_builder._fetch_sec_json")
    def test_parses_sec_json_format(self, mock_fetch):
        """Mock _fetch_sec_json to return sample data, verify DataFrame."""
        mock_fetch.return_value = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [
                [320193, "Apple Inc.", "AAPL", "Nasdaq"],
                [789019, "Microsoft Corp", "MSFT", "Nasdaq"],
                [1018724, "Amazon.com Inc.", "AMZN", "Nasdaq"],
            ],
        }
        df = fetch_sec_tickers()

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["cik", "name", "ticker", "exchange"]
        assert len(df) == 3
        assert "AAPL" in df["ticker"].values
        assert "MSFT" in df["ticker"].values
        assert "AMZN" in df["ticker"].values

    @patch("universe_builder._fetch_sec_json")
    def test_filters_to_nyse_nasdaq_only(self, mock_fetch):
        """Pass mixed exchanges, verify only NYSE/Nasdaq remain."""
        mock_fetch.return_value = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [
                [320193, "Apple Inc.", "AAPL", "Nasdaq"],
                [51143, "International Business Machines", "IBM", "NYSE"],
                [1234, "SomeOTC Corp", "OTCX", "OTC"],
                [5678, "SomeBats Corp", "BATS", "BATS"],
                [9999, "CboeCorp", "CBOE", "CBOE"],
            ],
        }
        df = fetch_sec_tickers()

        assert len(df) == 2
        assert set(df["ticker"].values) == {"AAPL", "IBM"}
        assert set(df["exchange"].values) == {"Nasdaq", "NYSE"}

    @patch("universe_builder._fetch_sec_json")
    def test_handles_sec_api_failure(self, mock_fetch):
        """Mock _fetch_sec_json to raise, verify empty DataFrame returned."""
        mock_fetch.side_effect = Exception("Network error")

        df = fetch_sec_tickers()

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["cik", "name", "ticker", "exchange"]
        assert len(df) == 0


# ---------------------------------------------------------------------------
# TestFilterTickerPatterns
# ---------------------------------------------------------------------------


class TestFilterTickerPatterns:
    """Tests for filter_ticker_patterns."""

    def test_excludes_warrants(self):
        result = filter_ticker_patterns(["AAPL", "SPKEW", "ACAHW"])
        assert result == ["AAPL"]

    def test_excludes_preferred(self):
        result = filter_ticker_patterns(["BAC", "BAC-PB", "WFC-PL", "JPM"])
        assert result == ["BAC", "JPM"]

    def test_excludes_long_tickers(self):
        result = filter_ticker_patterns(["AAPL", "ABCDEF", "LONGTICKERZ"])
        assert result == ["AAPL"]

    def test_preserves_valid_tickers(self):
        result = filter_ticker_patterns(["A", "GE", "AMD", "NVDA", "BRK.B"])
        assert result == ["A", "GE", "AMD", "NVDA", "BRK-B"]

    def test_preserves_single_letter_W(self):
        """'W' (Wayfair) should NOT be excluded — only multi-char tickers ending in W."""
        result = filter_ticker_patterns(["W", "AAPL", "TESTW"])
        assert "W" in result
        assert "AAPL" in result
        assert "TESTW" not in result

    def test_excludes_rights_and_units(self):
        result = filter_ticker_patterns(["AAPL", "FOO-R", "BAR-RT", "BAZ-U"])
        assert result == ["AAPL"]

    def test_excludes_known_etfs(self):
        result = filter_ticker_patterns(["SPY", "QQQ", "AAPL", "TQQQ", "MSFT"])
        assert result == ["AAPL", "MSFT"]

    def test_normalises_dots_to_dashes(self):
        result = filter_ticker_patterns(["BRK.B"])
        assert result == ["BRK-B"]


# ---------------------------------------------------------------------------
# TestSaveLoadUniverse
# ---------------------------------------------------------------------------


class TestSaveLoadUniverse:
    """Tests for save_universe and load_universe."""

    def test_save_creates_valid_json(self, tmp_path):
        filepath = str(tmp_path / "universe.json")
        universe = {
            "tickers": ["AAPL", "MSFT", "GOOG"],
            "sectors": {"AAPL": "Technology", "MSFT": "Technology", "GOOG": "Communication Services"},
            "updated": "2026-02-21",
        }
        save_universe(universe, filepath)

        with open(filepath, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        assert loaded == universe

    def test_load_returns_tickers_and_sectors(self, tmp_path):
        filepath = str(tmp_path / "universe.json")
        universe = {
            "tickers": ["AAPL", "MSFT"],
            "sectors": {"AAPL": "Technology", "MSFT": "Technology"},
        }
        save_universe(universe, filepath)

        result = load_universe(filepath)
        assert result is not None
        tickers, sectors = result
        assert tickers == ["AAPL", "MSFT"]
        assert sectors == {"AAPL": "Technology", "MSFT": "Technology"}

    def test_load_returns_none_on_missing_file(self):
        result = load_universe("/nonexistent/path/universe.json")
        assert result is None

    def test_load_returns_none_on_corrupt_json(self, tmp_path):
        filepath = str(tmp_path / "corrupt.json")
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write("{this is not valid json!!!")
        result = load_universe(filepath)
        assert result is None


# ---------------------------------------------------------------------------
# Helper to build a single-ticker DataFrame (flat columns, as yfinance
# returns for a single-ticker download)
# ---------------------------------------------------------------------------


def _make_single_ticker_df(
    close: float = 150.0,
    volume: int = 2_000_000,
    rows: int = 60,
) -> pd.DataFrame:
    """Return a flat-column DataFrame mimicking ``yf.download`` for one ticker."""
    idx = pd.date_range("2025-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.01,
            "Low": close * 0.98,
            "Close": close,
            "Adj Close": close,
            "Volume": volume,
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# TestFilterPriceVolume
# ---------------------------------------------------------------------------


class TestFilterPriceVolume:
    """Tests for filter_price_volume (mocks yf.download)."""

    @patch("universe_builder.time.sleep")  # don't actually sleep in tests
    @patch("universe_builder.yf.download")
    def test_filters_below_min_price(self, mock_download, _mock_sleep):
        """Ticker with close=$5 should be excluded by the price filter."""
        mock_download.return_value = _make_single_ticker_df(close=5.0, volume=1_000_000)

        result = filter_price_volume(["PENNY"], min_price=10.0)

        assert "PENNY" not in result
        assert result == []

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_filters_below_min_volume(self, mock_download, _mock_sleep):
        """Ticker with vol=100K should be excluded by the volume filter."""
        mock_download.return_value = _make_single_ticker_df(close=50.0, volume=100_000)

        result = filter_price_volume(["ILLIQUID"], min_price=10.0, min_avg_volume=500_000)

        assert "ILLIQUID" not in result
        assert result == []

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_passes_valid_ticker(self, mock_download, _mock_sleep):
        """Ticker with close=$150 and vol=2M should pass both filters."""
        mock_download.return_value = _make_single_ticker_df(close=150.0, volume=2_000_000)

        result = filter_price_volume(["GOOD"], min_price=10.0, min_avg_volume=500_000)

        assert result == ["GOOD"]

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_handles_failed_download(self, mock_download, _mock_sleep):
        """Empty DataFrame from yf.download should not crash."""
        mock_download.return_value = pd.DataFrame()

        result = filter_price_volume(["BAD"])

        assert result == []

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_handles_single_ticker_batch(self, mock_download, _mock_sleep):
        """Single ticker produces flat (non-MultiIndex) columns — must work."""
        df = _make_single_ticker_df(close=200.0, volume=3_000_000)
        # Confirm it is indeed flat columns (no MultiIndex)
        assert not isinstance(df.columns, pd.MultiIndex)
        mock_download.return_value = df

        result = filter_price_volume(["SOLO"])

        assert result == ["SOLO"]

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_skips_ticker_with_too_few_rows(self, mock_download, _mock_sleep):
        """Ticker with fewer than 10 rows of data should be skipped."""
        mock_download.return_value = _make_single_ticker_df(close=100.0, volume=1_000_000, rows=5)

        result = filter_price_volume(["SHORT"])

        assert result == []

    @patch("universe_builder.time.sleep")
    @patch("universe_builder.yf.download")
    def test_exception_in_download_skips_batch(self, mock_download, _mock_sleep):
        """If yf.download raises an exception, the batch is skipped gracefully."""
        mock_download.side_effect = Exception("Network timeout")

        result = filter_price_volume(["CRASH"])

        assert result == []
