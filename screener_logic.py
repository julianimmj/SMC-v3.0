"""
SMC Cloud Screener v3.0 - Complete Logic (Refatoção Rigorosa SMC)
Liquidity Sweeps + Strong Structures + BOS/CHOCH + Fibonacci + Order Blocks + FVG
"""

import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')


def download_data_batch(tickers: list, period: str = '2y', interval: str = '1d') -> dict:
    """Download data using yfinance in small batches to avoid rate limiting on cloud IPs."""
    import time
    data = {}
    BATCH_SIZE = 25
    DELAY = 2  # segundos entre batches

    for batch_start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[batch_start : batch_start + BATCH_SIZE]
        
        for attempt in range(3):  # até 3 tentativas por batch
            try:
                df_batch = yf.download(
                    batch, period=period, interval=interval,
                    group_by='ticker', progress=False, auto_adjust=True
                )
                
                if df_batch is None or df_batch.empty:
                    break

                for ticker in batch:
                    try:
                        if len(batch) > 1:
                            if isinstance(df_batch.columns, pd.MultiIndex) and ticker in df_batch.columns.get_level_values(0):
                                df = df_batch[ticker].copy()
                            else:
                                continue
                        else:
                            df = df_batch.copy()
                            if isinstance(df.columns, pd.MultiIndex):
                                df.columns = df.columns.get_level_values(0)

                        df.dropna(inplace=True)
                        if df.empty:
                            continue

                        df.reset_index(inplace=True)
                        if 'Date' not in df.columns and 'Datetime' in df.columns:
                            df.rename(columns={'Datetime': 'Date'}, inplace=True)
                        if 'Date' not in df.columns and df.index.name == 'Date':
                            df.reset_index(inplace=True)

                        df.reset_index(drop=True, inplace=True)
                        data[ticker] = df
                    except Exception:
                        continue

                break  # batch OK, sai do retry loop

            except Exception as e:
                if 'Rate' in str(e) or '429' in str(e):
                    time.sleep(DELAY * (attempt + 2))  # backoff progressivo
                else:
                    break

        # Delay entre batches
        if batch_start + BATCH_SIZE < len(tickers):
            time.sleep(DELAY)

    return data


