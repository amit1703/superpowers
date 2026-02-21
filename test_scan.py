#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, 'swing-trading-dashboard/backend')

from main import _run_scan
from datetime import datetime

async def test():
    scan_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tickers = ['CREE', 'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']  # Include CREE to test
    print(f"Starting test scan at {scan_ts}...")
    await _run_scan(scan_ts, tickers)
    print("Scan completed successfully!")

asyncio.run(test())
