import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

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
    """Contains the exact logic from screener.py"""
    data = yf.download(TICKERS, period="260d", interval="1d", progress=False)
    closes = data['Close']
    df_up = closes.pct_change() > 0
    df_down = closes.pct_change() < 0
    df_ma200 = closes.rolling(window=MA_WINDOW).mean()
    
    # Pre-calculating streaks for lookback
    streaks_up = df_up.apply(lambda x: x.rolling(window=len(x), min_periods=1).apply(get_streak, raw=False))
    streaks_down = df_down.apply(lambda x: x.rolling(window=len(x), min_periods=1).apply(get_streak, raw=False))

    results = []

    for ticker in TICKERS:
        current_price = closes[ticker].iloc[-1]
        current_ma = df_ma200[ticker].iloc[-1]
        
        c_up_streak = get_streak(df_up[ticker])
        c_down_streak = get_streak(df_down[ticker])
        p_up_streak = get_streak(df_up[ticker].iloc[:-1])
        p_down_streak = get_streak(df_down[ticker].iloc[:-1])

        ticker_actions = []

        # --- ENTRY LOGIC ---
        if c_down_streak == LONG_ENTRY_STREAK:
            ticker_actions.append(f"LONG ENTRY - 3rd Down Day hit at ${current_price:.2f}")
        if c_down_streak == LONG_ADDON_STREAK:
            ticker_actions.append(f"ADD-ON - 4th Down Day hit at ${current_price:.2f}")
        if c_up_streak == SHORT_ENTRY_STREAK and current_price < current_ma:
            ticker_actions.append(f"SHORT ENTRY - 3rd Up Day below MA hit at ${current_price:.2f}")

        # --- EXIT LOGIC ---
        if c_up_streak == 1 and p_down_streak in [3, 4]:
            ticker_actions.append(f"EXIT PARTIAL - Day 1 Reversal (Up after {int(p_down_streak)} Down Days)")
        if c_down_streak == 1 and p_up_streak == SHORT_ENTRY_STREAK:
            ticker_actions.append(f"EXIT PARTIAL - Day 1 Reversal (Down after {int(p_up_streak)} Up Days)")
        if c_up_streak == LONG_TARGET_UP_DAYS:
            ticker_actions.append(f"EXIT FULL - Long Target Reached (3rd Up Day)")
        if c_down_streak == SHORT_TARGET_DOWN_DAYS:
            ticker_actions.append(f"EXIT FULL - Short Target Reached (3rd Down Day)")

        # --- HARD STOP CALCULATIONS ---
        entry_3d_long = find_last_signal_price(streaks_down[ticker], closes[ticker], 3)
        entry_4d_long = find_last_signal_price(streaks_down[ticker], closes[ticker], 4)
        entry_3d_short = find_last_signal_price(streaks_up[ticker], closes[ticker], 3)

        if entry_3d_long and (current_price / entry_3d_long - 1) <= LONG_HARD_STOP_PCT:
            ticker_actions.append(f"HARD STOP BREACH - Current ${current_price:.2f} is 10%+ below 3-Day Entry (${entry_3d_long:.2f})")
        if entry_4d_long and (current_price / entry_4d_long - 1) <= LONG_HARD_STOP_PCT:
            ticker_actions.append(f"HARD STOP BREACH - Current ${current_price:.2f} is 10%+ below 4-Day Add-on (${entry_4d_long:.2f})")
        if entry_3d_short and (current_price / entry_3d_short - 1) >= SHORT_HARD_STOP_PCT:
            ticker_actions.append(f"HARD STOP BREACH - Current ${current_price:.2f} is 5%+ above Short Entry (${entry_3d_short:.2f})")

        results.append({
            "ticker": ticker,
            "price": current_price,
            "ma200": current_ma,
            "up_streak": int(c_up_streak),
            "down_streak": int(c_down_streak),
            "actions": ticker_actions if ticker_actions else ["NO ACTION REQUIRED"]
        })
    return results

# ==========================================
# STREAMLIT INTERFACE
# ==========================================
if __name__ == "__main__":
    st.set_page_config(page_title="Strategy Screener", layout="wide")
    st.title("📈 Mean Reversion Strategy Dashboard")
    
    try:
        scan_results = run_screener()
        
        for res in scan_results:
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.subheader(res['ticker'])
                    st.metric("Price", f"${res['price']:.2f}")
                    ma_status = "Above MA200" if res['price'] > res['ma200'] else "Below MA200"
                    st.write(f"Trend: {ma_status}")
                
                with col2:
                    for action in res['actions']:
                        if "ENTRY" in action:
                            st.success(action)
                        elif "EXIT" in action:
                            st.warning(action)
                        elif "HARD STOP" in action:
                            st.error(action)
                        else:
                            st.info(action)
                st.divider()
                
    except Exception as e:
        st.error(f"Error executing scan: {e}")