def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Identify swing highs and lows using rolling window (no look-ahead bias)."""
    df = df.copy()
    half = window // 2

    # center=True alinha a janela simetricamente; min_periods evita NaN nos extremos
    rolling_max = df['High'].rolling(window=window, center=True, min_periods=half + 1).max()
    rolling_min = df['Low'].rolling(window=window, center=True, min_periods=half + 1).min()

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

    # Bull sweep: wick goes below previous swing low + wraps back up (avoids marking pure dumps as sweeps)
    df['bull_sweep'] = (
        (df['Low'] < df['prev_swing_low']) &
        (df['Close'] > df['prev_swing_low']) 
    )

    # Bear sweep: wick goes above previous swing high + wraps back down
    df['bear_sweep'] = (
        (df['High'] > df['prev_swing_high']) &
        (df['Close'] < df['prev_swing_high'])
    )

    return df


def map_market_structure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rastrea rigorosamente 200+ candles como uma Máquina de Estado.
    Define Strong/Weak pontos ativamente baseados em Sweeps prévios e Quebras Corporais (Closes).
    Fake BOS (sem sweep prévio) é ignorado e não reposiciona os pontos fortes da estrutura.
    """
    df = detect_liquidity_sweeps(df)
    
    df['bos_bull'] = False
    df['bos_bear'] = False
    df['choch_bull'] = False
    df['choch_bear'] = False
    
    df['active_strong_low'] = np.nan
    df['active_strong_low_idx'] = np.nan
    df['active_strong_high'] = np.nan
    df['active_strong_high_idx'] = np.nan
    
    trend = 0  # 1 = Bull, -1 = Bear
    CANDIDATE_TTL = 200  # Máximo de candles que um candidato permanece válido (~10 meses D1)
    
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
            
        # Expirar candidatos antigos (TTL)
        if candidate_low is not None and (i - candidate_low[1]) > CANDIDATE_TTL:
            candidate_low = None
        if candidate_high is not None and (i - candidate_high[1]) > CANDIDATE_TTL:
            candidate_high = None

        # Avalia varreduras -> Criam candidatos a Pontos Fortes
        if df.loc[i, 'bull_sweep']:
            if candidate_low is None or cur_low < candidate_low[0]:
                candidate_low = (cur_low, i)
        elif candidate_low is not None and cur_low <= candidate_low[0]:
            candidate_low = (cur_low, i)  # Renova se a puxada continua

        if df.loc[i, 'bear_sweep']:
            if candidate_high is None or cur_high > candidate_high[0]:
                candidate_high = (cur_high, i)
        elif candidate_high is not None and cur_high >= candidate_high[0]:
            candidate_high = (cur_high, i)

        # ═══ Valida Quebras Estruturais (Close vs extremos do candle ANTERIOR) ═══
        # recent_high/recent_low ainda refletem o extremo até o candle i-1
        if trend == 1:
            # CHOCH de Baixa: Perde o verdadeiro Strong Low ativo
            if strong_low is not None and cur_close < strong_low[0]:
                df.loc[i, 'choch_bear'] = True
                trend = -1
                strong_high = candidate_high if candidate_high is not None else (recent_high, df.loc[:i, 'High'].idxmax())
                candidate_low = None
                recent_low = cur_low 
                recent_high = cur_high
                
            # BOS de Alta: Close rompe o topo da perna anterior
            elif cur_close > recent_high and candidate_low is not None:
                df.loc[i, 'bos_bull'] = True
                strong_low = candidate_low
                candidate_low = None
                recent_high = cur_high
                recent_low = strong_low[0]
                
        elif trend == -1:
            # CHOCH de Alta: Rompe acima do verdadeiro Strong High ativo
            if strong_high is not None and cur_close > strong_high[0]:
                df.loc[i, 'choch_bull'] = True
                trend = 1
                strong_low = candidate_low if candidate_low is not None else (recent_low, df.loc[:i, 'Low'].idxmin())
                candidate_high = None
                recent_high = cur_high
                recent_low = cur_low
                
            # BOS de Baixa: Close perde o fundo da perna anterior
            elif cur_close < recent_low and candidate_high is not None:
                df.loc[i, 'bos_bear'] = True
                strong_high = candidate_high
                candidate_high = None
                recent_low = cur_low
                recent_high = strong_high[0]
                
        else: # Estado Inicial -> Esperando a primeira estrutura
            if cur_close > recent_high:
                trend = 1
                df.loc[i, 'choch_bull'] = True
                if candidate_low is not None:
                    strong_low = candidate_low
                    candidate_low = None
                else:
                    min_idx = df.loc[:i, 'Low'].idxmin()
                    strong_low = (df.loc[min_idx, 'Low'], min_idx)
                recent_high = cur_high
                recent_low = cur_low
            elif cur_close < recent_low:
                trend = -1
                df.loc[i, 'choch_bear'] = True
                if candidate_high is not None:
                    strong_high = candidate_high
                    candidate_high = None
                else:
                    max_idx = df.loc[:i, 'High'].idxmax()
                    strong_high = (df.loc[max_idx, 'High'], max_idx)
                recent_low = cur_low
                recent_high = cur_high

        # ═══ SÓ DEPOIS dos checks: atualiza os extremos para o próximo candle ═══
        if cur_high > recent_high:
            recent_high = cur_high
        if cur_low < recent_low:
            recent_low = cur_low

        # Anexa estado aos frames
        if strong_low is not None:
            df.loc[i, 'active_strong_low'] = strong_low[0]
            df.loc[i, 'active_strong_low_idx'] = strong_low[1]
        if strong_high is not None:
            df.loc[i, 'active_strong_high'] = strong_high[0]
            df.loc[i, 'active_strong_high_idx'] = strong_high[1]
            
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


