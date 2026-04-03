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


def download_data_batch(tickers: list, period: str = '2y', interval: str = '1d') -> dict:
    """Download data using yfinance's native batch capabilities."""
    data = {}
    
    # yfinance natively handles batch downloading robustly
    df_batch = yf.download(tickers, period=period, interval=interval, group_by='ticker', progress=False, auto_adjust=True)
    
    if df_batch is None or df_batch.empty:
        return data

    for ticker in tickers:
        try:
            # Extract data for specific ticker
            if len(tickers) > 1:
                if ticker not in df_batch.columns.levels[0]:
                    continue
                df = df_batch[ticker].copy()
            else:
                df = df_batch.copy()
            
            df.dropna(inplace=True)
            if df.empty:
                continue
                
            df.reset_index(inplace=True)
            if 'Date' not in df.columns and 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'Date'}, inplace=True)
                
            # If the date column is still an index named Date
            if 'Date' not in df.columns and df.index.name == 'Date':
                df.reset_index(inplace=True)
                
            data[ticker] = df
        except Exception:
            continue

    return data


def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Identify swing highs and lows using rolling window (no look-ahead bias)."""
    df = df.copy()
    half = window // 2

    # Use shift-based approach instead of center=True to avoid look-ahead bias
    rolling_max = df['High'].rolling(window=window).max().shift(-half)
    rolling_min = df['Low'].rolling(window=window).min().shift(-half)

    df['swing_high'] = np.where(df['High'] == rolling_max, df['High'], np.nan)
    df['swing_low'] = np.where(df['Low'] == rolling_min, df['Low'], np.nan)

    return df


def detect_liquidity_sweeps(df: pd.DataFrame) -> pd.DataFrame:
    """Detect bullish and bearish liquidity sweeps."""
    df = df.copy()
    df = find_swing_highs_lows(df)

    # Use PREVIOUS swing levels (shift to avoid self-comparison)
    df['prev_swing_low'] = df['swing_low'].shift(1).ffill()
    df['prev_swing_high'] = df['swing_high'].shift(1).ffill()

    # Bull sweep: wick goes below previous swing low + closes bullish (body engulfs sweep)
    df['bull_sweep'] = (
        (df['Low'] < df['prev_swing_low']) &
        (df['Close'] > df['Open'])
    )

    # Bear sweep: wick goes above previous swing high + closes bearish
    df['bear_sweep'] = (
        (df['High'] > df['prev_swing_high']) &
        (df['Close'] < df['Open'])
    )

    return df


def identify_strong_structures(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify strong highs/lows: points that formed AFTER a liquidity sweep.
    A strong low forms when price sweeps a prior low then rallies (bull sweep),
    making the LOW of that sweep candle a 'protected' level.
    A strong high forms when price sweeps a prior high then falls (bear sweep).
    """
    df = detect_liquidity_sweeps(df)

    df['strong_low'] = False
    df['strong_high'] = False

    # After a bull_sweep candle, its Low is a strong low candidate
    # After a bear_sweep candle, its High is a strong high candidate
    for i in range(1, len(df) - 1):
        if df.loc[i, 'bull_sweep']:
            df.loc[i, 'strong_low'] = True
        if df.loc[i, 'bear_sweep']:
            df.loc[i, 'strong_high'] = True

    return df


def detect_bos_choch(df: pd.DataFrame) -> pd.DataFrame:
    """Detect BOS and CHOCH with close body validation."""
    df = identify_strong_structures(df)

    df['bos_bull'] = False
    df['bos_bear'] = False
    df['choch_bull'] = False
    df['choch_bear'] = False

    strong_high_levels = []
    strong_low_levels = []

    last_bos_bull_level = None
    last_bos_bear_level = None
    trend = None  # 'up' or 'down'

    for i in range(2, len(df)):
        row = df.loc[i]
        prev_row = df.loc[i - 1]

        curr_close = row['Close']
        prev_close = prev_row['Close']

        # Accumulate strong levels seen so far
        if df.loc[i - 1, 'strong_high']:
            strong_high_levels.append(df.loc[i - 1, 'High'])
        if df.loc[i - 1, 'strong_low']:
            strong_low_levels.append(df.loc[i - 1, 'Low'])

        if not strong_high_levels or not strong_low_levels:
            continue

        last_strong_high = max(strong_high_levels[-5:])  # Most relevant recent
        last_strong_low = min(strong_low_levels[-5:])

        # BOS Bull: close breaks above last strong high (continuation up)
        if curr_close > last_strong_high and prev_close <= last_strong_high:
            if trend == 'down':
                # Breaking up in a downtrend = CHOCH (reversal signal)
                df.loc[i, 'choch_bull'] = True
            else:
                df.loc[i, 'bos_bull'] = True
            trend = 'up'
            last_bos_bull_level = last_strong_high

        # BOS Bear: close breaks below last strong low (continuation down)
        elif curr_close < last_strong_low and prev_close >= last_strong_low:
            if trend == 'up':
                # Breaking down in an uptrend = CHOCH (reversal signal)
                df.loc[i, 'choch_bear'] = True
            else:
                df.loc[i, 'bos_bear'] = True
            trend = 'down'
            last_bos_bear_level = last_strong_low

    return df


