"""
SMC Cloud Screener v3.0 - Complete Logic
Liquidity Sweeps + Strong Structures + BOS/CHOCH + Fibonacci + Order Blocks + FVG
"""

import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']


def download_data_batch(tickers: list, period: str = '2y', interval: str = '1d', max_workers: int = 20) -> dict:
    """Download data in parallel using ThreadPoolExecutor."""
    data = {}
    
    def download_ticker(ticker):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty:
                return ticker, None
            df = df[COLUMNS]
            df.columns = COLUMNS
            return ticker, df
        except Exception as e:
            return ticker, None
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_ticker, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, df = future.result()
            if df is not None and not df.empty:
                data[ticker] = df
    
    return data


def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Identify swing highs and lows using rolling window."""
    df = df.copy()
    
    df['swing_high'] = df['High'].rolling(window=window, center=True).max()
    df['swing_high'] = df['High'].where(df['High'] == df['swing_high'])
    
    df['swing_low'] = df['Low'].rolling(window=window, center=True).min()
    df['swing_low'] = df['Low'].where(df['Low'] == df['swing_low'])
    
    df['swing_high'] = df['swing_high'].shift(-window // 2)
    df['swing_low'] = df['swing_low'].shift(-window // 2)
    
    return df


def detect_liquidity_sweeps(df: pd.DataFrame) -> pd.DataFrame:
    """Detect bullish and bearish liquidity sweeps."""
    df = df.copy()
    df = find_swing_highs_lows(df)
    
    df['prev_swing_low'] = df['swing_low'].shift(1)
    df['prev_swing_high'] = df['swing_high'].shift(1)
    
    df['bull_sweep'] = (
        (df['Low'] < df['prev_swing_low']) &
        (df['Close'] > df['Open']) &
        (df['Low'] < df['prev_swing_low'] * 1.01)
    )
    
    df['bear_sweep'] = (
        (df['High'] > df['prev_swing_high']) &
        (df['Close'] < df['Open']) &
        (df['High'] > df['prev_swing_high'] * 0.99)
    )
    
    return df


def identify_strong_structures(df: pd.DataFrame) -> pd.DataFrame:
    """Identify strong highs and lows that had prior liquidity sweep."""
    df = detect_liquidity_sweeps(df)
    
    df['strong_low'] = False
    df['strong_high'] = False
    
    for i in range(1, len(df)):
        if df.loc[i, 'bull_sweep']:
            swing_low = df.loc[i, 'swing_low']
            if swing_low and not pd.isna(swing_low):
                mask = (df['swing_low'] == swing_low) & (df.index > i)
                if mask.any():
                    df.loc[mask, 'strong_low'] = True
        
        if df.loc[i, 'bear_sweep']:
            swing_high = df.loc[i, 'swing_high']
            if swing_high and not pd.isna(swing_high):
                mask = (df['swing_high'] == swing_high) & (df.index > i)
                if mask.any():
                    df.loc[mask, 'strong_high'] = True
    
    return df


def detect_bos_chooch(df: pd.DataFrame) -> pd.DataFrame:
    """Detect BOS and CHOCH with close body validation."""
    df = identify_strong_structures(df)
    
    df['bos_bull'] = False
    df['bos_bear'] = False
    df['chooch_bull'] = False
    df['chooch_bear'] = False
    
    strong_highs = df[df['strong_high']]['High'].values
    strong_lows = df[df['strong_low']]['Low'].values
    
    last_strong_high_idx = None
    last_strong_low_idx = None
    
    for i in range(1, len(df)):
        current_price = df.loc[i, 'Close']
        current_high = df.loc[i, 'High']
        current_low = df.loc[i, 'Low']
        prev_close = df.loc[i-1, 'Close']
        
        for sh in strong_highs:
            if sh and not pd.isna(sh):
                if current_price > sh and prev_close <= sh:
                    df.loc[i, 'bos_bull'] = True
                    last_strong_high_idx = i
                    break
        
        for sl in strong_lows:
            if sl and not pd.isna(sl):
                if current_price < sl and prev_close >= sl:
                    df.loc[i, 'bos_bear'] = True
                    last_strong_low_idx = i
                    break
        
        if last_strong_low_idx is not None and i > last_strong_low_idx:
            strong_low_after = df.loc[last_strong_low_idx, 'Low']
            if current_price < strong_low_after and prev_close >= strong_low_after:
                df.loc[i, 'chooch_bear'] = True
        
        if last_strong_high_idx is not None and i > last_strong_high_idx:
            strong_high_after = df.loc[last_strong_high_idx, 'High']
            if current_price > strong_high_after and prev_close <= strong_high_after:
                df.loc[i, 'chooch_bull'] = True
    
    return df


def calculate_fibonacci(df: pd.DataFrame, start_idx: int, end_idx: int) -> dict:
    """Calculate Fibonacci levels for a move."""
    if start_idx >= end_idx or start_idx < 0 or end_idx >= len(df):
        return {}
    
    start_price = df.loc[start_idx, 'Low'] if df.loc[start_idx, 'Close'] > df.loc[start_idx, 'Open'] else df.loc[start_idx, 'Close']
    end_price = df.loc[end_idx, 'High']
    
    diff = end_price - start_price
    
    levels = {
        '0.0': start_price,
        '0.236': start_price + diff * 0.236,
        '0.382': start_price + diff * 0.382,
        '0.5': start_price + diff * 0.5,
        '0.618': start_price + diff * 0.618,
        '0.786': start_price + diff * 0.786,
        '1.0': end_price
    }
    
    return levels


def find_order_blocks(df: pd.DataFrame, signal_idx: int, direction: str) -> pd.DataFrame:
    """Find Order Blocks prior to a strong move."""
    if signal_idx < 3 or signal_idx >= len(df):
        return pd.DataFrame()
    
    search_range = range(max(0, signal_idx - 10), signal_idx)
    blocks = []
    
    for i in search_range:
        if direction == 'bull':
            if df.loc[i, 'Close'] < df.loc[i, 'Open']:
                block = {
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bearish'
                }
                blocks.append(block)
        else:
            if df.loc[i, 'Close'] > df.loc[i, 'Open']:
                block = {
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bullish'
                }
                blocks.append(block)
    
    return pd.DataFrame(blocks)


def find_fvg(df: pd.DataFrame, window: int = 3) -> list:
    """Find Fair Value Gaps (3 candles: n-1 high > n+1 low or n-1 low < n+1 high)."""
    fvgs = []
    
    for i in range(1, len(df) - 1):
        high_n1 = df.loc[i-1, 'High']
        low_n1 = df.loc[i-1, 'Low']
        high_n1_idx = i-1
        low_n1_idx = i-1
        
        if high_n1 > df.loc[i+1, 'Low']:
            fvg = {
                'type': 'bearish',
                'top': high_n1,
                'bottom': df.loc[i+1, 'Low'],
                'mid': (high_n1 + df.loc[i+1, 'Low']) / 2,
                'idx': high_n1_idx
            }
            fvgs.append(fvg)
        
        if low_n1 < df.loc[i+1, 'High']:
            fvg = {
                'type': 'bullish',
                'top': df.loc[i+1, 'High'],
                'bottom': low_n1,
                'mid': (df.loc[i+1, 'High'] + low_n1) / 2,
                'idx': low_n1_idx
            }
            fvgs.append(fvg)
    
    return fvgs


def detect_smc_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Main function to detect all SMC signals."""
    df = detect_bos_chooch(df)
    
    df['signal'] = None
    df['signal_type'] = None
    df['poi_type'] = None
    df['poi_price'] = np.nan
    df['zone'] = None
    df['sl_price'] = np.nan
    df['tp1_price'] = np.nan
    df['rr_ratio'] = np.nan
    df['mtf_note'] = None
    
    for i in range(10, len(df)):
        if df.loc[i, 'bos_bull']:
            direction = 'bull'
            start_idx = i - 5
            end_idx = i
            
            fib = calculate_fibonacci(df, start_idx, end_idx)
            
            current_price = df.loc[i, 'Close']
            
            order_blocks = find_order_blocks(df, i, 'bull')
            fvgs = find_fvg(df)
            
            poi_price = None
            poi_type = None
            zone = 'neutral'
            
            if 0.5 in fib:
                fib_50 = fib['0.5']
                if current_price < fib_50:
                    poi_price = fib_50
                    poi_type = 'fib_50'
                    zone = 'discount'
                else:
                    zone = 'premium'
            
            if not order_blocks.empty:
                ob = order_blocks.iloc[-1]
                if poi_price is None or abs(ob['low'] - current_price) < abs(poi_price - current_price):
                    poi_price = ob['low']
                    poi_type = 'order_block'
            
            for fvg in fvgs:
                if fvg['type'] == 'bullish':
                    if poi_price is None or abs(fvg['mid'] - current_price) < abs(poi_price - current_price):
                        poi_price = fvg['mid']
                        poi_type = 'fvg'
            
            if poi_price is not None:
                strong_lows = df[df['strong_low']]['Low'].values
                sl_price = min(strong_lows) if len(strong_lows) > 0 else current_price * 0.98
                
                strong_highs = df[df['strong_high']]['High'].values
                tp1_price = max(strong_highs) if len(strong_highs) > 0 else current_price * 1.02
                
                risk = abs(current_price - sl_price)
                reward = abs(tp1_price - current_price)
                rr = reward / risk if risk > 0 else 0
                
                df.loc[i, 'signal'] = direction
                df.loc[i, 'signal_type'] = 'BOS'
                df.loc[i, 'poi_type'] = poi_type
                df.loc[i, 'poi_price'] = poi_price
                df.loc[i, 'zone'] = zone if zone else 'neutral'
                df.loc[i, 'sl_price'] = sl_price
                df.loc[i, 'tp1_price'] = tp1_price
                df.loc[i, 'rr_ratio'] = round(rr, 2)
                df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF + alinhamento de fluxo'
        
        elif df.loc[i, 'bos_bear']:
            direction = 'bear'
            start_idx = i - 5
            end_idx = i
            
            fib = calculate_fibonacci(df, start_idx, end_idx)
            
            current_price = df.loc[i, 'Close']
            
            order_blocks = find_order_blocks(df, i, 'bear')
            fvgs = find_fvg(df)
            
            poi_price = None
            poi_type = None
            zone = 'neutral'
            
            if 0.5 in fib:
                fib_50 = fib['0.5']
                if current_price > fib_50:
                    poi_price = fib_50
                    poi_type = 'fib_50'
                    zone = 'premium'
                else:
                    zone = 'discount'
            
            if not order_blocks.empty:
                ob = order_blocks.iloc[-1]
                if poi_price is None or abs(ob['high'] - current_price) < abs(poi_price - current_price):
                    poi_price = ob['high']
                    poi_type = 'order_block'
            
            for fvg in fvgs:
                if fvg['type'] == 'bearish':
                    if poi_price is None or abs(fvg['mid'] - current_price) < abs(poi_price - current_price):
                        poi_price = fvg['mid']
                        poi_type = 'fvg'
            
            if poi_price is not None:
                strong_highs = df[df['strong_high']]['High'].values
                sl_price = max(strong_highs) if len(strong_highs) > 0 else current_price * 1.02
                
                strong_lows = df[df['strong_low']]['Low'].values
                tp1_price = min(strong_lows) if len(strong_lows) > 0 else current_price * 0.98
                
                risk = abs(current_price - sl_price)
                reward = abs(tp1_price - current_price)
                rr = reward / risk if risk > 0 else 0
                
                df.loc[i, 'signal'] = direction
                df.loc[i, 'signal_type'] = 'BOS'
                df.loc[i, 'poi_type'] = poi_type
                df.loc[i, 'poi_price'] = poi_price
                df.loc[i, 'zone'] = zone if zone else 'neutral'
                df.loc[i, 'sl_price'] = sl_price
                df.loc[i, 'tp1_price'] = tp1_price
                df.loc[i, 'rr_ratio'] = round(rr, 2)
                df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF + alinhamento de fluxo'
        
        elif df.loc[i, 'chooch_bull']:
            direction = 'bull'
            df.loc[i, 'signal'] = 'bull'
            df.loc[i, 'signal_type'] = 'CHOCH'
            df.loc[i, 'zone'] = 'reversal'
            df.loc[i, 'mtf_note'] = 'Reversão - aguardar entrada no POI'
        
        elif df.loc[i, 'chooch_bear']:
            direction = 'bear'
            df.loc[i, 'signal'] = 'bear'
            df.loc[i, 'signal_type'] = 'CHOCH'
            df.loc[i, 'zone'] = 'reversal'
            df.loc[i, 'mtf_note'] = 'Reversão - aguardar entrada no POI'
    
    return df


