import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh
import matplotlib.pyplot as plt

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

# Auto-refresh every 10s
st_autorefresh(interval=10000, key="refresh")

st.title("📊 Kraken Trading Bot Dashboard")

# Load files
state = load_json(STATE_FILE, {})
config = load_json(CONFIG_FILE, {})

# Current price
st.metric("Current Price", f"£{state.get('last_price', 'fetching...')}")

# Config summary
st.sidebar.header("⚙️ Config")
st.sidebar.json(config)

# Open trades
st.subheader("📈 Open Trades")
if state.get("open_trades"):
    st.dataframe(pd.DataFrame(state["open_trades"]))
else:
    st.info("No open trades.")

# Closed trades
st.subheader("📉 Closed Trades")
if state.get("closed_trades"):
    df_closed = pd.DataFrame(state["closed_trades"])
    df_closed["profit_loss"] = pd.to_numeric(df_closed["profit_loss"], errors="coerce").fillna(0.0)
    st.dataframe(df_closed)

    total_bot = df_closed[df_closed["source"] == "bot"]["profit_loss"].sum()
    total_manual = df_closed[df_closed["source"] == "manual"]["profit_loss"].sum()
    total_all = df_closed["profit_loss"].sum()

    st.markdown("### Profit & Loss Breakdown")
    st.write(f"🤖 Bot: **£{total_bot:.2f}**")
    st.write(f"🧑 Manual: **£{total_manual:.2f}**")
    st.write(f"💰 Total: **£{total_all:.2f}**")

    # Sidebar PnL chart
    st.sidebar.markdown("### 📊 PnL Breakdown")
    summary_df = pd.DataFrame({
        "Source": ["Bot", "Manual", "Total"],
        "PnL": [total_bot, total_manual, total_all]
    })

    fig, ax = plt.subplots(figsize=(3, 2))
    colors = ["#4CAF50", "#2196F3", "#FFC107"]  # Green, Blue, Gold
    ax.bar(summary_df["Source"], summary_df["PnL"], color=colors)
    ax.set_ylabel("PnL (£)")
    ax.set_title("PnL by Source", fontsize=10)
    st.sidebar.pyplot(fig)

else:
    st.info("No closed trades yet.")