def find_order_blocks(df: pd.DataFrame, start_idx: int, end_idx: int, direction: str) -> pd.DataFrame:
    """Encontra os últimos Order Blocks institucionais APENAS dentro da pernada definida."""
    blocks = []
    # Proteção de limite
    start_idx = max(0, start_idx)
    end_idx = min(len(df)-1, max(start_idx+1, end_idx))
    
    for i in range(start_idx, end_idx):
        if direction == 'bull':
            # OB bullish = ultimos candles vermelhos acumulativos antes do empurrão
            if df.loc[i, 'Close'] < df.loc[i, 'Open']:
                blocks.append({
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bearish'
                })
        else:
            # OB bearish = últimos candles verdes acumulativos antes do drop
            if df.loc[i, 'Close'] > df.loc[i, 'Open']:
                blocks.append({
                    'idx': i,
                    'high': df.loc[i, 'High'],
                    'low': df.loc[i, 'Low'],
                    'close': df.loc[i, 'Close'],
                    'color': 'bullish'
                })
    return pd.DataFrame(blocks)


def find_fvg(df: pd.DataFrame, start_idx: int, end_idx: int) -> list:
    """Encontra FVGs reais em um range estrutural (3 candles de imbalance)."""
    fvgs = []
    start_idx = max(1, start_idx)
    end_idx = min(len(df)-1, max(start_idx+1, end_idx))
    
    for i in range(start_idx, end_idx):
        high_n_minus1 = df.loc[i - 1, 'High']
        low_n_minus1 = df.loc[i - 1, 'Low']
        high_n_plus1 = df.loc[i + 1, 'High']
        low_n_plus1 = df.loc[i + 1, 'Low']

        # Imbalance de Alta (FVG Bullish): O topo do candle anterior nem trisca no fundo do próximo
        if high_n_minus1 < low_n_plus1:
            fvgs.append({
                'type': 'bullish',
                'top': low_n_plus1,
                'bottom': high_n_minus1,
                'mid': (low_n_plus1 + high_n_minus1) / 2,
                'idx': i
            })

        # Imbalance de Baixa (FVG Bearish)
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
    """Função principal que aplica a malha fina aos sinais baseados em Smart Money."""
    df = map_market_structure(df)

    df['signal'] = None
    df['signal_type'] = None
    df['poi_type'] = None
    df['poi_price'] = np.nan
    df['zone'] = None
    df['sl_price'] = np.nan
    df['tp1_price'] = np.nan
    df['fib_50'] = np.nan
    df['mtf_note'] = None
    
    # Flags para a visualização do Gráfico no app.py
    df['strong_low'] = False
    df['strong_high'] = False

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

        # == Cenário COMPRA ==
        if signal_dir == 'bull':
            # Ponto de origem absoluto do forte movimento
            sl_val = df.loc[i, 'active_strong_low']
            if pd.isna(df.loc[i, 'active_strong_low_idx']):
                continue
            sl_idx = int(df.loc[i, 'active_strong_low_idx'])
            
            # Marca para plotagem correta
            df.loc[sl_idx, 'strong_low'] = True

            # Ápice do movimento ATÉ o candle do sinal (sem look-ahead)
            top_val = df['High'].iloc[sl_idx : i + 1].max()
            top_idx = df['High'].iloc[sl_idx : i + 1].idxmax()
            
            if top_val <= sl_val:
                continue

            fib = calculate_fibonacci(sl_val, top_val)
            fib_50 = fib['0.5']
            
            order_blocks = find_order_blocks(df, sl_idx, top_idx, signal_dir)
            fvgs = find_fvg(df, sl_idx, top_idx)
            
            poi_price = None
            poi_type = None

            # Condição SMC: O POI M-U-S-T estar na zona Discount (< 50%) para compras.
            if not order_blocks.empty:
                discount_obs = order_blocks[order_blocks['low'] < fib_50]
                if not discount_obs.empty:
                    ob = discount_obs.iloc[-1]
                    poi_price = (ob['high'] + ob['low']) / 2
                    poi_type = 'Order Block'

            if poi_price is None:
                for fvg in reversed(fvgs):
                    if fvg['type'] == 'bullish' and fvg['mid'] < fib_50:
                        poi_price = fvg['mid']
                        poi_type = 'FVG'
                        break

            if poi_price is None:
                poi_price = fib_50
                poi_type = 'Fib 50%'

            sl_price = sl_val * 0.999 # O SL é matemático abaixo do fundo forte
            # TP projeta ACIMA do topo atual via Fibonacci -0.272 extension
            fib_range = top_val - sl_val
            tp1_price = top_val + fib_range * 0.272  # ~27% além do topo
            
        # == Cenário VENDA ==
        else: 
            sh_val = df.loc[i, 'active_strong_high']
            if pd.isna(df.loc[i, 'active_strong_high_idx']):
                continue
            sh_idx = int(df.loc[i, 'active_strong_high_idx'])
            
            # Marca para plotagem
            df.loc[sh_idx, 'strong_high'] = True
            
            # Ponto fraco pra ser mitigado (até o candle do sinal, sem look-ahead)
            bot_val = df['Low'].iloc[sh_idx : i + 1].min()
            bot_idx = df['Low'].iloc[sh_idx : i + 1].idxmin()
            
            if bot_val >= sh_val:
                continue

            fib = calculate_fibonacci(sh_val, bot_val)
            fib_50 = fib['0.5']
            
            order_blocks = find_order_blocks(df, sh_idx, bot_idx, signal_dir)
            fvgs = find_fvg(df, sh_idx, bot_idx)
            
            poi_price = None
            poi_type = None

            # Condição SMC: O POI tem que estar Premium (> 50%) para vendas.
            if not order_blocks.empty:
                premium_obs = order_blocks[order_blocks['high'] > fib_50]
                if not premium_obs.empty:
                    ob = premium_obs.iloc[-1]
                    poi_price = (ob['high'] + ob['low']) / 2
                    poi_type = 'Order Block'

            if poi_price is None:
                for fvg in reversed(fvgs):
                    if fvg['type'] == 'bearish' and fvg['mid'] > fib_50:
                        poi_price = fvg['mid']
                        poi_type = 'FVG'
                        break

            if poi_price is None:
                poi_price = fib_50
                poi_type = 'Fib 50%'

            sl_price = sh_val * 1.001 # Protegido de liquidação acidental no High
            # TP projeta ABAIXO do fundo atual via Fibonacci -0.272 extension
            fib_range = sh_val - bot_val
            tp1_price = bot_val - fib_range * 0.272  # ~27% além do fundo

        # Atribuição da Zona com base no preço DE HOJE
        current_price = df.loc[i, 'Close']
        if signal_dir == 'bull':
            zone = 'discount' if current_price <= fib_50 else 'premium'
        else:
            zone = 'premium' if current_price >= fib_50 else 'discount'

        df.loc[i, 'signal'] = signal_dir
        df.loc[i, 'signal_type'] = signal_type
        df.loc[i, 'poi_type'] = poi_type
        df.loc[i, 'poi_price'] = round(float(poi_price), 2)
        df.loc[i, 'zone'] = zone
        df.loc[i, 'sl_price'] = round(float(sl_price), 2)
        df.loc[i, 'tp1_price'] = round(float(tp1_price), 2)
        df.loc[i, 'fib_50'] = round(float(fib_50), 2)
        df.loc[i, 'mtf_note'] = 'Aguardar CHOCH interno LTF no M15 para confirmar absorção'

    df.drop(columns=['active_strong_low_idx', 'active_strong_high_idx', 'active_strong_low', 'active_strong_high'], errors='ignore', inplace=True)
    return df


