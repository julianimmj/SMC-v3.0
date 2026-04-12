import json
import os
import pandas as pd
from screener_logic import run_screener
from notifier import send_alert_email

def job():
    print("Iniciando varredura diária automática SMC Screener...")
    
    # 1. Run engine
    try:
        df_signals = run_screener('tickers_b3.csv')
    except Exception as e:
        print(f"Erro na varredura: {e}")
        return

    # 2. Save ALL signals so the frontend UI sliders work correctly!
    if not df_signals.empty:
        df_signals.to_csv('latest_scan.csv', index=False)
        print(f"Salvo latest_scan.csv com {len(df_signals)} resultados.")
    else:
        pd.DataFrame().to_csv('latest_scan.csv', index=False)
        print("Nenhum resultado capturado no robô para o CSV.")

    # 3. Filter high-probability setups (RR > 3) EXCLUSIVELY for the Email Alerts
    if not df_signals.empty:
        df_emails = df_signals[df_signals['RR'] > 3].copy()
    else:
        df_emails = pd.DataFrame()

    # 4. Notify if there are high-prob signals
    if not df_emails.empty:
        # Load emails
        try:
            with open('emails.json', 'r') as f:
                data = json.load(f)
                emails = data.get('emails', [])
        except:
            emails = []

        if emails:
            print(f"Preparando smtp para {len(emails)} e-mails...")
            # Github secrets config
            sender_email = os.environ.get('SMTP_EMAIL')
            sender_pass = os.environ.get('SMTP_PASSWORD')
            
            if sender_email and sender_pass:
                send_alert_email(df_emails, emails, sender_email, sender_pass)
            else:
                print("Segredo SMTP não configurado. Impossível enviar e-mails.")

if __name__ == '__main__':
    job()
