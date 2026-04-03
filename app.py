"""
SMC Cloud Screener v3.0 - Streamlit App
Screener Institucional para Ações da B3 com lógica SMC (Smart Money Concepts)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

from screener_logic import (
    run_screener,
    download_data_batch,
    detect_smc_signals,
)

# ─── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SMC Cloud Screener v3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
  --bg-dark: #0d0d1a;
  --bg-card: #12122a;
  --bg-glass: rgba(30, 30, 60, 0.55);
  --accent: #4a90d9;
  --accent2: #7c5cbf;
  --green: #00c48c;
  --red: #ff4d6d;
  --gold: #f4c430;
  --text-primary: #e8e8f0;
  --text-secondary: #8888aa;
  --border: rgba(74, 144, 217, 0.25);
}

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-primary);
}

.stApp {
    background: linear-gradient(135deg, #0d0d1a 0%, #111130 50%, #0d0d1a 100%);
}

/* ── Landing Hero ── */
.hero-wrapper {
    text-align: center;
    padding: 60px 20px 40px;
    position: relative;
}
.hero-badge {
    display: inline-block;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    color: white;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 6px 18px;
    border-radius: 50px;
    margin-bottom: 22px;
}
.hero-title {
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #ffffff 0%, #a0bfe8 60%, #7c5cbf 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 16px;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: var(--text-secondary);
    max-width: 650px;
    margin: 0 auto 36px;
    line-height: 1.7;
}

/* ── Stat bar ── */
.stat-row {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin-bottom: 50px;
    flex-wrap: wrap;
}
.stat-item {
    text-align: center;
}
.stat-number {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-label {
    font-size: 0.78rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── Feature cards ── */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
    margin: 0 auto 50px;
    max-width: 1100px;
    padding: 0 16px;
}
.feature-card {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 24px;
    backdrop-filter: blur(12px);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(74, 144, 217, 0.18);
}
.feature-icon {
    font-size: 2rem;
    margin-bottom: 14px;
}
.feature-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
}
.feature-desc {
    font-size: 0.84rem;
    color: var(--text-secondary);
    line-height: 1.55;
}

/* ── Disclaimer ── */
.disclaimer {
    background: rgba(244, 196, 48, 0.08);
    border: 1px solid rgba(244, 196, 48, 0.3);
    border-radius: 12px;
    padding: 16px 22px;
    font-size: 0.82rem;
    color: var(--gold);
    text-align: center;
    max-width: 900px;
    margin: 0 auto 40px;
}

/* ── Signal table ── */
.signal-bull {
    color: var(--green);
    font-weight: 700;
}
.signal-bear {
    color: var(--red);
    font-weight: 700;
}

/* ── Status boxes ── */
.status-box {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(8px);
    margin-bottom: 16px;
}

/* ── MTF note ── */
.mtf-note {
    background: rgba(74, 144, 217, 0.1);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-top: 12px;
}

/* ── Streamlit overrides ── */
div[data-testid="metric-container"] {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 1rem;
    padding: 14px 40px;
    cursor: pointer;
    transition: opacity 0.2s ease, transform 0.15s ease;
    width: 100%;
}
.stButton > button:hover {
    opacity: 0.88;
    transform: translateY(-1px);
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f28 0%, #12122a 100%);
    border-right: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)


# ─── Session state init ──────────────────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'landing'
if 'signals_df' not in st.session_state:
    st.session_state.signals_df = None
if 'last_run' not in st.session_state:
    st.session_state.last_run = None


# ─── Landing Page ────────────────────────────────────────────────────────────────
def landing_page():
    st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-badge">⚡ Smart Money Concepts • B3 • ICT 2025 / 2026</div>
        <div class="hero-title">SMC Cloud Screener<br>v3.0</div>
        <div class="hero-subtitle">
            Varredura diária de <strong>200+ ativos</strong> da B3 com lógica institucional SMC —
            Liquidity Sweeps, BOS/CHOCH, Order Blocks, FVGs e Fibonacci.<br>
            Apenas estruturas fortes com varredura de liquidez confirmada.
        </div>
    </div>

    <div class="stat-row">
        <div class="stat-item">
            <div class="stat-number">200+</div>
            <div class="stat-label">Ativos Monitorados</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">D1</div>
            <div class="stat-label">Timeframe</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">6</div>
            <div class="stat-label">Confluências SMC</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">100%</div>
            <div class="stat-label">Automático</div>
        </div>
    </div>

    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">💧</div>
            <div class="feature-title">Liquidity Sweeps</div>
            <div class="feature-desc">Detecta varreduras de liquidez que validam topos e fundos fortes. Descarta Fake BOS sem sweep prévio.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">BOS / CHOCH</div>
            <div class="feature-desc">Identifica quebras de estrutura (continuação) e mudanças de caráter (reversão) com validação de close de corpo.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Fibonacci</div>
            <div class="feature-desc">Zonas de Discount (compra) e Premium (venda) com nível 50% como filtro de entrada de alta confluência.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧱</div>
            <div class="feature-title">Order Blocks + FVG</div>
            <div class="feature-desc">Blocos de ordem e Fair Value Gaps como POIs institucionais. Priorizados quando coincidem com OB+FVG.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <div class="feature-title">Gráficos Interativos</div>
            <div class="feature-desc">Candlestick Plotly com marcações visuais de sweeps, BOS/CHOCH, OBs, FVGs e zonas Fibonacci.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔁</div>
            <div class="feature-title">Nota MTF</div>
            <div class="feature-desc">Lembrete de confirmação em timeframe menor (CHOCH LTF 15min/1min) antes da entrada real.</div>
        </div>
    </div>

    <div class="disclaimer" style="max-width:900px;margin:0 auto 40px;">
        ⚠️ <strong>Isenção de Responsabilidade:</strong> Este screener é uma ferramenta de análise técnica. Não constitui conselho financeiro.
        Sempre realize sua própria análise e gestão de risco antes de operar.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        if st.button("🚀 Iniciar Screener", key="btn_start"):
            st.session_state.page = 'screener'
            st.rerun()


# ─── Screener Page ───────────────────────────────────────────────────────────────
def build_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Build an interactive SMC chart for a given ticker DataFrame."""
    df_plot = df.tail(120).copy()
    df_plot = df_plot.reset_index(drop=True)

    # Date axis
    if 'Date' in df_plot.columns:
        x_axis = pd.to_datetime(df_plot['Date']).dt.strftime('%Y-%m-%d')
    else:
        x_axis = list(range(len(df_plot)))

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.75, 0.25],
        subplot_titles=[f"📈 {ticker} — SMC Chart (D1)", "Volume"]
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=x_axis,
        open=df_plot['Open'],
        high=df_plot['High'],
        low=df_plot['Low'],
        close=df_plot['Close'],
        name='Preço',
        increasing_line_color='#00c48c',
        decreasing_line_color='#ff4d6d',
        increasing_fillcolor='rgba(0,196,140,0.7)',
        decreasing_fillcolor='rgba(255,77,109,0.7)',
    ), row=1, col=1)

    # Volume bars
    colors_vol = ['#00c48c' if c >= o else '#ff4d6d'
                  for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(
        x=x_axis, y=df_plot['Volume'],
        name='Volume',
        marker_color=colors_vol,
        opacity=0.6,
    ), row=2, col=1)

    # Mark liquidity sweeps
    if 'bull_sweep' in df_plot.columns:
        sweep_bull = df_plot[df_plot['bull_sweep'] == True]
        fig.add_trace(go.Scatter(
            x=x_axis[sweep_bull.index] if not sweep_bull.empty else [],
            y=sweep_bull['Low'] * 0.998 if not sweep_bull.empty else [],
            mode='markers',
            marker=dict(symbol='triangle-up', size=10, color='#00c48c'),
            name='Bull Sweep',
        ), row=1, col=1)

    if 'bear_sweep' in df_plot.columns:
        sweep_bear = df_plot[df_plot['bear_sweep'] == True]
        fig.add_trace(go.Scatter(
            x=x_axis[sweep_bear.index] if not sweep_bear.empty else [],
            y=sweep_bear['High'] * 1.002 if not sweep_bear.empty else [],
            mode='markers',
            marker=dict(symbol='triangle-down', size=10, color='#ff4d6d'),
            name='Bear Sweep',
        ), row=1, col=1)

    # BOS Bull lines
    if 'bos_bull' in df_plot.columns:
        bos_bull_idx = df_plot[df_plot['bos_bull'] == True].index
        for idx in bos_bull_idx:
            fig.add_vline(
                x=x_axis[idx],
                line_width=1.5, line_dash='dash',
                line_color='rgba(0,196,140,0.6)',
                annotation_text='BOS ▲',
                annotation_font_color='#00c48c',
                annotation_font_size=10,
            )

    # BOS Bear lines
    if 'bos_bear' in df_plot.columns:
        bos_bear_idx = df_plot[df_plot['bos_bear'] == True].index
        for idx in bos_bear_idx:
            fig.add_vline(
                x=x_axis[idx],
                line_width=1.5, line_dash='dash',
                line_color='rgba(255,77,109,0.6)',
                annotation_text='BOS ▼',
                annotation_font_color='#ff4d6d',
                annotation_font_size=10,
            )

    # CHOCH lines
    if 'choch_bull' in df_plot.columns:
        choch_bull_idx = df_plot[df_plot['choch_bull'] == True].index
        for idx in choch_bull_idx:
            fig.add_vline(
                x=x_axis[idx],
                line_width=2, line_dash='dot',
                line_color='rgba(124,92,191,0.8)',
                annotation_text='CHOCH ▲',
                annotation_font_color='#a07ee0',
                annotation_font_size=10,
            )

    if 'choch_bear' in df_plot.columns:
        choch_bear_idx = df_plot[df_plot['choch_bear'] == True].index
        for idx in choch_bear_idx:
            fig.add_vline(
                x=x_axis[idx],
                line_width=2, line_dash='dot',
                line_color='rgba(124,92,191,0.8)',
                annotation_text='CHOCH ▼',
                annotation_font_color='#a07ee0',
                annotation_font_size=10,
            )

    # Strong lows / highs
    if 'strong_low' in df_plot.columns:
        sl_rows = df_plot[df_plot['strong_low'] == True]
        for _, row_data in sl_rows.iterrows():
            fig.add_hline(
                y=row_data['Low'],
                line_width=1, line_dash='dot',
                line_color='rgba(0,196,140,0.4)',
            )

    if 'strong_high' in df_plot.columns:
        sh_rows = df_plot[df_plot['strong_high'] == True]
        for _, row_data in sh_rows.iterrows():
            fig.add_hline(
                y=row_data['High'],
                line_width=1, line_dash='dot',
                line_color='rgba(255,77,109,0.4)',
            )

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(13,13,26,0)',
        plot_bgcolor='rgba(13,13,26,0)',
        font=dict(family='Inter', color='#e8e8f0', size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            bgcolor='rgba(13,13,26,0.5)', bordercolor='rgba(74,144,217,0.3)',
        ),
        margin=dict(l=10, r=10, t=50, b=10),
        height=550,
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')

    return fig


