import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# STRATEGY PARAMETERS
# ==========================================
TICKERS = ['SPY', 'WFC', 'XOM']
MA_WINDOW = 200
LONG_ENTRY_STREAK = 3
LONG_ADDON_STREAK = 4
SHORT_ENTRY_STREAK = 3
LONG_TARGET_UP_DAYS = 3
SHORT_TARGET_DOWN_DAYS = 3
LONG_HARD_STOP_PCT = -0.10
SHORT_HARD_STOP_PCT = 0.05

# ==========================================
# LOGIC FUNCTIONS
# ==========================================

def get_streak(series):
    count = 0
    for i in range(len(series) - 1, -1, -1):
        if series.iloc[i]:
            count += 1
        else:
            break
    return count

def find_last_signal_price(streak_series, price_series, target_streak):
    for i in range(len(streak_series) - 1, -1, -1):
        if streak_series.iloc[i] == target_streak:
            return price_series.iloc[i]
    return None

def run_screener():
    """Runs the strategy logic and returns results for both UI and Telegram."""
    try:
        data = yf.download(TICKERS, period="260d", interval="1d", progress=False)
        closes = data['Close']
        df_up = closes.pct_change() > 0
        df_down = closes.pct_change() < 0
        df_ma200 = closes.rolling(window=MA_WINDOW).mean()

        results = []
        for ticker in TICKERS:
            current_price = closes[ticker].iloc[-1]
            current_ma = df_ma200[ticker].iloc[-1]
            c_up_streak = get_streak(df_up[ticker])
            c_down_streak = get_streak(df_down[ticker])
            p_up_streak = get_streak(df_up[ticker].iloc[:-1])
            p_down_streak = get_streak(df_down[ticker].iloc[:-1])

            actions = []
            
            # Entry/Exit Logic
            if c_down_streak == LONG_ENTRY_STREAK:
                actions.append(("success", f"LONG ENTRY: 3rd Down Day at ${current_price:.2f}"))
            if c_down_streak == LONG_ADDON_STREAK:
                actions.append(("success", f"ADD-ON: 4th Down Day at ${current_price:.2f}"))
            if c_up_streak == SHORT_ENTRY_STREAK and current_price < current_ma:
                actions.append(("success", f"SHORT ENTRY: 3rd Up Day below MA at ${current_price:.2f}"))
            if c_up_streak == 1 and p_down_streak in [3, 4]:
                actions.append(("info", f"EXIT PARTIAL: Day 1 Reversal (Long)"))
            if c_down_streak == 1 and p_up_streak == SHORT_ENTRY_STREAK:
                actions.append(("info", f"EXIT PARTIAL: Day 1 Reversal (Short)"))
            if c_up_streak == LONG_TARGET_UP_DAYS:
                actions.append(("warning", f"EXIT FULL: Long Target hit"))
            if c_down_streak == SHORT_TARGET_DOWN_DAYS:
                actions.append(("warning", f"EXIT FULL: Short Target hit"))

            # Hard Stop Checks
            entry_3d_long = find_last_signal_price(df_down[ticker], closes[ticker], 3)
            if entry_3d_long and (current_price / entry_3d_long - 1) <= LONG_HARD_STOP_PCT:
                actions.append(("error", "🚨 HARD STOP BREACH (Long)"))

            results.append({
                "ticker": ticker,
                "price": current_price,
                "up_streak": int(c_up_streak),
                "down_streak": int(c_down_streak),
                "actions": actions
            })
        return results, None
    except Exception as e:
        return [], str(e)

# ==========================================
# STREAMLIT UI SECTION
# ==========================================
if __name__ == "__main__":
    st.set_page_config(page_title="Strategy Screener")
    st.title("📈 Daily Strategy Dashboard")
    
    scan_results, error = run_screener()
    
    if error:
        st.error(f"Error loading data: {error}")
    else:
        for res in scan_results:
            st.subheader(f"{res['ticker']}: ${res['price']:.2f}")
            if not res['actions']:
                st.write("Neutral - No Action")
            else:
                for style, msg in res['actions']:
                    if style == "success": st.success(msg)
                    elif style == "info": st.info(msg)
                    elif style == "warning": st.warning(msg)
                    elif style == "error": st.error(msg)
            
            with st.expander("Strategy Details"):
                st.write(f"Up Streak: {res['up_streak']}")
                st.write(f"Down Streak: {res['down_streak']}")