def calculate_fibonacci(start_price: float, end_price: float) -> dict:
    """Calculate Fibonacci levels for a move."""
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

    search_range = range(max(0, signal_idx - 15), signal_idx)
    blocks = []

    for i in search_range:
        if direction == 'bull':
            # For bullish OB: last bearish candle before the impulse up
            if df.loc[i, 'Close'] < df.loc[i, 'Open']:
                blocks.append({
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bearish'
                })
        else:
            # For bearish OB: last bullish candle before the impulse down
            if df.loc[i, 'Close'] > df.loc[i, 'Open']:
                blocks.append({
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bullish'
                })

    return pd.DataFrame(blocks)


def find_fvg(df: pd.DataFrame) -> list:
    """Find Fair Value Gaps (3 candles: gap between n-1 and n+1)."""
    fvgs = []

    for i in range(1, len(df) - 1):
        high_n_minus1 = df.loc[i - 1, 'High']
        low_n_minus1 = df.loc[i - 1, 'Low']
        high_n_plus1 = df.loc[i + 1, 'High']
        low_n_plus1 = df.loc[i + 1, 'Low']

        # Bearish FVG: high of n-1 is BELOW low of n+1 → gap going up
        if high_n_minus1 < low_n_plus1:
            fvgs.append({
                'type': 'bullish',
                'top': low_n_plus1,
                'bottom': high_n_minus1,
                'mid': (low_n_plus1 + high_n_minus1) / 2,
                'idx': i
            })

        # Bullish FVG: low of n-1 is ABOVE high of n+1 → gap going down
        if low_n_minus1 > high_n_plus1:
            fvgs.append({
                'type': 'bearish',
                'top': low_n_minus1,
                'bottom': high_n_plus1,
                'mid': (low_n_minus1 + high_n_plus1) / 2,
                'idx': i
            })

    return fvgs