def screener_page():
    # ─ Sidebar ─────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ SMC Screener v3.0")
        st.divider()

        if st.button("🏠 Voltar à Landing Page", key="btn_home"):
            st.session_state.page = 'landing'
            st.rerun()

        st.markdown("#### 🔍 Filtros")
        filter_type = st.selectbox(
            "Tipo de Sinal",
            ["Todos", "BOS", "CHOCH"],
            key="filter_type"
        )
        filter_dir = st.selectbox(
            "Direção",
            ["Todas", "Alta (Bull)", "Baixa (Bear)"],
            key="filter_dir"
        )
        filter_zone = st.selectbox(
            "Zona Fibonacci",
            ["Todas", "Discount", "Premium", "Reversal"],
            key="filter_zone"
        )

        st.divider()
        st.markdown("#### 📋 MTF Nota de Execução")
        st.markdown("""
        <div class="mtf-note">
        1. Aguarde o preço chegar ao POI no D1<br>
        2. Mude para LTF (15min/1min)<br>
        3. Espere CHOCH interno no LTF<br>
        4. Entre quando fluxo LTF alinhar com D1<br>
        5. SL: abaixo/acima do strong level<br>
        6. TP: próximo weak high/low oposto
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.session_state.last_run:
                st.caption(f"🕐 Última varredura:\n{st.session_state.last_run.strftime('%H:%M')}")
        with col_b:
            if st.button("🔄 Novo Scan", key="btn_rescan"):
                st.session_state.signals_df = None

    # ─ Header ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding: 20px 0 10px;">
        <h1 style="font-size:2rem;font-weight:800;
                   background:linear-gradient(135deg,#fff 0%,#a0bfe8 60%,#7c5cbf 100%);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;margin:0;">
            📈 SMC Screener — Sinais Ativos
        </h1>
        <p style="color:#8888aa;margin-top:6px;font-size:0.9rem;">
            Varredura Diária (D1) • Lógica ICT/SMC 2025-2026 • Apenas Estruturas com Sweep Confirmado
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─ Run screener ────────────────────────────────────────────────────────────
    if st.session_state.signals_df is None:
        with st.spinner("🔍 Varrendo 200+ ativos da B3... Aguarde (pode levar 1-3 minutos)"):
            try:
                signals = run_screener('tickers_b3.csv')
                st.session_state.signals_df = signals
                st.session_state.last_run = datetime.datetime.now()
            except Exception as e:
                st.error(f"Erro ao executar screener: {e}")
                st.session_state.signals_df = pd.DataFrame()

    signals_df = st.session_state.signals_df

    # ─ Apply filters ────────────────────────────────────────────────────────────
    filtered = signals_df.copy() if signals_df is not None and not signals_df.empty else pd.DataFrame()

    if not filtered.empty:
        if filter_type != "Todos":
            filtered = filtered[filtered['Tipo'] == filter_type]
        if filter_dir == "Alta (Bull)":
            filtered = filtered[filtered['Sinal'] == 'bull']
        elif filter_dir == "Baixa (Bear)":
            filtered = filtered[filtered['Sinal'] == 'bear']
        if filter_zone != "Todas":
            filtered = filtered[filtered['Zona'].str.title() == filter_zone]

    # ─ KPI metrics ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    total = len(filtered) if not filtered.empty else 0
    bull_count = len(filtered[filtered['Sinal'] == 'bull']) if not filtered.empty else 0
    bear_count = len(filtered[filtered['Sinal'] == 'bear']) if not filtered.empty else 0
    bos_count = len(filtered[filtered['Tipo'] == 'BOS']) if not filtered.empty else 0

    col1.metric("🎯 Sinais Totais", total)
    col2.metric("🟢 Alta (Bull)", bull_count)
    col3.metric("🔴 Baixa (Bear)", bear_count)
    col4.metric("📊 BOS", bos_count)

    st.divider()

    # ─ Table ────────────────────────────────────────────────────────────────────
    if filtered.empty:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:3rem;margin-bottom:16px;">🔍</div>
            <div style="font-size:1.2rem;color:#8888aa;">Nenhum sinal encontrado com os filtros aplicados.</div>
            <div style="font-size:0.85rem;color:#666688;margin-top:8px;">
                Tente alterar os filtros ou clique em "Novo Scan" para atualizar.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Style helper columns
        display_df = filtered.drop(columns=['Nota MTF'], errors='ignore').copy()

        # Format direction column for display
        if 'Sinal' in display_df.columns:
            display_df['Sinal'] = display_df['Sinal'].apply(
                lambda x: '🟢 Bull' if x == 'bull' else '🔴 Bear'
            )
        if 'Zona' in display_df.columns:
            display_df['Zona'] = display_df['Zona'].apply(
                lambda x: '🔵 Discount' if x == 'discount'
                else ('🟡 Premium' if x == 'premium'
                      else ('🟣 Reversal' if x == 'reversal' else x))
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(500, 80 + 38 * len(display_df)),
            hide_index=True,
        )

        st.caption(f"Exibindo {len(display_df)} sino(s) | última varredura: {st.session_state.last_run.strftime('%d/%m/%Y %H:%M') if st.session_state.last_run else '—'}")

        # ─ Chart section ──────────────────────────────────────────────────────
        st.divider()
        st.markdown("### 📊 Gráfico Interativo")

        tickers_available = filtered['Ticker'].unique().tolist() if not filtered.empty else []
        if tickers_available:
            selected_ticker = st.selectbox(
                "Selecione o ativo para visualizar",
                tickers_available,
                key="chart_ticker"
            )

            with st.spinner(f"Carregando gráfico de {selected_ticker}..."):
                try:
                    import yfinance as yf
                    df_raw = yf.download(
                        f"{selected_ticker}.SA",
                        period='6mo',
                        interval='1d',
                        progress=False,
                        auto_adjust=True
                    )
                    if isinstance(df_raw.columns, pd.MultiIndex):
                        df_raw.columns = df_raw.columns.get_level_values(0)
                    df_raw = df_raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    df_raw.dropna(inplace=True)
                    df_raw.reset_index(inplace=True)
                    df_raw.reset_index(drop=True, inplace=True)

                    from screener_logic import detect_smc_signals
                    df_analyzed = detect_smc_signals(df_raw)
                    fig = build_chart(df_analyzed, selected_ticker)
                    st.plotly_chart(fig, use_container_width=True)

                    # MTF note
                    mtf_row = filtered[filtered['Ticker'] == selected_ticker].iloc[0]
                    direction_label = "📈 Alta (Bull)" if mtf_row['Sinal'] in ['bull', '🟢 Bull'] else "📉 Baixa (Bear)"
                    tipo_label = mtf_row.get('Tipo', '—')
                    zona_label = mtf_row.get('Zona', '—')

                    st.markdown(f"""
                    <div class="mtf-note">
                        <strong>{selected_ticker}</strong> — {direction_label} | {tipo_label} | Zona: {zona_label}<br>
                        ⚠️ <em>Aguardar CHOCH interno no LTF (15min/1min) + alinhamento de fluxo antes de operar.</em>
                    </div>
                    """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {e}")


# ─── Router ─────────────────────────────────────────────────────────────────────
if st.session_state.page == 'landing':
    landing_page()
else:
    screener_page()
