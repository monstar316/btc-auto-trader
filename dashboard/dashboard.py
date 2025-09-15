import streamlit as st
import json
import os
import pandas as pd
import time

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "last_price": None,
        "last_trade_time": None,
        "open_position": False,
        "daily_trade_count": 0,
        "mode": "unknown",
        "open_trades": [],
        "trade_history": []
    }

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")
st.title("📊 Trading Bot Dashboard")

# Auto-refresh every 10 seconds
st_autorefresh = st.sidebar.empty()
st_autorefresh.text("Auto-refreshing every 10s")

state = load_state()

# --- Overview ---
col1, col2, col3 = st.columns(3)
col1.metric("Bot Mode", state.get("mode", "unknown"))
col2.metric("Last Price", state.get("last_price", "N/A"))
col3.metric("Trades Today", state.get("daily_trade_count", 0))

st.divider()

# --- Open Trades ---
st.subheader("📌 Open Trades")
if state.get("open_trades"):
    df_open = pd.DataFrame(state["open_trades"])
    st.dataframe(df_open, use_container_width=True)
else:
    st.info("No open trades.")

# --- Trade History ---
st.subheader("📜 Trade History")
if state.get("trade_history"):
    df_hist = pd.DataFrame(state["trade_history"])
    st.dataframe(df_hist, use_container_width=True)
else:
    st.info("No trade history yet.")

# Refresh every 10s (frontend)
time.sleep(10)
st.experimental_rerun()
