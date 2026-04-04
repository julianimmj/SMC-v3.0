import yfinance as yf
from screener_logic import detect_smc_signals
from app import build_chart
import traceback

try:
    df = yf.Ticker('PETR4.SA').history(period='6mo', interval='1d', auto_adjust=True)
    df.reset_index(inplace=True)
    if 'Date' not in df.columns and 'Datetime' in df.columns:
        df.rename(columns={'Datetime': 'Date'}, inplace=True)
    df_analyzed = detect_smc_signals(df)
    fig = build_chart(df_analyzed, 'PETR4')
    print('Chart OK')
except Exception as e:
    traceback.print_exc()
