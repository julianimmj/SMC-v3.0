import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import datetime

def send_alert_email(df_signals: pd.DataFrame, subscriber_emails: list, sender_email: str, sender_password: str):
    if df_signals.empty or not subscriber_emails:
        return

    # Build sleek HTML table
    table_rows = ""
    for _, row in df_signals.iterrows():
        # Clean colors for the email
        dir_color = "#10d9a0" if row['Sinal'] == 'bull' else "#f4436c"
        sinal_txt = "Alta" if row['Sinal'] == 'bull' else "Baixa"
        
        table_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #333342;">
                <strong>{row['Ticker']}</strong> <br>
                <span style="font-size:12px; color:{dir_color}; font-weight:bold;">{sinal_txt} ({row['Tipo']})</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #333342; font-size:14px; text-align:center;">
                {row['Zona'].title()}<br>
                <span style="font-size:12px; color:#8b8baa;">({row['POI']})</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #333342; text-align:right;">
                Entry: R$ {row['POI Preço']:.2f}<br>
                SL: R$ {row['SL']:.2f} | TP: R$ {row['TP1']:.2f}<br>
                <strong style="color:#f1f1fa;">RR: {row['RR']}x</strong>
            </td>
        </tr>
        """

    html_content = f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    </head>
    <body style="margin:0; padding:0; background-color:#07071a; color:#f1f1fa; font-family:'Inter', sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color:#121226; border-radius: 8px; overflow: hidden; margin-top:20px; border:1px solid #333342;">
            <div style="background: linear-gradient(130deg, #4f8ef7, #8b8baa); padding: 24px; text-align: center;">
                <h1 style="color:white; margin:0; font-size: 24px; letter-spacing: -0.5px;">SMC Cloud Screener</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 6px 0 0; font-size: 14px;">Alerta Diário de Oportunidades B3</p>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color:#c6c6d3; line-height:1.6;">
                    Olá TRADER,<br><br>
                    O nosso algoritmo de <em>Smart Money Concepts</em> isolou 
                    <strong style="color:#4f8ef7;">{len(df_signals)} oportunidades</strong> em zonas intocadas durante o scan de hoje ({datetime.datetime.now().strftime('%d/%m')}).
                </p>

                <table width="100%" style="border-collapse: collapse; margin-top: 20px; background-color: #07071a; border-radius: 6px;">
                    {table_rows}
                </table>

                <p style="margin-top: 30px; font-size: 12px; color:#8b8baa; text-align:center;">
                    Lembre-se: Desça para timeframes menores (M15) para procurar CHOCH Interno no toque dessas zonas antes de engatilhar seu risco. <br><br>
                    <a href="https://smc-v30.streamlit.app/" style="color:#4f8ef7; text-decoration:none;">Acessar Painel Interativo Completo</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    subject = f"🚨 {len(df_signals)} Sinais SMC Detectados ({datetime.datetime.now().strftime('%d/%m')})"

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)

        for to_email in subscriber_emails:
            msg = MIMEMultipart()
            msg['From'] = f"SMC Screener <{sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))
            
            server.send_message(msg)
            
        server.quit()
        print(f"Emails sent successfully to {len(subscriber_emails)} subscribers.")
    except Exception as e:
        print(f"SMTP Error: {e}")
