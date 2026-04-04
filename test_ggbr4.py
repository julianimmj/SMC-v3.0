import yfinance as yf
from screener_logic import detect_smc_signals
import pandas as pd

df = yf.download('GGBR4.SA', period='2y', interval='1d', auto_adjust=True, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df.dropna(inplace=True)
df.reset_index(inplace=True)
if 'Date' not in df.columns and 'Datetime' in df.columns:
    df.rename(columns={'Datetime': 'Date'}, inplace=True)
df.reset_index(drop=True, inplace=True)
df_analyzed = detect_smc_signals(df)
signals = df_analyzed[df_analyzed['signal'].notna()].tail(10)

print(f"Current Price (last row close): {df_analyzed['Close'].iloc[-1]}")
for idx, row in signals.iterrows():
    print(f"\nIDX: {idx}, Signal: {row['signal']}, Date: {row['Date']}, POI: {row['poi_price']}, SL: {row['sl_price']}, TP1: {row['tp1_price']}")
    if row['signal'] == 'bull':
        lowest = df_analyzed.loc[idx:, 'Low'].min()
        print(f"  Lowest since signal: {lowest}")
        print(f"  Did it hit SL? {lowest <= row['sl_price']}")
    elif row['signal'] == 'bear':
        highest = df_analyzed.loc[idx:, 'High'].max()
        print(f"  Highest since signal: {highest}")
        print(f"  Did it hit SL? {highest >= row['sl_price']}")
