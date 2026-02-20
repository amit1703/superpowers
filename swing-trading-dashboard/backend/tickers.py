"""
Ticker universe for scanning.
Combined S&P 500 + Russell 1000 — approximately 700 unique tickers.
Deduplicated; update periodically as index constituents change.
"""

# ── S&P 500 ────────────────────────────────────────────────────────────────
SP500 = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AVGO", "GOOGL", "GOOG",
    # Retail / Consumer Discretionary
    "COST", "NFLX", "LULU", "SBUX", "ORLY", "ROST", "DLTR", "KDP", "MDLZ",
    "MNST", "MCD", "YUM", "DPZ", "CMG", "NKE", "TJX", "BBY", "DG", "WMT",
    "TGT", "HD", "LOW", "F", "GM", "TSCO", "AZO", "ULTA", "DECK", "HAS",
    "MAT", "PVH", "RL", "TPR", "VFC", "LKQ", "GPC", "LEA",
    # Semiconductors
    "AMD", "QCOM", "AMAT", "MU", "LRCX", "KLAC", "MRVL", "ADI", "MCHP",
    "NXPI", "ON", "INTC", "TXN", "MPWR", "SWKS", "QRVO", "ENTG", "COHR",
    "MKSI", "ACLS", "ONTO", "WOLF",
    # Software / Cloud / SaaS
    "ADBE", "INTU", "PANW", "SNPS", "CDNS", "CRWD", "WDAY", "ZS", "TEAM",
    "DDOG", "FTNT", "SPLK", "TTD", "NOW", "CRM", "SAP", "ORCL", "IBM",
    "CTSH", "ACN", "EPAM", "GLOB", "LDOS", "SAIC", "CACI", "VRSK",
    # Biotech / Pharma / MedTech
    "AMGN", "REGN", "GILD", "BIIB", "VRTX", "MRNA", "IDXX", "DXCM", "ALGN",
    "ABT", "MDT", "SYK", "BSX", "EW", "HOLX", "ISRG", "RMD", "PODD", "NVST",
    "HSIC", "TECH", "XRAY", "ZBH", "TFX", "ABMD", "HAE",
    # Pharma / Large-cap
    "LLY", "JNJ", "PFE", "MRK", "ABBV", "BMY", "ZTS", "VTRS", "PBH",
    # Healthcare Services / Managed Care
    "UNH", "CVS", "CI", "HUM", "CNC", "MOH", "ELV", "DVA", "HCA", "THC",
    "UHS", "ENSG", "ADUS", "NHC",
    # Telecom
    "TMUS", "VZ", "T", "CHTR", "SIRI",
    # Media / Entertainment
    "DIS", "CMCSA", "FOX", "FOXA", "NWSA", "NWS", "EA", "TTWO", "ATVI",
    "LYV", "PARA", "WBD",
    # Industrials / Aerospace / Defense
    "HON", "BA", "RTX", "LMT", "NOC", "GD", "L3T", "HII", "TDG", "AXON",
    "GE", "MMM", "EMR", "ITW", "PH", "ROK", "DOV", "AME", "FTV", "GNRC",
    "XYL", "IDEX", "RRX", "CSGP",
    # Transport / Logistics
    "UPS", "FDX", "ODFL", "SAIA", "JBHT", "CHRW", "EXPD", "XPO", "UBER",
    "LYFT", "CPRT", "CTAS", "PCAR", "FAST", "MSCI", "NFG",
    # Energy
    "XOM", "CVX", "COP", "OXY", "EOG", "SLB", "HAL", "BKR", "DVN", "FANG",
    "MPC", "VLO", "PSX", "PXD", "HES", "APA", "CVI", "MTDR", "SM", "CPE",
    "CTRA", "KMI", "WMB", "OKE", "ET", "TRGP", "ENLC",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "XEL", "SRE", "PCG", "EIX", "AWK",
    "ES", "CMS", "NI", "AES", "ETR", "EXC", "CEG", "PPL", "LNT", "EVRG",
    "WTRG", "SWX", "OGE", "POR", "AVA", "NWE", "FSLR", "ENPH", "SEDG",
    # Real Estate / REITs
    "AMT", "PLD", "EQIX", "CCI", "SPG", "O", "VICI", "WPC", "IRM", "PSA",
    "EXR", "AVB", "EQR", "ESS", "UDR", "CPT", "NXR", "MAA", "NNN", "STAG",
    "REXR", "FR", "DRE", "PEAK", "HR", "DOC", "MPW", "SBAC", "AMH",
    "INVH", "SUI", "ELS", "UE",
    # Financials — Banks
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "TFC", "PNC", "KEY",
    "CFG", "HBAN", "RF", "FITB", "MTB", "ZION", "CMA", "SBNY", "WAL",
    "WTFC", "PVTB", "BOKF", "CADE", "IBOC",
    # Financials — Insurance / Asset Mgmt
    "BRK-B", "CB", "AIG", "MET", "PRU", "PGR", "TRV", "AFL", "ALL", "HIG",
    "CNA", "LNC", "FG", "UNM", "EQH", "BEN", "IVZ", "AMG", "TROW", "BLK",
    "STT", "BK", "NTRS", "FIS", "FISV", "GPN", "PYPL", "MA", "V",
    # Fintech / Payments
    "SQ", "COIN", "HOOD", "SOFI", "AFRM", "UPST", "LC",
    # Consumer Staples
    "PG", "KO", "PEP", "PM", "MO", "KVUE", "STZ", "TAP", "BUD", "SAM",
    "CHD", "CLX", "CL", "EPC", "HELE", "SPB", "ENR", "KMB",
    # Materials / Chemicals
    "LIN", "APD", "DD", "DOW", "CTVA", "FMC", "CE", "OLN", "EMN", "HUN",
    "CC", "TROX", "HWKN", "IOSP", "KWR", "CBT", "KALU", "AA", "NUE",
    "STLD", "RS", "CMC", "WOR", "ATI", "AKS", "CLF", "MT", "FCX", "NEM",
    "AEM", "GOLD", "KGC", "AG", "PAAS", "HL", "CDE", "WPM", "FNV",
    # Diversified / Conglomerate
    "MMC", "AON", "WTW", "BURL", "SPGI", "MCO", "ICE", "CBOE", "CME",
    "NDAQ", "MKTX", "MSCI",
    # E-commerce / Internet
    "EBAY", "ETSY", "W", "CHWY", "OSTK", "PRTS", "REAL",
    # Travel / Hospitality
    "ABNB", "BKNG", "EXPE", "TRIP", "HLT", "MAR", "H", "IHG", "WH",
    "CCL", "RCL", "NCLH", "DAL", "UAL", "AAL", "LUV", "ALK", "JBLU",
    # Auto / EV
    "TSLA", "RIVN", "LCID", "F", "GM", "STLA", "TM", "HMC",
    # High-growth emerging
    "PLTR", "SNOW", "RBLX", "ROKU", "PINS", "DKNG", "ZM", "BILL", "HUBS",
    "PCTY", "PAYC", "VEEV", "DOCU", "COUP", "SMAR", "BOX", "QLYS", "SAIL",
    # International large-cap ADRs
    "MELI", "PDD", "ASML", "TSM", "BABA", "JD", "NIO", "XPEV", "LI",
    "SE", "GRAB", "VALE", "RIO", "BHP", "TTE", "BP", "SHEL", "E",
    # Diversified Tech
    "CSCO", "ANET", "JNPR", "NTAP", "PSTG", "EQIX", "WDC", "STX", "SMCI",
    "HPE", "HPQ", "DELL", "LOGI", "ZBRA", "TER", "KEYS", "GRMN", "FLEX",
    "JABIL", "CXM",
    # Managed Services / IT Services
    "ADP", "PAYX", "CDW", "CDNS", "TTEC", "MAXN", "PRFT", "EXLS",
    # Additional S&P 500 names
    "MTD", "A", "WAT", "BIO", "TMO", "DHR", "IQV", "CRL", "ICLR", "MEDP",
    "CRVL", "PRGO", "CTLT", "AVTR", "PKI", "NTRA", "GH", "EXAS", "VEEV",
    "FATE", "BEAM", "EDIT", "NTLA", "CRSP",
]

