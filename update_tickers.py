import pandas as pd
import yfinance as yf
import re

print("Carregando tickers base...")

# Lista expandida com papéis IBOV, IBrX-100, FIIs líquidos e BDRs populares
novo_universo = [
    # IBOV / Principais
    "PETR4", "PETR3", "VALE3", "ITUB4", "BBDC4", "BBDC3", "BBAS3", "ABEV3", "WEGE3", "RENT3",
    "SUZB3", "ELET3", "Elet6", "EQTL3", "RADL3", "B3SA3", "BPAC11", "HAPV3", "PRIO3", "RAIL3",
    "ENEV3", "LREN3", "VIVT3", "MGLU3", "VBBR3", "SBSP3", "CPFE3", "CCRO3", "UGPA3", "CSAN3",
    "CMIG4", "TIMS3", "TOTS3", "EGIE3", "BRFS3", "JBSS3", "KLBN11", "ASAI3", "NTCO3", "CPLE6",
    "GGBR4", "GOAU4", "CSNA3", "USIM5", "CYRE3", "EZTC3", "MRVE3", "TEND3", "MULT3", "IGTI11",
    "ALOS3", "CRFB3", "PCAR3", "BHIA3", "YDUQ3", "COGN3", "CVCB3", "FLRY3", "MDIA3", "SMTO3",
    "SLCE3", "AGRO3", "TTEN3", "RECV3", "RRRP3", "ENGI11", "TAEE11", "TRPL4", "SAPR11", "CSMG3",
    "SANB11", "BPAN4", "BRSR6", "ABCB4", "CXSE3", "PSSA3", "BBSE3", "IRBR3", "WIZC3", "AZUL4",
    "GOLL4", "EMBR3", "POMO4", "WEGE3", "TUPY3", "SHUL4", "RANI3", "STBP3", "PORT3", "INTB3",
    "VAMO3", "ARZZ3", "SOMA3", "CEAB3", "GUAR3", "AMAR3", "OIBR3", "OIBR4", "AURE3", "NEOE3",
    "ALUP11", "VIVA3", "DIRR3", "DXCO3", "MYPK3", "KEPL3", "ROMI3", "LEVE3", "VLID3", "PFRM3",
    "FRAS3", "JSLG3", "LOGG3", "SIMH3", "TASA4", "VULC3", "AURA33", "CBAV3", "FESA4", "UNIP6",
    "RCSL3", "MILS3", "TGMA3", "JALL3", "SMFT3", "ZAMP3", "PETZ3", "SBFG3", "MLAS3", "MATD3",
    "VITT3", "CAML3", "ODPV3", "QUAL3", "ONCO3", "PARD3", "BLAU3", "VAMO3", "NGRD3", "MERC4",
    # FIIs líquidos
    "MXRF11", "HGLG11", "KNCR11", "KNIP11", "BTLG11", "XPLG11", "IRDM11", "CPTS11", "VISC11",
    "HGRU11", "HGCR11", "TGAR11", "BRCR11", "VGHF11", "DEVA11", "MCCI11", "RECR11", "RBRR11",
    "HFOF11", "BCFF11", "PVBI11", "ALZR11", "TRXF11", "MALL11", "XPML11", "HSML11", "VILG11",
    # BDRs e ETFs
    "BOVA11", "SMAL11", "IVVB11", "HASH11", "NASD11", "TECB11", 
    "AAPL34", "MSFT34", "GOGL34", "AMZO34", "META34", "TSLA34", "NVDC34", "MELI34", "ROXO34",
    "MERC4", "CSED3", "BMOB3", "AERI3", "FIQE3", "IFCM3", "CASH3", "NINJ3", "ENJU3", "TOTS3"
]

# Read existing
try:
    df_old = pd.read_csv('tickers_b3.csv')
    old_tickers = df_old['ticker'].dropna().tolist()
except Exception:
    old_tickers = []

all_tickers = sorted(list(set([x.upper().strip() for x in old_tickers + novo_universo])))

print(f"Total de ativos para checagem: {len(all_tickers)}")
SA_tickers = [x + ".SA" for x in all_tickers]

# Download data for validity and liquidity check (last 30 days)
print("Baixando histórico recente para filtro de liquidez...")
data = yf.download(SA_tickers, period='30d', group_by='ticker', progress=False)

valid_liquid_tickers = []

for base_ticker, sa_ticker in zip(all_tickers, SA_tickers):
    try:
        if len(SA_tickers) > 1 and sa_ticker in data.columns.levels[0]:
            t_data = data[sa_ticker]
        elif len(SA_tickers) == 1:
            t_data = data
        else:
            t_data = pd.DataFrame()
            
        t_data = t_data.dropna(subset=['Close', 'Volume'])
        if len(t_data) > 15: # At least 15 active trading days in the last 30
            # Financial volume
            t_data['FinVol'] = t_data['Close'] * t_data['Volume']
            med_finvol = t_data['FinVol'].median()
            
            # Filtro: Pelo menos R$ 1.500.000 de volume financeiro diário mediano
            if med_finvol > 1500000:
                valid_liquid_tickers.append(base_ticker)
    except Exception as e:
        pass

valid_liquid_tickers = sorted(list(set(valid_liquid_tickers)))
total_valid = len(valid_liquid_tickers)
print(f"Sobreviventes após limpeza e filtro de liquidez: {total_valid} ativos.")

# Save
pd.DataFrame({'ticker': valid_liquid_tickers}).to_csv('tickers_b3.csv', index=False)
print("tickers_b3.csv salvo com sucesso!")

# Update app.py
with open("app.py", "r", encoding="utf-8") as f:
    app_text = f.read()

# Replace TOTAL_TICKERS = xxx
app_text = re.sub(r'TOTAL_TICKERS\s*=\s*\d+', f'TOTAL_TICKERS = {total_valid}', app_text)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_text)

print(f"app.py atualizado para TOTAL_TICKERS = {total_valid}")
