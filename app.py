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

from screener_logic import run_screener, detect_smc_signals

# ─── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SMC Cloud Screener v3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

:root {
  --bg:        #07071a;
  --bg-mid:    #0d0d28;
  --bg-glass:  rgba(255,255,255,0.04);
  --bg-glass2: rgba(255,255,255,0.07);
  --accent:    #4f8ef7;
  --accent2:   #8b5cf6;
  --green:     #10d9a0;
  --red:       #f4436c;
  --gold:      #f5c842;
  --purple:    #a78bfa;
  --t1:        #f1f1fa;
  --t2:        #8b8baa;
  --t3:        #4a4a68;
  --border:    rgba(255,255,255,0.07);
  --border-a:  rgba(79,142,247,0.3);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--t1);
}

/* Remove Streamlit padding on landing */
.block-container {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer    { display: none !important; }

.stApp {
    background:
        radial-gradient(ellipse 90% 55% at 50% -5%,  rgba(79,142,247,0.10) 0%, transparent 65%),
        radial-gradient(ellipse 55% 45% at 85% 75%,  rgba(139,92,246,0.09) 0%, transparent 60%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-mid) 100%) !important;
    min-height: 100vh;
}

/* ══════════════════════════ NAVBAR ══════════════════════════ */
.lp-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 64px;
    background: rgba(7,7,26,0.88);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 999;
}
.lp-nav-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.3px;
    color: var(--t1);
}
.lp-nav-brand .accent {
    background: linear-gradient(90deg, var(--accent), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.lp-nav-pills {
    display: flex;
    gap: 8px;
    align-items: center;
}
.pill {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid var(--border);
    color: var(--t3);
}
.pill.blue   { color: var(--accent);  border-color: rgba(79,142,247,0.35); background: rgba(79,142,247,0.06); }
.pill.green  { color: var(--green);   border-color: rgba(16,217,160,0.35); background: rgba(16,217,160,0.06); }
.pill.purple { color: var(--purple);  border-color: rgba(167,139,250,0.35); background: rgba(167,139,250,0.06); }

/* ══════════════════════════ HERO ══════════════════════════ */
.lp-hero {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 60px;
    align-items: center;
    padding: 80px 64px 72px;
    max-width: 1360px;
    margin: 0 auto;
}
/* --- Hero Left --- */
.lp-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    color: var(--accent);
    background: rgba(79,142,247,0.08);
    border: 1px solid rgba(79,142,247,0.28);
    padding: 5px 14px;
    border-radius: 999px;
    margin-bottom: 24px;
}
.lp-h1 {
    font-size: 4rem;
    font-weight: 900;
    letter-spacing: -2px;
    line-height: 1.03;
    color: var(--t1);
    margin-bottom: 6px;
}
.lp-h1 .g {
    background: linear-gradient(130deg, #82b4ff 0%, #c4a4ff 50%, #82b4ff 100%);
    background-size: 200% auto;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shim 5s linear infinite;
}
@keyframes shim { to { background-position: 200% center; } }
.lp-version {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--t3);
    margin-bottom: 22px;
    display: block;
}
.lp-desc {
    font-size: 1.05rem;
    color: var(--t2);
    line-height: 1.78;
    max-width: 500px;
    margin-bottom: 40px;
}
.lp-desc strong { color: var(--t1); font-weight: 600; }
.lp-checks {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-bottom: 40px;
}
.lp-check {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.88rem;
    color: var(--t2);
}
.lp-check::before {
    content: '✓';
    width: 20px; height: 20px;
    border-radius: 6px;
    background: rgba(16,217,160,0.12);
    border: 1px solid rgba(16,217,160,0.3);
    color: var(--green);
    font-size: 0.72rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

/* --- Hero Right: Mock Panel --- */
.lp-panel {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 20px;
    overflow: hidden;
    backdrop-filter: blur(24px);
    box-shadow: 0 8px 48px rgba(0,0,0,0.35);
    position: relative;
}
.lp-panel::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(79,142,247,0.55) 40%, rgba(139,92,246,0.55) 60%, transparent 100%);
}
.lp-panel-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    background: rgba(255,255,255,0.02);
}
.lp-panel-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--t3);
}
.lp-live-badge {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.68rem; font-weight: 600; color: var(--green);
}
.lp-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--green);
    animation: blink 2s ease-in-out infinite;
}
@keyframes blink { 0%,100% {opacity:1} 50% {opacity:0.25} }
.lp-panel-body { padding: 14px 16px 10px; }
.lp-row {
    display: grid;
    grid-template-columns: 80px 64px 1fr 90px;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    margin-bottom: 6px;
    transition: background 0.15s;
}
.lp-row:hover { background: rgba(255,255,255,0.03); }
.tk { font-size: 0.9rem; font-weight: 800; color: var(--t1); }
.st { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.5px; padding: 3px 8px; border-radius: 5px; text-align: center; }
.st.bos   { color: var(--accent);  background: rgba(79,142,247,0.13);  }
.st.choch { color: var(--purple);  background: rgba(167,139,250,0.13); }
.dr { font-size: 0.75rem; font-weight: 600; }
.dr.up   { color: var(--green); }
.dr.dn   { color: var(--red);   }
.zn { font-size: 0.7rem; color: var(--t3); text-align: right; }
.lp-panel-foot {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    font-size: 0.7rem; color: var(--t3);
    background: rgba(255,255,255,0.02);
}