def get_latest_signals(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Extract the latest signals from the dataframe."""
    signals = df[df['signal'].notna()].tail(lookback)
    return signals


def run_screener(tickers_file: str = 'tickers_b3.csv', min_rr: float = 1.5) -> pd.DataFrame:
    """Run the complete screener on all tickers."""
    tickers_df = pd.read_csv(tickers_file)
    tickers = [f"{t}.SA" for t in tickers_df['ticker'].tolist()]
    
    print(f"Baixando dados de {len(tickers)} ativos...")
    data = download_data_batch(tickers)
    
    all_signals = []
    
    print("Processando sinais SMC...")
    for ticker, df in data.items():
        if df is None or len(df) < 50:
            continue
        
        try:
            df_result = detect_smc_signals(df)
            signals = get_latest_signals(df_result)
            
            if not signals.empty:
                latest = signals.iloc[-1]
                if pd.notna(latest['signal']) and latest.get('rr_ratio', 0) >= min_rr:
                    ticker_clean = ticker.replace('.SA', '')
                    all_signals.append({
                        'ticker': ticker_clean,
                        'signal': latest['signal'],
                        'signal_type': latest['signal_type'],
                        'price': df_result.iloc[-1]['Close'],
                        'poi_type': latest.get('poi_type'),
                        'poi_price': latest.get('poi_price'),
                        'zone': latest.get('zone'),
                        'sl': latest.get('sl_price'),
                        'tp1': latest.get('tp1_price'),
                        'rr': latest.get('rr_ratio'),
                        'mtf_note': latest.get('mtf_note')
                    })
        except Exception as e:
            continue
    
    if all_signals:
        result_df = pd.DataFrame(all_signals)
        return result_df
    return pd.DataFrame()


if __name__ == '__main__':
    result = run_screener()
    if not result.empty:
        print("\n=== SINAIS SMC ENCONTRADOS ===")
        print(result.to_string())
    else:
        print("Nenhum sinal encontrado com os critérios configurados.")
