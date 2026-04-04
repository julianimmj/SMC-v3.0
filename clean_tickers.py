import pandas as pd
import yfinance as yf
import re

df = pd.read_csv('tickers_b3.csv')
tickers = [x + '.SA' for x in df['ticker']]
print(f"Original tickers: {len(tickers)}")

# Fetch data for 5 days
data = yf.download(tickers, period='5d', group_by='ticker', progress=False)

valid_tickers = []
invalid_tickers = []

for ticker in tickers:
    try:
        if len(tickers) > 1 and ticker in data.columns.levels[0]:
            ticker_data = data[ticker]
        elif len(tickers) == 1:
            ticker_data = data
        else:
            ticker_data = pd.DataFrame()
            
        if ticker_data.empty or len(ticker_data.dropna()) == 0:
            invalid_tickers.append(ticker)
        else:
            valid_tickers.append(ticker)
    except:
        invalid_tickers.append(ticker)
        
print(f"Invalid: {len(invalid_tickers)} -> {invalid_tickers}")
print(f"Valid: {len(valid_tickers)}")

# Rewrite CSV with valid
clean_list = [x.replace('.SA', '') for x in valid_tickers]
clean_df = df[df['ticker'].isin(clean_list)]
clean_df.to_csv('tickers_b3.csv', index=False)
print("Saved clean tickers_b3.csv!")
