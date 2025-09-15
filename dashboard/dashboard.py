import os
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# --------------------------
# Helpers
# --------------------------
def load_config():
    """Load config with safe defaults if missing."""
    config_path = os.getenv("CONFIG_PATH", "config.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning("⚠️ config.json not found — using defaults")
        return {
            "trade_symbol": "XXBTZGBP",
            "trade_amount": 0.001,
            "max_daily_trades": 3,
            "paper_trading": False
        }

def load_json(filename, default):
    try:
        with open(filename) as f:
            return json.load(f)
    except FileNotFoundError:
        return default

# --------------------------
# Load data
# --------------------------
config = load_config()
state = load_json("bot_state.json", {})
trades = load_json("trades.json", [])

# --------------------------
# Dashboard Layout
# --------------------------
st.set_page_config(page_title="Kraken Trading Bot", layout="wide")
st.title("📊 Kraken Trading Bot Dashboard")

# Auto-refresh every 10s
st_autorefresh(interval=10 * 1000, key="refresh")

# --------------------------
# Config Section
# --------------------------
st.subheader("⚙️ Current Configuration")
st.json(config)

# --------------------------
# Bot State
# --------------------------
st.subheader("🤖 Bot State")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Mode", state.get("mode", "N/A"))
col2.metric("Open Position", str(state.get("open_position", False)))
col3.metric("Daily Trades", state.get("daily_trade_count", 0))
col4.metric("Last Reset", state.get("last_reset_date", "N/A"))

# --------------------------
# Open Trades
# --------------------------
st.subheader("📂 Open Trades")
open_trades = state.get("open_trades", [])
if open_trades:
    df_open = pd.DataFrame(open_trades)
    st.dataframe(df_open)
else:
    st.info("No open trades at the moment.")

# --------------------------
# Trade History
# --------------------------
st.subheader("📜 Trade History")
if trades:
    df_trades = pd.DataFrame(trades)
    st.dataframe(df_trades)

    # Performance chart
    if "profit_loss" in df_trades.columns:
        st.subheader("📈 Profit / Loss Over Time")
        fig, ax = plt.subplots()
        df_trades["profit_loss"].cumsum().plot(ax=ax)
        ax.set_ylabel("Cumulative P/L")
        st.pyplot(fig)
else:
    st.info("No trades recorded yet.")

# --------------------------
# Price Section
# --------------------------
st.subheader("💰 Market Price (Placeholder)")
last_price = state.get("last_price", None)
if last_price:
    st.metric("Last Price", f"£{last_price:,.2f}")
else:
    st.info("Fetching price...")