/* ══════════════════════════ STATS BAR ══════════════════════════ */
.lp-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    background: rgba(255,255,255,0.015);
}
.lp-stat {
    padding: 34px 16px;
    text-align: center;
    border-right: 1px solid var(--border);
    transition: background 0.2s;
    cursor: default;
}
.lp-stat:last-child { border-right: none; }
.lp-stat:hover { background: rgba(255,255,255,0.025); }
.lp-snum {
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: -1.5px;
    line-height: 1;
    background: linear-gradient(130deg, var(--accent), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    display: block;
    margin-bottom: 8px;
}
.lp-slabel {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--t3);
    margin-bottom: 4px;
}
.lp-ssub {
    font-size: 0.68rem;
    color: rgba(75,75,110,0.8);
}

/* ══════════════════════════ FEATURES ══════════════════════════ */
.lp-sec {
    padding: 72px 64px;
    max-width: 1360px;
    margin: 0 auto;
}
.lp-sec-head { text-align: center; margin-bottom: 52px; }
.lp-sec-ey {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--accent); margin-bottom: 12px;
}
.lp-sec-title {
    font-size: 2.1rem; font-weight: 800; letter-spacing: -0.6px;
    color: var(--t1); margin-bottom: 14px; line-height: 1.15;
}
.lp-sec-sub {
    font-size: 0.95rem; color: var(--t2); max-width: 580px;
    margin: 0 auto; line-height: 1.72;
}
.lp-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}
.lp-card {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 30px 28px;
    backdrop-filter: blur(20px);
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.lp-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-a);
    box-shadow: 0 18px 50px rgba(79,142,247,0.10);
}
.lp-card-glow {
    position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(ellipse 80% 60% at 50% -10%, rgba(79,142,247,0.06), transparent);
}
.lp-icon-wrap {
    width: 46px; height: 46px;
    border-radius: 13px;
    background: var(--bg-glass2);
    border: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
    margin-bottom: 20px;
}
.lp-card-title {
    font-size: 0.97rem; font-weight: 700; color: var(--t1); margin-bottom: 10px;
}
.lp-card-desc {
    font-size: 0.82rem; color: var(--t2); line-height: 1.65;
}
.lp-card-step {
    margin-top: 18px;
    font-size: 0.64rem; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: var(--accent); opacity: 0.6;
}

/* ══════════════════════════ WORKFLOW ══════════════════════════ */
.lp-flow-wrap {
    background: rgba(255,255,255,0.015);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    padding: 56px 64px;
}
.lp-flow-inner { max-width: 1360px; margin: 0 auto; }
.lp-flow-title {
    font-size: 1.35rem; font-weight: 800;
    letter-spacing: -0.4px; color: var(--t1);
    margin-bottom: 42px; text-align: center;
}
.lp-flow-title span { color: var(--accent); }
.lp-steps {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0;
    position: relative;
}
.lp-steps::before {
    content: '';
    position: absolute;
    top: 22px; left: 6%; right: 6%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-a) 20%, var(--border-a) 80%, transparent);
}
.lp-step { text-align: center; padding: 0 10px; }
.lp-step-circle {
    width: 44px; height: 44px;
    border-radius: 50%;
    background: var(--bg-mid);
    border: 1px solid var(--border-a);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 800; color: var(--accent);
    margin: 0 auto 16px;
    position: relative; z-index: 1;
}
.lp-step-name {
    font-size: 0.78rem; font-weight: 700; color: var(--t1);
    margin-bottom: 6px; line-height: 1.3;
}
.lp-step-desc {
    font-size: 0.67rem; color: var(--t3); line-height: 1.45;
}

