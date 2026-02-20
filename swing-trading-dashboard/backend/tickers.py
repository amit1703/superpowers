"""
Ticker universe for scanning.
Default: Nasdaq 100 components (update periodically as index changes).
"""

NASDAQ_100 = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AVGO", "GOOGL", "GOOG",
    # Retail / Consumer
    "COST", "NFLX", "LULU", "SBUX", "ORLY", "ROST", "DLTR", "KDP", "MDLZ", "MNST",
    # Semiconductors
    "AMD", "QCOM", "AMAT", "MU", "LRCX", "KLAC", "MRVL", "ADI", "MCHP", "NXPI",
    "ON", "GFS", "INTC",
    # Software / Cloud
    "ADBE", "INTU", "PANW", "SNPS", "CDNS", "CRWD", "WDAY", "ZS", "TEAM", "DDOG",
    "OKTA", "ANSS", "VRSK", "FTNT", "SPLK", "TTD",
    # Biotech / Pharma
    "AMGN", "REGN", "GILD", "BIIB", "VRTX", "MRNA", "IDXX", "DXCM", "ALGN",
    # Telecom / Media
    "TMUS", "CHTR", "SIRI", "EA",
    # Industrials / Other
    "HON", "TXN", "CSCO", "ADP", "PAYX", "CTAS", "PCAR", "FAST", "ODFL", "CPRT",
    # Energy / Utilities
    "CEG", "EXC", "AEP", "XEL", "FSLR",
    # Financial / Fintech
    "PYPL", "ABNB",
    # Emerging / High-growth
    "MELI", "PDD", "ASML",
    # Healthcare
    "ISRG",
    # Additional Nasdaq growth names
    "COIN", "PLTR", "SNOW", "RBLX", "ROKU", "PINS", "HOOD", "DKNG", "ENPH", "ZM",
    "EBAY", "CTSH", "FANG", "GEHC", "RIVN",
]

# Alias used by main.py
SCAN_UNIVERSE: list[str] = NASDAQ_100