# ── Russell 1000 additions (not already in S&P 500) ───────────────────────
RUSSELL1000_EXTRA = [
    # Mid-cap growth tech
    "OKTA", "ZI", "GTLB", "CFLT", "MDB", "NET", "ESTC", "APPN", "ALTR",
    "INST", "BLKB", "ALTR", "TOST", "RELY", "ASAN", "MNDY", "FRSH",
    # Cybersecurity
    "S", "TENB", "VRNS", "CHKP", "CYBR", "QLYS", "OSPN", "RPD",
    # Data / Analytics
    "CLDR", "DOMO", "SPSC", "POWI", "AZPN", "SMAR", "FIVN", "NICE",
    # Healthcare / Biotech mid-cap
    "INCY", "HALO", "EXEL", "KITE", "PTCT", "RARE", "FOLD", "ACAD",
    "RCKT", "ARCT", "BDTX", "PRAX", "NUVL", "RVMD", "PTGX", "STOK",
    "IMVT", "KYMR", "RLAY", "VERA", "ALLO", "IMMU", "CLDX", "DNLI",
    # MedTech mid-cap
    "NVCR", "INSP", "TNDM", "IRTC", "ONEM", "HIMS", "SDGR", "RXRX",
    # Financials mid-cap
    "LBAI", "FFIN", "IBTX", "SFNC", "CVBF", "TCBI", "WSFS", "BANF",
    "EWBC", "PPBI", "WABC", "FULT", "UMBF", "VBTX", "FRST",
    # Insurance mid-cap
    "KMPR", "RLI", "SIGI", "ARGO", "SKWD", "KINGSWAY",
    # Energy mid-cap
    "CHRD", "VTLE", "CRC", "NOG", "TALO", "PR", "BATL", "SWN", "AR",
    "RRC", "EQT", "CNX", "COG", "GPOR",
    # Industrials mid-cap
    "AZEK", "IBP", "SITE", "BLDR", "FBM", "BECN", "GMS", "PGTI",
    "CSL", "ESAB", "GNSS", "RXO", "GXO", "DSGR", "AIRC", "DCP",
    "MATX", "HUBG", "MRTN", "PTSI", "ARCB", "WERN", "HTLD", "USX",
    # Consumer mid-cap
    "BOOT", "FIVE", "OLLI", "PSMT", "PRPB", "DXPE", "MMS", "TMUS",
    "HIBB", "BIG", "WSM", "RH", "ARHAUS", "LOVE", "KIRK", "CATO",
    "PRPL", "SNBR", "CSPR", "LESL", "POOL", "PATK", "WGO", "THO",
    "CWH", "MCBC", "BC", "MBUU",
    # Real estate / Homebuilders
    "DHI", "LEN", "PHM", "TOL", "MTH", "MDC", "LGIH", "SKY", "CVCO",
    "SSD", "TREX", "FBIN", "MAS", "FBHS", "ALLE", "ACCO",
    # Specialty retail
    "AMZN", "CHWY", "PETS", "FRPT", "CENT", "ANDE",
    # Media / Publishing mid-cap
    "NYT", "GCI", "LEE", "MDP", "SSP", "NXST", "GTN", "SBGI",
    # Diversified mid-cap
    "HRB", "JEF", "LAZ", "VRTS", "STEP", "GCMG", "HLNE", "CASS",
    "WSBC", "IBCP", "NBTB", "NCOM", "ESSA", "HTBK",
    # Agriculture / Specialty Chemicals
    "MON", "CTVA", "AGCO", "CF", "MOS", "NTR", "SMG", "SHW", "PPG",
    "RPM", "AXTA", "KWR", "IOSP",
    # Healthcare services
    "AMED", "LHCG", "SGRY", "ASAN", "ACMR", "HCSG", "PNTG", "OPCH",
    "EVDY", "GDRX", "PHVAR", "CERT",
    # Additional high-growth
    "APP", "TTD", "MGNI", "TPVG", "DSP", "IAS", "BMBL", "MTCH",
    "IAC", "ANGI", "CARS", "CARG", "TDC", "OPEN", "RDFN", "COMP",
    "UWMC", "RKT", "PFSI", "GHLD", "HMST", "RATE",
    # Clean energy / EV infrastructure
    "PLUG", "BLNK", "EVGO", "CHPT", "NKLA", "HYLN", "WKHS", "RIDE",
    "GOEV", "FSR", "SOLO", "XPEV",
    # Streaming / Content
    "SPOT", "AMCX", "FUBO", "SLING", "CURI",
    # Biotech / Gene editing additional
    "IONS", "BIIB", "ALKS", "ACAD", "SAGE", "AXSM", "JAZZ", "ITCI",
    "PTCT", "SRPT", "MNKD", "AGEN",
    # Software additional
    "MIME", "EVTC", "TLIS", "SMAR", "ALRM", "FSLY", "DDOG", "LPSN",
    "REAL", "POSH", "FROG", "SQSP",
    # Semiconductors additional (fabless, equipment)
    "FORM", "ACMR", "AMKR", "ICHR", "KLIC", "CREE", "AMBA", "SLAB",
    "DIOD", "IXYS", "SMTC", "AEIS", "RMBS", "POWI",
]

# ── Combined deduplicated scan universe ─────────────────────────────────────
# dict.fromkeys preserves order and deduplicates
SCAN_UNIVERSE: list[str] = list(dict.fromkeys(SP500 + RUSSELL1000_EXTRA))