/* ══════════════════════════ CTA BAND ══════════════════════════ */
.lp-cta {
    padding: 72px 64px;
    text-align: center;
    background:
        radial-gradient(ellipse 70% 80% at 50% 50%, rgba(79,142,247,0.06), transparent),
        var(--bg-mid);
    border-top: 1px solid var(--border);
}
.lp-cta-title {
    font-size: 2rem; font-weight: 800; letter-spacing: -0.6px;
    color: var(--t1); margin-bottom: 12px;
}
.lp-cta-sub {
    font-size: 0.95rem; color: var(--t2); margin-bottom: 36px; line-height: 1.7;
}
.lp-disclaimer {
    display: flex; align-items: flex-start; justify-content: center;
    gap: 10px;
    font-size: 0.74rem; color: rgba(245,200,66,0.55);
    background: rgba(245,200,66,0.035);
    border-top: 1px solid rgba(245,200,66,0.10);
    padding: 16px 32px;
    text-align: center;
    line-height: 1.65;
}

/* ══════════════════════════ SCREENER PAGE ══════════════════════════ */
.block-container.screener-page {
    padding: 24px 32px !important;
    max-width: 100% !important;
}
.mtf-note {
    background: rgba(79,142,247,0.07);
    border-left: 3px solid var(--accent);
    border-radius: 0 10px 10px 0;
    padding: 13px 18px;
    font-size: 0.83rem;
    color: var(--t2);
    margin-top: 14px;
    line-height: 1.65;
}
div[data-testid="metric-container"] {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
.stButton > button {
    background: linear-gradient(130deg, var(--accent) 0%, var(--accent2) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 13px 28px !important;
    transition: opacity 0.2s, transform 0.15s !important;
    width: 100% !important;
    letter-spacing: 0.2px;
}
.stButton > button:hover { opacity: 0.86 !important; transform: translateY(-1px) !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #07071a 0%, #0d0d28 100%) !important;
    border-right: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session state ───────────────────────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = 'landing'
if 'signals_df' not in st.session_state:
    st.session_state.signals_df = None
if 'last_run' not in st.session_state:
    st.session_state.last_run = None


# ─── Landing Page ────────────────────────────────────────────────────────────────
def landing_page():

    # ── 1. Navbar ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-nav">
        <div class="lp-nav-brand">
            📈&nbsp;&nbsp;<span class="accent">SMC Cloud Screener</span>
        </div>
        <div class="lp-nav-pills">
            <span class="pill blue">B3 · Bovespa</span>
            <span class="pill purple">ICT / SMC 2025–2026</span>
            <span class="pill green">● Ao Vivo</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 2. Hero ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-hero">

      <!-- LEFT -->
      <div>
        <div class="lp-eyebrow">⚡ Smart Money Concepts · Institucional</div>
        <div class="lp-h1">Screener SMC<br><span class="g">para a B3</span></div>
        <span class="lp-version">v3.0 &nbsp;·&nbsp; Dados: Yahoo Finance &nbsp;·&nbsp; Timeframe: D1</span>
        <div class="lp-desc">
          Varredura diária de <strong>200+ ativos</strong> com lógica institucional rigorosa.
          Apenas sinais com <strong>sweep de liquidez confirmado</strong> — sem Fake BOS, sem ruído.
        </div>
        <div class="lp-checks">
          <div class="lp-check">Liquidity Sweeps detectados com validação de wick</div>
          <div class="lp-check">BOS e CHOCH confirmados por fechamento de corpo</div>
          <div class="lp-check">Order Blocks + FVG como POIs de alta confluência</div>
          <div class="lp-check">Zonas Fibonacci Discount / Premium automáticas</div>
          <div class="lp-check">Nota MTF integrada ao resultado de cada sinal</div>
        </div>
      </div>

      <!-- RIGHT: Mock signal panel -->
      <div>
        <div class="lp-panel">
          <div class="lp-panel-bar">
            <span class="lp-panel-title">📊 Sinais Ativos — D1</span>
            <div class="lp-live-badge"><div class="lp-dot"></div> Atualizado hoje</div>
          </div>
          <div class="lp-panel-body">
            <div class="lp-row">
              <span class="tk">PETR4</span><span class="st bos">BOS</span><span class="dr up">▲ Alta</span><span class="zn">🔵 Discount</span>
            </div>
            <div class="lp-row">
              <span class="tk">VALE3</span><span class="st choch">CHOCH</span><span class="dr dn">▼ Baixa</span><span class="zn">🟡 Premium</span>
            </div>
            <div class="lp-row">
              <span class="tk">WEGE3</span><span class="st bos">BOS</span><span class="dr up">▲ Alta</span><span class="zn">🔵 Discount</span>
            </div>
            <div class="lp-row">
              <span class="tk">ITUB4</span><span class="st bos">BOS</span><span class="dr dn">▼ Baixa</span><span class="zn">🟡 Premium</span>
            </div>
            <div class="lp-row">
              <span class="tk">BBDC4</span><span class="st choch">CHOCH</span><span class="dr up">▲ Alta</span><span class="zn">🔵 Discount</span>
            </div>
          </div>
          <div class="lp-panel-foot">
            <span>200+ ativos escaneados</span>
            <span>yfinance · B3</span>
            <span>ICT/SMC 2025–2026</span>
          </div>
        </div>
      </div>

    </div>
    """, unsafe_allow_html=True)

    # ── 3. Stats Bar ────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-stats">
      <div class="lp-stat">
        <span class="lp-snum">200+</span>
        <div class="lp-slabel">Ativos Escaneados</div>
        <div class="lp-ssub">Ibovespa + Mais Líquidos B3</div>
      </div>
      <div class="lp-stat">
        <span class="lp-snum">D1</span>
        <div class="lp-slabel">Timeframe Diário</div>
        <div class="lp-ssub">2 anos de histórico via yfinance</div>
      </div>
      <div class="lp-stat">
        <span class="lp-snum">6</span>
        <div class="lp-slabel">Camadas de Validação</div>
        <div class="lp-ssub">Sweep · BOS · OB · FVG · Fib · MTF</div>
      </div>
      <div class="lp-stat">
        <span class="lp-snum">0%</span>
        <div class="lp-slabel">Fake BOS</div>
        <div class="lp-ssub">Sweep prévio sempre obrigatório</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 4. Feature Cards ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-sec">
      <div class="lp-sec-head">
        <div class="lp-sec-ey">Metodologia</div>
        <div class="lp-sec-title">Lógica SMC Rigorosa · Sem Exceções</div>
        <div class="lp-sec-sub">
          Cada sinal passa por 6 camadas de validação antes de chegar à tabela.
          Estruturas fracas são descartadas automaticamente.
        </div>
      </div>
      <div class="lp-grid">

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">💧</div>
          <div class="lp-card-title">Liquidity Sweeps</div>
          <div class="lp-card-desc">Detecta varreduras de liquidez que validam topos e fundos fortes. Confirmado por wick. Estruturas sem sweep são descartadas.</div>
          <div class="lp-card-step">→ Passo 1</div>
        </div>

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">🏗️</div>
          <div class="lp-card-title">Strong High / Low</div>
          <div class="lp-card-desc">Identifica estruturas protegidas por sweep prévio. Apenas níveis protegidos servem de referência para BOS e CHOCH.</div>
          <div class="lp-card-step">→ Passo 2</div>
        </div>

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">🎯</div>
          <div class="lp-card-title">BOS &amp; CHOCH</div>
          <div class="lp-card-desc">Break of Structure (continuação) e Change of Character (reversão). Validados obrigatoriamente por fechamento de corpo de vela.</div>
          <div class="lp-card-step">→ Passo 3</div>
        </div>

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">📐</div>
          <div class="lp-card-title">Fibonacci 50%</div>
          <div class="lp-card-desc">Zonas de Discount (compras abaixo de 50%) e Premium (vendas acima). Filtro de entrada de alta probabilidade sobre a pernada impulsiva.</div>
          <div class="lp-card-step">→ Passo 4</div>
        </div>

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">🧱</div>
          <div class="lp-card-title">Order Blocks + FVG</div>
          <div class="lp-card-desc">Última vela contrária antes do impulso. Priorizados quando coincidem com Fair Value Gap (3 velas) para máxima confluência.</div>
          <div class="lp-card-step">→ Passo 5</div>
        </div>

        <div class="lp-card">
          <div class="lp-card-glow"></div>
          <div class="lp-icon-wrap">📊</div>
          <div class="lp-card-title">Gráfico Interativo</div>
          <div class="lp-card-desc">Candlestick Plotly com marcações visuais de sweeps, BOS/CHOCH, strong levels, Order Blocks e zonas Fibonacci em tempo real.</div>
          <div class="lp-card-step">→ Visualização</div>
        </div>

      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5. MTF Workflow ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-flow-wrap">
      <div class="lp-flow-inner">
        <div class="lp-flow-title">Fluxo de Execução <span>Multi-Timeframe</span></div>
        <div class="lp-steps">
          <div class="lp-step">
            <div class="lp-step-circle">01</div>
            <div class="lp-step-name">Sinal no D1</div>
            <div class="lp-step-desc">BOS ou CHOCH com close de corpo confirmado</div>
          </div>
          <div class="lp-step">
            <div class="lp-step-circle">02</div>
            <div class="lp-step-name">POI Mapeado</div>
            <div class="lp-step-desc">OB, FVG ou Fibonacci 50% como zona de interesse</div>
          </div>
          <div class="lp-step">
            <div class="lp-step-circle">03</div>
            <div class="lp-step-name">Aguarde o Preço</div>
            <div class="lp-step-desc">Espere retorno ao POI no D1 sem antecipar</div>
          </div>
          <div class="lp-step">
            <div class="lp-step-circle">04</div>
            <div class="lp-step-name">Confirme no LTF</div>
            <div class="lp-step-desc">CHOCH interno no 15min ou 1min como gatilho</div>
          </div>
          <div class="lp-step">
            <div class="lp-step-circle">05</div>
            <div class="lp-step-name">Entrada e SL</div>
            <div class="lp-step-desc">Início do OB. SL abaixo / acima do strong level</div>
          </div>
          <div class="lp-step">
            <div class="lp-step-circle">06</div>
            <div class="lp-step-name">Alvo e Parciais</div>
            <div class="lp-step-desc">TP no weak high/low. Parcial no 1º alvo</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 6. CTA Band ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-cta">
        <div class="lp-cta-title">Pronto para encontrar os próximos sinais?</div>
        <div class="lp-cta-sub">
            A varredura leva entre 1 e 3 minutos e cobre 200+ ativos da B3.<br>
            Resultados filtráveis por tipo de sinal, direção e zona Fibonacci.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA Button via Streamlit ─────────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([3, 2, 3])
    with col_c:
        if st.button("🚀  Iniciar Screener Agora", key="btn_start"):
            st.session_state.page = 'screener'
            st.rerun()

    # ── Disclaimer ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="lp-disclaimer">
        ⚠️&nbsp; <strong>Isenção de Responsabilidade:</strong>&nbsp;
        Este screener é exclusivamente uma ferramenta de análise técnica. Não constitui aconselhamento financeiro,
        recomendação de investimento ou oferta de valores mobiliários.
        Sempre realize sua própria análise e consulte um profissional habilitado antes de operar.
    </div>
    """, unsafe_allow_html=True)


# ─── Chart Builder ───────────────────────────────────────────────────────────────
def build_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    df_plot = df.tail(120).copy().reset_index(drop=True)

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

    fig.add_trace(go.Candlestick(
        x=x_axis,
        open=df_plot['Open'], high=df_plot['High'],
        low=df_plot['Low'], close=df_plot['Close'],
        name='Preço',
        increasing_line_color='#10d9a0', decreasing_line_color='#f4436c',
        increasing_fillcolor='rgba(16,217,160,0.7)',
        decreasing_fillcolor='rgba(244,67,108,0.7)',
    ), row=1, col=1)

    colors_vol = ['#10d9a0' if c >= o else '#f4436c'
                  for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(
        x=x_axis, y=df_plot['Volume'],
        name='Volume', marker_color=colors_vol, opacity=0.55,
    ), row=2, col=1)

    for col_name, label, color, dash in [
        ('bos_bull',   'BOS ▲',   'rgba(16,217,160,0.65)', 'dash'),
        ('bos_bear',   'BOS ▼',   'rgba(244,67,108,0.65)', 'dash'),
        ('choch_bull', 'CHOCH ▲', 'rgba(167,139,250,0.8)', 'dot'),
        ('choch_bear', 'CHOCH ▼', 'rgba(167,139,250,0.8)', 'dot'),
    ]:
        if col_name in df_plot.columns:
            for idx in df_plot[df_plot[col_name] == True].index:
                fig.add_vline(
                    x=x_axis[idx], line_width=1.5, line_dash=dash,
                    line_color=color,
                    annotation_text=label,
                    annotation_font_color=color, annotation_font_size=10,
                )

    if 'bull_sweep' in df_plot.columns:
        sw = df_plot[df_plot['bull_sweep'] == True]
        if not sw.empty:
            fig.add_trace(go.Scatter(
                x=[x_axis[i] for i in sw.index], y=sw['Low'] * 0.9975,
                mode='markers', marker=dict(symbol='triangle-up', size=10, color='#10d9a0'),
                name='Bull Sweep',
            ), row=1, col=1)

    if 'bear_sweep' in df_plot.columns:
        sw = df_plot[df_plot['bear_sweep'] == True]
        if not sw.empty:
            fig.add_trace(go.Scatter(
                x=[x_axis[i] for i in sw.index], y=sw['High'] * 1.0025,
                mode='markers', marker=dict(symbol='triangle-down', size=10, color='#f4436c'),
                name='Bear Sweep',
            ), row=1, col=1)

    if 'strong_low' in df_plot.columns:
        for _, r in df_plot[df_plot['strong_low'] == True].iterrows():
            fig.add_hline(y=r['Low'], line_width=1, line_dash='dot', line_color='rgba(16,217,160,0.3)')

    if 'strong_high' in df_plot.columns:
        for _, r in df_plot[df_plot['strong_high'] == True].iterrows():
            fig.add_hline(y=r['High'], line_width=1, line_dash='dot', line_color='rgba(244,67,108,0.3)')

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(7,7,26,0)',
        plot_bgcolor='rgba(7,7,26,0)',
        font=dict(family='Inter', color='#f1f1fa', size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    bgcolor='rgba(7,7,26,0.5)', bordercolor='rgba(79,142,247,0.25)'),
        margin=dict(l=10, r=10, t=50, b=10),
        height=560,
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
    return fig


# ─── Screener Page ───────────────────────────────────────────────────────────────
def screener_page():
    with st.sidebar:
        st.markdown("### ⚙️ SMC Screener v3.0")
        st.divider()

        if st.button("🏠 Voltar à Landing Page", key="btn_home"):
            st.session_state.page = 'landing'
            st.rerun()

        st.markdown("#### 🔍 Filtros")
        filter_type = st.selectbox("Tipo de Sinal", ["Todos", "BOS", "CHOCH"], key="filter_type")
        filter_dir  = st.selectbox("Direção", ["Todas", "Alta (Bull)", "Baixa (Bear)"], key="filter_dir")
        filter_zone = st.selectbox("Zona Fibonacci", ["Todas", "Discount", "Premium", "Reversal"], key="filter_zone")

        st.divider()
        st.markdown("#### 📋 MTF Nota de Execução")
        st.markdown("""
        <div class="mtf-note">
        1. Aguarde o preço chegar ao POI no D1<br>
        2. Mude para LTF (15min / 1min)<br>
        3. Espere CHOCH interno no LTF<br>
        4. Entre quando fluxo LTF alinhar com D1<br>
        5. SL: abaixo / acima do strong level<br>
        6. TP: próximo weak high / low oposto
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        if st.session_state.last_run:
            st.caption(f"🕐 Última varredura: {st.session_state.last_run.strftime('%d/%m %H:%M')}")
        if st.button("🔄 Novo Scan", key="btn_rescan"):
            st.session_state.signals_df = None

    st.markdown("""
    <div style="padding:20px 0 10px;">
        <h1 style="font-size:1.9rem;font-weight:800;letter-spacing:-0.5px;
                   background:linear-gradient(130deg,#f1f1fa,#8b8baa);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;margin:0;">
            📈 SMC Screener &mdash; Sinais Ativos
        </h1>
        <p style="color:#4a4a68;margin-top:6px;font-size:0.85rem;">
            Varredura Diária (D1) · Lógica ICT/SMC 2025-2026 · Apenas Estruturas com Sweep Confirmado
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.signals_df is None:
        with st.spinner("🔍 Varrendo 200+ ativos da B3... Aguarde (1-3 minutos)"):
            try:
                signals = run_screener('tickers_b3.csv')
                st.session_state.signals_df = signals
                st.session_state.last_run = datetime.datetime.now()
            except Exception as e:
                st.error(f"Erro ao executar screener: {e}")
                st.session_state.signals_df = pd.DataFrame()

    signals_df = st.session_state.signals_df
    filtered = signals_df.copy() if signals_df is not None and not signals_df.empty else pd.DataFrame()

    if not filtered.empty:
        if filter_type != "Todos":
            filtered = filtered[filtered['Tipo'] == filter_type]
        if filter_dir == "Alta (Bull)":
            filtered = filtered[filtered['Sinal'] == 'bull']
        elif filter_dir == "Baixa (Bear)":
            filtered = filtered[filtered['Sinal'] == 'bear']
        if filter_zone != "Todas":
            zone_map = {'Discount': 'discount', 'Premium': 'premium', 'Reversal': 'reversal'}
            filtered = filtered[filtered['Zona'] == zone_map.get(filter_zone, filter_zone)]

    col1, col2, col3, col4 = st.columns(4)
    total      = len(filtered) if not filtered.empty else 0
    bull_count = len(filtered[filtered['Sinal'] == 'bull']) if not filtered.empty else 0
    bear_count = len(filtered[filtered['Sinal'] == 'bear']) if not filtered.empty else 0
    bos_count  = len(filtered[filtered['Tipo']  == 'BOS'])  if not filtered.empty else 0

    col1.metric("🎯 Sinais Totais", total)
    col2.metric("🟢 Alta (Bull)",   bull_count)
    col3.metric("🔴 Baixa (Bear)",  bear_count)
    col4.metric("📊 BOS",           bos_count)

    st.divider()

    if filtered.empty:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:2.8rem;margin-bottom:16px;">🔍</div>
            <div style="font-size:1.1rem;color:#8b8baa;">Nenhum sinal encontrado com os filtros aplicados.</div>
            <div style="font-size:0.82rem;color:#4a4a68;margin-top:8px;">
                Tente alterar os filtros ou clique em "Novo Scan" para atualizar.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        display_df = filtered.drop(columns=['Nota MTF'], errors='ignore').copy()
        if 'Sinal' in display_df.columns:
            display_df['Sinal'] = display_df['Sinal'].apply(
                lambda x: '🟢 Bull' if x == 'bull' else '🔴 Bear')
        if 'Zona' in display_df.columns:
            display_df['Zona'] = display_df['Zona'].apply(
                lambda x: '🔵 Discount' if x == 'discount'
                else ('🟡 Premium' if x == 'premium'
                      else ('🟣 Reversal' if x == 'reversal' else x or '—')))

        st.dataframe(display_df, use_container_width=True,
                     height=min(520, 80 + 38 * len(display_df)), hide_index=True)
        st.caption(f"Exibindo {len(display_df)} sinal(is) | "
                   f"última varredura: {st.session_state.last_run.strftime('%d/%m/%Y %H:%M') if st.session_state.last_run else '—'}")

        st.divider()
        st.markdown("### 📊 Gráfico Interativo")
        tickers_available = filtered['Ticker'].unique().tolist()
        if tickers_available:
            selected_ticker = st.selectbox("Selecione o ativo", tickers_available, key="chart_ticker")
            with st.spinner(f"Carregando gráfico de {selected_ticker}..."):
                try:
                    import yfinance as yf
                    df_raw = yf.download(f"{selected_ticker}.SA", period='6mo', interval='1d',
                                         progress=False, auto_adjust=True)
                    if isinstance(df_raw.columns, pd.MultiIndex):
                        df_raw.columns = df_raw.columns.get_level_values(0)
                    df_raw = df_raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    df_raw.dropna(inplace=True)
                    df_raw.reset_index(inplace=True)
                    df_raw.reset_index(drop=True, inplace=True)
                    df_analyzed = detect_smc_signals(df_raw)
                    fig = build_chart(df_analyzed, selected_ticker)
                    st.plotly_chart(fig, use_container_width=True)

                    mtf_row = filtered[filtered['Ticker'] == selected_ticker].iloc[0]
                    direction_label = "📈 Alta (Bull)" if mtf_row['Sinal'] == 'bull' else "📉 Baixa (Bear)"
                    st.markdown(f"""
                    <div class="mtf-note">
                        <strong>{selected_ticker}</strong> — {direction_label}
                        | {mtf_row.get('Tipo', '—')} | Zona: {mtf_row.get('Zona', '—')}<br>
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
