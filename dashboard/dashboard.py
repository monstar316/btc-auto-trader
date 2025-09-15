import streamlit as st
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
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
st.sidebar.info("⏳ Auto-refresh every 10s")

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

    # --- Price Evolution Chart ---
    st.subheader("📈 Price Evolution")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_hist["timestamp"], df_hist["price_open"], label="Price", marker="o")
    for i, row in df_hist.iterrows():
        if row.get("side") == "buy":
            ax.scatter(row["timestamp"], row["price_open"], color="green", marker="^", s=100, label="Buy" if i == 0 else "")
        elif row.get("side") == "sell":
            ax.scatter(row["timestamp"], row["price_open"], color="red", marker="v", s=100, label="Sell" if i == 0 else "")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)

    # --- PnL Curve ---
    st.subheader("💰 PnL Over Time")
    if "pnl" in df_hist.columns:
        df_hist["cum_pnl"] = df_hist["pnl"].cumsum()
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(df_hist["timestamp"], df_hist["cum_pnl"], label="Cumulative PnL", color="blue")
        ax2.axhline(0, color="gray", linestyle="--")
        ax2.set_xlabel("Time")
        ax2.set_ylabel("PnL")
        ax2.legend()
        st.pyplot(fig2)
    else:
        st.info("PnL data not available in history yet.")
else:
    st.info("No trade history yet.")

# Refresh every 10s (frontend)
time.sleep(10)
st.rerun()
