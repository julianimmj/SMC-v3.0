import warnings
warnings.filterwarnings('ignore')
import pandas as pd
from screener_logic import download_data_batch, detect_smc_signals, get_latest_signals

tickers = ['GRND3.SA', 'PETR4.SA', 'VALE3.SA']
data = download_data_batch(tickers)
for t, df in data.items():
    res = detect_smc_signals(df.copy())
    sigs = get_latest_signals(res)
    if not sigs.empty:
        print(f"--- Signals for {t} ---")
        for idx, row in sigs.iterrows():
            print(f"Date: {df.loc[idx, 'Date']}, Signal: {row['signal']}, Type: {row['signal_type']}")
            print(f"  POI: {row['poi_price']} (type: {row['poi_type']}) - Zone: {row['zone']}")
            print(f"  SL: {row['sl_price']}, TP1: {row['tp1_price']}")
            
            # Replicate invalidation logic to see why it fails
            poi = float(row['poi_price'])
            sl = float(row['sl_price'])
            tp1 = float(row['tp1_price'])
            
            failed = False
            if row['signal'] == 'bull':
                if poi <= sl:
                    print(f"  FAIL: poi ({poi}) <= sl ({sl})")
                    failed = True
                if df.loc[idx:, 'Low'].min() <= sl:
                    print(f"  FAIL: min low ({df.loc[idx:, 'Low'].min()}) <= sl ({sl})")
                    failed = True
            else:
                if poi >= sl:
                    print(f"  FAIL: poi ({poi}) >= sl ({sl})")
                    failed = True
                if df.loc[idx:, 'High'].max() >= sl:
                    print(f"  FAIL: max high ({df.loc[idx:, 'High'].max()}) >= sl ({sl})")
                    failed = True
            if not failed:
                print("  => VALID!")

print('DONE')
