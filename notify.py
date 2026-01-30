import os
import requests
from strlit_screener import run_screener 

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=15)
    except Exception as e:
        print(f"Connection Error: {e}")

# Run the logic
scan_results = run_screener()

alert_text = "🎯 Daily Strategy Alert:\n"
has_signal = False

for res in scan_results:
    if res['actions']:
        has_signal = True
        alert_text += f"\n[{res['ticker']}] ${res['price']:.2f}\n"
        for style, msg in res['actions']:
            alert_text += f"- {msg}\n"

if has_signal:
    send_telegram_msg(alert_text)
else:
    send_telegram_msg("✅ Strategy Scan Complete: No signals triggered.")