def get_latest_signals(df: pd.DataFrame, lookback: int = 15) -> pd.DataFrame:
    """Extrai os últimos sinais relevantes para display rápido."""
    signals = df[df['signal'].notna()].tail(lookback)
    return signals


def run_screener(tickers_file: str = 'tickers_b3.csv') -> pd.DataFrame:
    """Varre todos os tickets da bolsa passando o rigor de RR e SL."""
    try:
        tickers_df = pd.read_csv(tickers_file)
        # Deduplica ativos
        tickers = list(set([f"{t}.SA" for t in tickers_df['ticker'].dropna()]))
    except Exception as e:
        print(f"Erro ao ler tickers: {e}")
        return pd.DataFrame()

    print(f"Baixando dados retrospectivos de {len(tickers)} ativos...")
    data = download_data_batch(tickers)

    all_signals = []

    print("Submetendo os ativos ao Smart Money Concepts Algoritmo...")
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
                    last_close = float(df['Close'].iloc[-1])
                    poi = latest.get('poi_price')
                    sl = latest.get('sl_price')
                    tp1 = latest.get('tp1_price')

                    if pd.isna(poi) or pd.isna(sl) or pd.isna(tp1):
                        continue

                    # Filtro severo de Invalidação pós-signal (Stop-Out Dinâmico + TP Atingido + Expiração)
                    signal_idx = latest.name
                    
                    # Se o sinal é muito antigo (prescrito), ignora (usamos 100 dias úteis como trava máxima de segurança)
                    if (len(df) - 1) - df.index.get_loc(signal_idx) > 100:
                        continue

                    if latest['signal'] == 'bull':
                        if poi <= sl: continue # Protecao matemática 
                        if df.loc[signal_idx:, 'Low'].min() <= sl * 1.005: continue # Stop-Out (0.5% tolerância)
                        if df.loc[signal_idx:, 'High'].max() >= tp1 * 0.995: continue # Target-Hit (0.5% tolerância)
                        if last_close >= tp1: continue  # Preço atual já superou o alvo
                        risk = abs(poi - sl)
                        reward = abs(tp1 - poi)
                    else: # bear
                        if poi >= sl: continue
                        if df.loc[signal_idx:, 'High'].max() >= sl * 0.995: continue # Stop-Out (0.5% tolerância)
                        if df.loc[signal_idx:, 'Low'].min() <= tp1 * 1.005: continue # Target-Hit (0.5% tolerância)
                        if last_close <= tp1: continue  # Preço atual já estourou o alvo
                        risk = abs(sl - poi)
                        reward = abs(poi - tp1)

                    rr = round(reward / risk, 2) if risk > 0 else 0

                    # Recalcula Zona Fibonacci com o preço de hoje
                    fib_50_val = latest.get('fib_50')
                    if pd.notna(fib_50_val):
                        fib_50_val = float(fib_50_val)
                        if latest['signal'] == 'bull':
                            zone = 'discount' if last_close <= fib_50_val else 'premium'
                        else:
                            zone = 'premium' if last_close >= fib_50_val else 'discount'
                    else:
                        zone = latest.get('zone')

                    # Distância do preço atual ao POI (%)
                    dist_poi = round(((last_close - poi) / poi) * 100, 1)

                    all_signals.append({
                        'Ticker': ticker_clean,
                        'Sinal': latest['signal'],
                        'Tipo': latest['signal_type'],
                        'Preço': round(last_close, 2),
                        'POI': latest.get('poi_type'),
                        'POI Preço': round(float(poi), 2),
                        'Zona': zone,
                        'SL': round(float(sl), 2),
                        'TP1': round(float(tp1), 2),
                        'RR': rr,
                        'Dist. POI': f"{dist_poi:+.1f}%",
                        'Nota MTF': latest.get('mtf_note')
                    })
        except Exception as e:
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
        print("A malha fina não reteve nenhum sinal ativo com as configurações SMC rigorosas de hoje.")
