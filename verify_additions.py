import yfinance as yf

candidates = [
    # ETFs
    "BOVA11", "IVVB11", "SMAL11", "HASH11", "NASD11",
    # BDRs
    "ROXO34", "MELI34", "MCOA34", "AAPL34", "AMZO34", "MSFT34", 
    "GOGL34", "META34", "TSLA34", "NVDC34", "NFLX34", "DISB34",
    # FIIs
    "IRDM11", "VILG11", "HGRU11", "ALZR11", "XPIN11", 
    # Stocks
    "CXSE3", "CMIN3", "VAMO3", "MATD3"
]

valid = []
invalid = []

for c in candidates:
    ticker = c + ".SA"
    try:
        data = yf.download(ticker, period="5d", progress=False)
        if not data.empty and not data['Close'].dropna().empty:
            valid.append(c)
        else:
            invalid.append(c)
    except Exception:
        invalid.append(c)

print("Valid Additions:", valid)
print("Invalid Additions:", invalid)
