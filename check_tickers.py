import pandas as pd
import yfinance as yf
import time

df = pd.read_csv('tickers_b3.csv')
invalid_tickers = []
valid_tickers = []

print("Validando tickers com yfinance individualmente...")

# Pega todos unicos
tickers = [t for t in df['ticker'].unique() if pd.notna(t)]

for ticker in tickers:
    yf_t = ticker + ".SA"
    try:
        t = yf.Ticker(yf_t)
        hist = t.history(period="5d")
        if hist.empty:
            invalid_tickers.append(ticker)
        else:
            valid_tickers.append(ticker)
    except:
        invalid_tickers.append(ticker)
    time.sleep(0.1) # sleep to avoid rate limits

print(f"\nTickers Inválidos Encontrados ({len(invalid_tickers)}):")
for t in invalid_tickers:
    print(t)

with open('invalid_tickers.txt', 'w') as f:
    for t in invalid_tickers:
        f.write(t + "\n")
