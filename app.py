"""
SMC Cloud Screener v3.0 - Streamlit Application
Professional Dashboard for B3 Stocks with SMC Logic
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import os
warnings.filterwarnings('ignore')


COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

st.set_page_config(
    page_title="SMC Cloud Screener v3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    'bull': '#2ECC71',
    'bear': '#E74C3C',
    'neutral': '#7F8C8D',
    'sweep': '#F39C12',
    'ob': '#9B59B6',
    'fvg': '#3498DB',
    'fib': '#E67E22',
    'background': '#1A1A2E',
    'card_bg': '#16213E',
    'accent': '#4A90D9',
    'text': '#ECEFF4',
    'text_muted': '#A0A0A0'
}


def download_data_batch(tickers: list, period: str = '2y', interval: str = '1d', max_workers: int = 20) -> dict:
    """Download data in parallel using ThreadPoolExecutor."""
    data = {}
    
    def download_ticker(ticker):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty:
                return ticker, None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return ticker, df
        except:
            return ticker, None
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_ticker, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, df = future.result()
            if df is not None and not df.empty:
                data[ticker] = df
    
    return data


def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Identify swing highs and lows."""
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


def find_fvg(df: pd.DataFrame) -> list:
    """Find Fair Value Gaps."""
    fvgs = []
    
    for i in range(1, len(df) - 1):
        high_n1 = df.loc[i-1, 'High']
        low_n1 = df.loc[i-1, 'Low']
        
        if high_n1 > df.loc[i+1, 'Low']:
            fvg = {
                'type': 'bearish',
                'top': high_n1,
                'bottom': df.loc[i+1, 'Low'],
                'mid': (high_n1 + df.loc[i+1, 'Low']) / 2,
                'idx': i-1
            }
            fvgs.append(fvg)
        
        if low_n1 < df.loc[i+1, 'High']:
            fvg = {
                'type': 'bullish',
                'top': df.loc[i+1, 'High'],
                'bottom': low_n1,
                'mid': (df.loc[i+1, 'High'] + low_n1) / 2,
                'idx': i-1
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
        zone = 'neutral'
        
        if df.loc[i, 'bos_bull']:
            direction = 'bull'
            start_idx = max(0, i - 5)
            end_idx = i
            
            fib = calculate_fibonacci(df, start_idx, end_idx)
            current_price = df.loc[i, 'Close']
            order_blocks = find_order_blocks(df, i, 'bull')
            fvgs = find_fvg(df)
            
            poi_price = None
            poi_type = None
            
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
                df.loc[i, 'zone'] = zone
                df.loc[i, 'sl_price'] = sl_price
                df.loc[i, 'tp1_price'] = tp1_price
                df.loc[i, 'rr_ratio'] = round(rr, 2)
                df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF + alinhamento de fluxo'
        
        elif df.loc[i, 'bos_bear']:
            direction = 'bear'
            start_idx = max(0, i - 5)
            end_idx = i
            
            fib = calculate_fibonacci(df, start_idx, end_idx)
            current_price = df.loc[i, 'Close']
            order_blocks = find_order_blocks(df, i, 'bear')
            fvgs = find_fvg(df)
            
            poi_price = None
            poi_type = None
            
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
                df.loc[i, 'zone'] = zone
                df.loc[i, 'sl_price'] = sl_price
                df.loc[i, 'tp1_price'] = tp1_price
                df.loc[i, 'rr_ratio'] = round(rr, 2)
                df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF + alinhamento de fluxo'
        
        elif df.loc[i, 'chooch_bull']:
            df.loc[i, 'signal'] = 'bull'
            df.loc[i, 'signal_type'] = 'CHOCH'
            df.loc[i, 'zone'] = 'reversal'
            df.loc[i, 'mtf_note'] = 'Reversão - aguardar entrada no POI'
        
        elif df.loc[i, 'chooch_bear']:
            df.loc[i, 'signal'] = 'bear'
            df.loc[i, 'signal_type'] = 'CHOCH'
            df.loc[i, 'zone'] = 'reversal'
            df.loc[i, 'mtf_note'] = 'Reversão - aguardar entrada no POI'
    
    return df


def get_latest_signals(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Extract the latest signals from the dataframe."""
    signals = df[df['signal'].notna()].tail(lookback)
    return signals


def run_screener(tickers_file: str = 'tickers_b3.csv', min_rr: float = 1.0) -> pd.DataFrame:
    """Run the complete screener on all tickers."""
    tickers_df = pd.read_csv(tickers_file)
    
    def get_yf_ticker(ticker, tipo):
        if tipo == 'BDR':
            return ticker
        return f"{ticker}.SA"
    
    tickers = [get_yf_ticker(t, row['tipo']) for t, row in tickers_df.iterrows()]
    
    data = download_data_batch(tickers)
    
    all_signals = []
    
    for ticker, df in data.items():
        if df is None or len(df) < 50:
            continue
        
        try:
            df_result = detect_smc_signals(df)
            signals = get_latest_signals(df_result)
            
            if not signals.empty:
                latest = signals.iloc[-1]
                if pd.notna(latest['signal']):
                    if latest.get('rr_ratio', 0) >= min_rr or latest['signal_type'] == 'CHOCH':
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
        except:
            continue
    
    if all_signals:
        result_df = pd.DataFrame(all_signals)
        return result_df
    return pd.DataFrame()


def create_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create interactive chart with SMC markers."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    df = detect_smc_signals(df)
    
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=ticker
        ),
        row=1, col=1
    )
    
    df_sweeps = df[df['bull_sweep'] | df['bear_sweep']]
    if not df_sweeps.empty:
        fig.add_trace(
            go.Scatter(
                x=df_sweeps.index,
                y=df_sweeps['Low'].where(df_sweeps['bull_sweep']).fillna(df_sweeps['High']),
                mode='markers',
                marker=dict(symbol='triangle-down', size=10, color=COLORS['sweep']),
                name='Liquidity Sweep'
            ),
            row=1, col=1
        )
    
    df_strong = df[df['strong_low'] | df['strong_high']]
    if not df_strong.empty:
        fig.add_trace(
            go.Scatter(
                x=df_strong.index,
                y=df_strong['Low'].where(df_strong['strong_low']).fillna(df_strong['High']),
                mode='markers',
                marker=dict(symbol='diamond', size=12, color=COLORS['ob']),
                name='Strong Level'
            ),
            row=1, col=1
        )
    
    signals = df[df['signal'].notna()]
    if not signals.empty:
        for idx, row in signals.iterrows():
            color = COLORS['bull'] if row['signal'] == 'bull' else COLORS['bear']
            fig.add_annotation(
                x=idx,
                y=row['Close'],
                text=f"{row['signal_type']}",
                showarrow=True,
                arrowhead=2,
                arrowcolor=color,
                font=dict(color=color, size=10)
            )
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker=dict(color='rgba(128, 128, 128, 0.5)')
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        template='plotly_dark',
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxesrangeslicing()
    fig.update_yaxes(title="Price", row=1, col=1)
    fig.update_yaxes(title="Volume", row=2, col=1)
    
    return fig


def landing_page():
    """Professional landing page."""
    
    st.markdown("""
    <style>
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00C805, #00E70A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.3rem;
        color: #A0A0A0;
        margin-bottom: 1.5rem;
    }
    .feature-card {
        background: linear-gradient(145deg, #16213E, #1A1A2E);
        border-radius: 12px;
        padding: 14px;
        margin: 6px 0;
        border: 1px solid #2D3A4F;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .feature-card h4 {
        margin: 0 0 6px 0;
    }
    .feature-card p {
        margin: 0;
        line-height: 1.3;
    }
    .stat-card {
        background: linear-gradient(145deg, #1A1A2E, #16213E);
        border-radius: 10px;
        padding: 14px;
        text-align: center;
        border: 1px solid #2D3A4F;
    }
    .stat-number {
        font-size: 1.6rem;
        font-weight: bold;
        color: #4A90D9;
    }
    .stat-label {
        color: #A0A0A0;
        font-size: 0.75rem;
    }
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #4A90D9, transparent);
        margin: 1.2rem 0;
    }
    .mtf-note {
        background: #16213E;
        border-left: 4px solid #F39C12;
        padding: 10px;
        border-radius: 0 8px 8px 0;
        margin: 6px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<p class="hero-title">📈 SMC Cloud Screener v3.0</p>', unsafe_allow_html=True)
        st.markdown('''<p class="hero-subtitle">Screener Institucional para Ações da B3</p>
        <p style="color: #7F8C8D; font-size: 0.85rem;">
            Varredura diária de 280+ ativos com lógica SMC (Smart Money Concepts)<br>
            Baseado em ICT/SMC 2025-2026 com validação rigorosa de liquidez
        </p>''', unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🚀")
        if st.button("▶ Iniciar Screener", type="primary", use_container_width=True):
            st.session_state['show_screener'] = True
            st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown("### 🔑 Funcionalidades Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="feature-card">
            <h4 style="color: {COLORS['sweep']};">💧 Liquidity Sweeps</h4>
            <p style="color: #A0A0A0; font-size: 0.8rem;">Detecção de varreduras de liquidez (sweeps) que validam topos e fundos fortes</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="feature-card">
            <h4 style="color: {COLORS['bull']};">🎯 BOS/CHOCH</h4>
            <p style="color: #A0A0A0; font-size: 0.8rem;">Identificação de quebras de estrutura com validação de close de corpo</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="feature-card">
            <h4 style="color: {COLORS['fib']};">📊 Fibonacci</h4>
            <p style="color: #A0A0A0; font-size: 0.8rem;">Zonas de Discount (compra) e Premium (venda) com níveis 50%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="feature-card">
            <h4 style="color: {COLORS['ob']};">🧱 Order Blocks + FVG</h4>
            <p style="color: #A0A0A0; font-size: 0.8rem;">Blocos de ordem e Fair Value Gaps como POIs de alta confluência</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">280+</div>
            <div class="stat-label">Ações B3</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">45+</div>
            <div class="stat-label">BDRs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">D1</div>
            <div class="stat-label">Timeframe</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">1:3</div>
            <div class="stat-label">RR Mínimo</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown("### ⚠️ Regras de Execução (MTF)")
    
    st.markdown("""
    <div class="mtf-note">
        <strong>Fluxo de Trabalho:</strong><br>
        1. Aguarde o preço retornar ao POI no timeframe D1<br>
        2. Mude para LTF (15min/1min) e espere CHOCH interno<br>
        3. Entre apenas quando o fluxo do LTF se alinhar com a tendência D1<br>
        4. Entrada: início do Order Block ou preenchimento parcial do FVG<br>
        5. <strong>SL:</strong> Logo abaixo/acima do strong low/high<br>
        6. <strong>TP:</strong> Primeiro alvo = topo/fundo fraco oposto
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; color: #555; font-size: 0.8rem;">
        <p>Desenvolvido com base em ICT/SMC 2025-2026 | Dados: Yahoo Finance</p>
        <p>⚠️ <strong>Isenção de Responsabilidade:</strong> Este screener é uma ferramenta de análise. 
        Não constitui conselho financeiro. Sempre faça sua própria análise antes de operar.</p>
    </div>
    """, unsafe_allow_html=True)


def screener_page():
    """Main screener page."""
    
    st.markdown("""
    <style>
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        color: #00C805;
    }
    .filter-badge {
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<p class="header-title">📈 SMC Screener - Sinais Ativos</p>', unsafe_allow_html=True)
    
    with col2:
        if st.button("← Voltar", use_container_width=True):
            st.session_state['show_screener'] = False
            st.rerun()
    
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        
        min_rr = st.slider("RR Mínimo", 1.0, 5.0, 1.5, 0.5)
        
        signal_filter = st.multiselect(
            "Filtrar Sinais",
            ["bull", "bear"],
            default=["bull", "bear"]
        )
        
        zone_filter = st.multiselect(
            "Filtrar Zona",
            ["discount", "premium", "reversal"],
            default=["discount", "premium", "reversal"]
        )
        
        st.markdown("---")
        st.markdown("### 📊 Legenda")
        st.markdown(f"<span style='color: {COLORS['bull']}'>🟢 Bullish</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: {COLORS['bear']}'>🔴 Bearish</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: {COLORS['sweep']}'>🟡 Sweep</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: {COLORS['ob']}'>🟣 Order Block</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: {COLORS['fvg']}'>🔵 FVG</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: {COLORS['fib']}'>🟠 Fibonacci</span>", unsafe_allow_html=True)
    
    if 'signals_df' not in st.session_state:
        with st.spinner('🔄 Executando screener... isso pode levar alguns minutos'):
            st.session_state['signals_df'] = run_screener(min_rr=min_rr)
    
    df = st.session_state['signals_df']
    
    if not df.empty:
        if signal_filter:
            df = df[df['signal'].isin(signal_filter)]
        if zone_filter:
            df = df[df['zone'].isin(zone_filter)]
        
        st.markdown(f"### 📊 Encontrados: {len(df)} sinais")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sinais Bull", len(df[df['signal'] == 'bull']))
        with col2:
            st.metric("Sinais Bear", len(df[df['signal'] == 'bear']))
        with col3:
            st.metric("Discount", len(df[df['zone'] == 'discount']))
        with col4:
            st.metric("Premium", len(df[df['zone'] == 'premium']))
        
        st.markdown("---")
        
        def color_signal(val):
            if val == 'bull':
                return f'color: {COLORS["bull"]}; font-weight: bold;'
            elif val == 'bear':
                return f'color: {COLORS["bear"]}; font-weight: bold;'
            return ''
        
        styled_df = df.style.applymap(color_signal, subset=['signal'])\
            .format({
                'price': 'R$ {:.2f}',
                'poi_price': 'R$ {:.2f}',
                'sl': 'R$ {:.2f}',
                'tp1': 'R$ {:.2f}',
                'rr': '{:.2f}'
            })
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        st.markdown("---")
        st.markdown("### 📈 Análise Gráfica")
        
        selected_ticker = st.selectbox("Selecione um ativo para análise", df['ticker'].tolist())
        
        if selected_ticker:
            ticker_data = pd.read_csv('tickers_b3.csv')
            ticker_symbol = f"{selected_ticker}.SA"
            
            with st.spinner(f'Carregando dados de {selected_ticker}...'):
                data = yf.download(ticker_symbol, period='2y', interval='1d', progress=False)
                data.columns = COLUMNS
                
                fig = create_chart(data, selected_ticker)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### 📋 Detalhes do Sinal")
                signal_data = df[df['ticker'] == selected_ticker].iloc[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tipo", signal_data['signal'].upper())
                with col2:
                    st.metric("Zona", signal_data['zone'].upper())
                with col3:
                    st.metric("RR", f"{signal_data['rr']:.2f}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Preço Atual", f"R$ {signal_data['price']:.2f}")
                with col2:
                    st.metric("POI", f"R$ {signal_data['poi_price']:.2f}" if pd.notna(signal_data['poi_price']) else "N/A")
                with col3:
                    st.metric("POI Type", signal_data['poi_type'].upper() if pd.notna(signal_data['poi_type']) else "N/A")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Stop Loss", f"R$ {signal_data['sl']:.2f}" if pd.notna(signal_data['sl']) else "N/A")
                with col2:
                    st.metric("Take Profit 1", f"R$ {signal_data['tp1']:.2f}" if pd.notna(signal_data['tp1']) else "N/A")
                
                st.info(f"💡 {signal_data['mtf_note']}")
                
    else:
        st.warning("⚠️ Nenhum sinal encontrado com os critérios selecionados.")
        st.info("Tente ajustar o filtro de RR mínimo ou os filtros de sinais/zonas.")
    
    if st.button("🔄 Atualizar Screener"):
        st.session_state.pop('signals_df', None)
        st.rerun()


def main():
    """Main application."""
    
    if 'show_screener' not in st.session_state:
        st.session_state['show_screener'] = False
    
    if st.session_state['show_screener']:
        screener_page()
    else:
        landing_page()


if __name__ == '__main__':
    main()