def detect_smc_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Main function to detect all SMC signals."""
    df = detect_bos_choch(df)

    df['signal'] = None
    df['signal_type'] = None
    df['poi_type'] = None
    df['poi_price'] = np.nan
    df['zone'] = None
    df['sl_price'] = np.nan
    df['tp1_price'] = np.nan
    df['mtf_note'] = None

    fvgs = find_fvg(df)

    for i in range(10, len(df)):
        signal_dir = None
        signal_type = None

        if df.loc[i, 'bos_bull']:
            signal_dir = 'bull'
            signal_type = 'BOS'
        elif df.loc[i, 'bos_bear']:
            signal_dir = 'bear'
            signal_type = 'BOS'
        elif df.loc[i, 'choch_bull']:
            signal_dir = 'bull'
            signal_type = 'CHOCH'
        elif df.loc[i, 'choch_bear']:
            signal_dir = 'bear'
            signal_type = 'CHOCH'

        if signal_dir is None:
            continue

        current_price = df.loc[i, 'Close']

        # Fibonacci: find relevant swing range (last ~20 candles)
        lookback = min(i, 20)
        if signal_dir == 'bull':
            start_price = df.loc[i - lookback:i, 'Low'].min()
            end_price = df.loc[i - lookback:i, 'High'].max()
        else:
            start_price = df.loc[i - lookback:i, 'Low'].min()
            end_price = df.loc[i - lookback:i, 'High'].max()

        fib = calculate_fibonacci(start_price, end_price)
        fib_50 = fib.get('0.5', current_price)

        zone = 'discount' if current_price < fib_50 else 'premium'

        poi_price = None
        poi_type = None

        # Prioritize POI near current price
        order_blocks = find_order_blocks(df, i, signal_dir)

        if signal_dir == 'bull':
            # Look for OB below current price (discount zone)
            if not order_blocks.empty:
                close_obs = order_blocks[order_blocks['low'] <= current_price]
                if not close_obs.empty:
                    ob = close_obs.iloc[-1]
                    poi_price = (ob['high'] + ob['low']) / 2
                    poi_type = 'Order Block'

            # Look for bullish FVG below current price
            for fvg in reversed(fvgs):
                if fvg['type'] == 'bullish' and fvg['mid'] < current_price and fvg['idx'] < i:
                    if poi_price is None or abs(fvg['mid'] - current_price) < abs(poi_price - current_price):
                        poi_price = fvg['mid']
                        poi_type = 'FVG'
                    break

            if poi_price is None:
                poi_price = fib_50
                poi_type = 'Fib 50%'

        else:  # bear
            if not order_blocks.empty:
                close_obs = order_blocks[order_blocks['high'] >= current_price]
                if not close_obs.empty:
                    ob = close_obs.iloc[-1]
                    poi_price = (ob['high'] + ob['low']) / 2
                    poi_type = 'Order Block'

            for fvg in reversed(fvgs):
                if fvg['type'] == 'bearish' and fvg['mid'] > current_price and fvg['idx'] < i:
                    if poi_price is None or abs(fvg['mid'] - current_price) < abs(poi_price - current_price):
                        poi_price = fvg['mid']
                        poi_type = 'FVG'
                    break

            if poi_price is None:
                poi_price = fib_50
                poi_type = 'Fib 50%'

        # SL/TP
        strong_lows = df[df['strong_low']]['Low'].values
        strong_highs = df[df['strong_high']]['High'].values

        if signal_dir == 'bull':
            sl_price = float(df.loc[i - lookback:i, 'Low'].min()) * 0.995
            tp1_price = float(df.loc[i - lookback:i, 'High'].max()) * 1.01
        else:
            sl_price = float(df.loc[i - lookback:i, 'High'].max()) * 1.005
            tp1_price = float(df.loc[i - lookback:i, 'Low'].min()) * 0.99

        df.loc[i, 'signal'] = signal_dir
        df.loc[i, 'signal_type'] = signal_type
        df.loc[i, 'poi_type'] = poi_type
        df.loc[i, 'poi_price'] = round(float(poi_price), 2) if poi_price else np.nan
        df.loc[i, 'zone'] = zone
        df.loc[i, 'sl_price'] = round(float(sl_price), 2)
        df.loc[i, 'tp1_price'] = round(float(tp1_price), 2)
        df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF + alinhamento de fluxo'

    return df


def get_latest_signals(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """Extract the latest signals from the dataframe."""
    signals = df[df['signal'].notna()].tail(lookback)
    return signals


def run_screener(tickers_file: str = 'tickers_b3.csv') -> pd.DataFrame:
    """Run the complete screener on all tickers."""
    try:
        tickers_df = pd.read_csv(tickers_file)
        # Deduplicate to prevent processing the same asset multiple times
        tickers = list(set([f"{t}.SA" for t in tickers_df['ticker'].dropna()]))
    except Exception as e:
        print(f"Erro ao ler tickers: {e}")
        return pd.DataFrame()

    print(f"Baixando dados de {len(tickers)} ativos...")
    data = download_data_batch(tickers)

    all_signals = []

    print("Processando sinais SMC...")
    for ticker, df in data.items():
        if df is None or len(df) < 50:
            continue

        try:
            df_result = detect_smc_signals(df.copy())
            signals = get_latest_signals(df_result)

            if not signals.empty:
                latest = signals.iloc[-1]
                if pd.notna(latest['signal']):
                    ticker_clean = ticker.replace('.SA', '')
                    # Use the last row's Close from the original dataframe
                    last_close = df['Close'].iloc[-1]
                    current_price = float(last_close) if not isinstance(last_close, pd.Series) else float(last_close.iloc[0])
                    poi = latest.get('poi_price')
                    sl = latest.get('sl_price')
                    tp1 = latest.get('tp1_price')

                    risk = abs(current_price - float(sl)) if pd.notna(sl) else 0
                    reward = abs(float(tp1) - current_price) if pd.notna(tp1) else 0
                    rr = round(reward / risk, 2) if risk > 0 else 0

                    all_signals.append({
                        'Ticker': ticker_clean,
                        'Sinal': latest['signal'],
                        'Tipo': latest['signal_type'],
                        'Preço': round(current_price, 2),
                        'POI': latest.get('poi_type'),
                        'POI Preço': round(float(poi), 2) if pd.notna(poi) else None,
                        'Zona': latest.get('zone'),
                        'SL': round(float(sl), 2) if pd.notna(sl) else None,
                        'TP1': round(float(tp1), 2) if pd.notna(tp1) else None,
                        'RR': rr,
                        'Nota MTF': latest.get('mtf_note')
                    })
        except Exception:
            continue

    if all_signals:
        return pd.DataFrame(all_signals)
    return pd.DataFrame()


if __name__ == '__main__':
    result = run_screener()
    if not result.empty:
        print("\n=== SINAIS SMC ENCONTRADOS ===")
        print(result.to_string())
    else:
        print("Nenhum sinal encontrado com os critérios configurados.")
