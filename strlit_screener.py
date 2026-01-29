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


@st.cache_data(ttl=3600)  # Cache data for 1 hour to avoid Yahoo blocks
def fetch_data(tickers):
    data = yf.download(tickers, period="260d", interval="1d", progress=False)
    return data['Close']


# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Strategy Screener", layout="wide")
st.title("📈 Daily Strategy Screener")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if st.button('🔄 Refresh Data'):
    st.cache_data.clear()

try:
    closes = fetch_data(TICKERS)
    df_up = closes.pct_change() > 0
    df_down = closes.pct_change() < 0
    df_ma200 = closes.rolling(window=MA_WINDOW).mean()

    # We'll need these for the hard stop logic
    streaks_up_all = df_up.rolling(window=10).apply(lambda x: get_streak(x), raw=False)
    streaks_down_all = df_down.rolling(window=10).apply(lambda x: get_streak(x), raw=False)

    # Create Columns for a clean layout
    cols = st.columns(len(TICKERS))

    for idx, ticker in enumerate(TICKERS):
        with cols[idx]:
            current_price = closes[ticker].iloc[-1]
            current_ma = df_ma200[ticker].iloc[-1]
            c_up_streak = get_streak(df_up[ticker])
            c_down_streak = get_streak(df_down[ticker])
            p_up_streak = get_streak(df_up[ticker].iloc[:-1])
            p_down_streak = get_streak(df_down[ticker].iloc[:-1])

            ma_status = "✅ Above" if current_price > current_ma else "❌ Below"

            st.metric(label=ticker, value=f"${current_price:.2f}", delta=f"{ma_status} MA200")

            # Action Logic
            actions = []

            # Entry/Add-on
            if c_down_streak == LONG_ENTRY_STREAK:
                actions.append(("success", f"LONG ENTRY: 3rd Down Day"))
            if c_down_streak == LONG_ADDON_STREAK:
                actions.append(("success", f"ADD-ON: 4th Down Day"))
            if c_up_streak == SHORT_ENTRY_STREAK and current_price < current_ma:
                actions.append(("error", f"SHORT ENTRY: 3rd Up Day"))

            # Exits
            if c_up_streak == 1 and p_down_streak in [3, 4]:
                actions.append(("info", f"EXIT PARTIAL: Day 1 Reversal (Long)"))
            if c_down_streak == 1 and p_up_streak == SHORT_ENTRY_STREAK:
                actions.append(("info", f"EXIT PARTIAL: Day 1 Reversal (Short)"))
            if c_up_streak == LONG_TARGET_UP_DAYS:
                actions.append(("warning", f"EXIT FULL: Long Target hit"))
            if c_down_streak == SHORT_TARGET_DOWN_DAYS:
                actions.append(("warning", f"EXIT FULL: Short Target hit"))

            # Hard Stop Checks
            entry_3d_long = find_last_signal_price(streaks_down_all[ticker], closes[ticker], 3)
            if entry_3d_long and (current_price / entry_3d_long - 1) <= LONG_HARD_STOP_PCT:
                actions.append(("error", "🚨 HARD STOP BREACH (Long)"))

            # Display Actions
            if not actions:
                st.write("Neutral - No Action")
            else:
                for style, msg in actions:
                    if style == "success":
                        st.success(msg)
                    elif style == "info":
                        st.info(msg)
                    elif style == "warning":
                        st.warning(msg)
                    elif style == "error":
                        st.error(msg)

            # Mini Details
            with st.expander("Strategy Details"):
                st.write(f"Up Streak: {int(c_up_streak)}")
                st.write(f"Down Streak: {int(c_down_streak)}")
                st.write(f"MA200: ${current_ma:.2f}")

except Exception as e:
    st.error(f"Error loading data: {e}")