import os
import requests
from main import run_screener_logic # We'll wrap your logic in a function

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

results = run_screener_logic()
alert_text = "🎯 Daily Strategy Alert:\n"
has_signal = False

for res in results:
    # Only notify if actions are NOT "NO ACTION REQUIRED"
    if "NO ACTION REQUIRED" not in res['actions']:
        has_signal = True
        alert_text += f"\n[{res['ticker']}] ${res['price']:.2f}\n"
        for action in res['actions']:
            alert_text += f"- {action}\n"

if has_signal:
    send_telegram_msg(alert_text)
else:
    send_telegram_msg("✅ Strategy Scan Complete: No signals triggered.")
