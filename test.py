"""
Test implementation of the new SMC Engine
"""
import pandas as pd
import numpy as np

def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    df = df.copy()
    half = window // 2
    rolling_max = df['High'].rolling(window=window).max().shift(-half)
    rolling_min = df['Low'].rolling(window=window).min().shift(-half)
    df['swing_high'] = np.where(df['High'] == rolling_max, df['High'], np.nan)
    df['swing_low'] = np.where(df['Low'] == rolling_min, df['Low'], np.nan)
    return df

def detect_liquidity_sweeps(df: pd.DataFrame) -> pd.DataFrame:
    df = find_swing_highs_lows(df)
    df['prev_swing_low'] = df['swing_low'].shift(1).ffill()
    df['prev_swing_high'] = df['swing_high'].shift(1).ffill()
    
    # Sweep: wick breaks extreme, body closes within (engine optimization: just check wick + close against open)
    # Actually, a better definition of sweep: wick goes below, but close is ABOVE the prev swing low!
    df['bull_sweep'] = (df['Low'] < df['prev_swing_low']) & (df['Close'] > df['prev_swing_low'])
    df['bear_sweep'] = (df['High'] > df['prev_swing_high']) & (df['Close'] < df['prev_swing_high'])
    return df

def map_market_structure(df: pd.DataFrame) -> pd.DataFrame:
    df = detect_liquidity_sweeps(df)
    
    df['bos_bull'] = False
    df['bos_bear'] = False
    df['choch_bull'] = False
    df['choch_bear'] = False
    
    df['active_strong_low'] = np.nan
    df['active_strong_low_idx'] = np.nan
    df['active_strong_high'] = np.nan
    df['active_strong_high_idx'] = np.nan
    
    trend = 0  
    
    recent_high = df['High'].iloc[0]
    recent_low = df['Low'].iloc[0]
    
    strong_low = None
    strong_high = None
    
    candidate_low = None
    candidate_high = None
    
    for i in range(1, len(df)):
        cur_high = df.loc[i, 'High']
        cur_low = df.loc[i, 'Low']
        cur_close = df.loc[i, 'Close']

        # Update leg extremes
        if cur_high > recent_high:
            recent_high = cur_high
        if cur_low < recent_low:
            recent_low = cur_low
            
        # Detect candidates from sweeps
        if df.loc[i, 'bull_sweep']:
            if candidate_low is None or cur_low < candidate_low[0]:
                candidate_low = (cur_low, i)
        else:
            if candidate_low is not None and cur_low <= candidate_low[0]:
                candidate_low = (cur_low, i)  # Update if it keeps going down in the exact same move

        if df.loc[i, 'bear_sweep']:
            if candidate_high is None or cur_high > candidate_high[0]:
                candidate_high = (cur_high, i)
        else:
            if candidate_high is not None and cur_high >= candidate_high[0]:
                candidate_high = (cur_high, i)

        if trend == 1:
            if strong_low is not None and cur_close < strong_low[0]:
                df.loc[i, 'choch_bear'] = True
                trend = -1
                strong_high = candidate_high if candidate_high is not None else (recent_high, df.loc[:i, 'High'].idxmax())
                candidate_low = None
                recent_low = cur_low 
            elif cur_close > recent_high and candidate_low is not None:
                df.loc[i, 'bos_bull'] = True
                strong_low = candidate_low
                candidate_low = None
                recent_high = cur_high
                
        elif trend == -1:
            if strong_high is not None and cur_close > strong_high[0]:
                df.loc[i, 'choch_bull'] = True
                trend = 1
                strong_low = candidate_low if candidate_low is not None else (recent_low, df.loc[:i, 'Low'].idxmin())
                candidate_high = None
                recent_high = cur_high 
            elif cur_close < recent_low and candidate_high is not None:
                df.loc[i, 'bos_bear'] = True
                strong_high = candidate_high
                candidate_high = None
                recent_low = cur_low
                
        else:
            if cur_close > recent_high and candidate_low is not None:
                trend = 1
                df.loc[i, 'choch_bull'] = True
                strong_low = candidate_low
                candidate_low = None
                recent_high = cur_high
            elif cur_close < recent_low and candidate_high is not None:
                trend = -1
                df.loc[i, 'choch_bear'] = True
                strong_high = candidate_high
                candidate_high = None
                recent_low = cur_low

        if strong_low is not None:
            df.loc[i, 'active_strong_low'] = strong_low[0]
            df.loc[i, 'active_strong_low_idx'] = strong_low[1]
        if strong_high is not None:
            df.loc[i, 'active_strong_high'] = strong_high[0]
            df.loc[i, 'active_strong_high_idx'] = strong_high[1]
            
    return df

print("Compiled successfully!")
