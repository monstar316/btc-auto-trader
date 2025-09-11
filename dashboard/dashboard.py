import streamlit as st
import json
import time
import os

# --- Absolute paths inside the container ---
DATA_DIR = "/app/data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
TRADE_FILE = os.path.join(DATA_DIR, "trades.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# --- JSON helpers ---
def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

st.set_page_config(page_title="Kraken Bot Dashboard", layout="wide")
st.title("💹 Kraken Bot Dashboard (GBP)")

# Placeholders
last_price_placeholder = st.empty()
trades_placeholder = st.empty()
config_placeholder = st.sidebar.empty()

while True:
    state = load_json(STATE_FILE)
    trades = load_json(TRADE_FILE)
    config = load_json(CONFIG_FILE)

    # --- Last Price ---
    last_price = state.get("last_price")
    if last_price:
        last_price_placeholder.metric("Last BTC Price (GBP)", f"£{last_price:.2f}")
    else:
        last_price_placeholder.text("Fetching price...")

    # --- Trades ---
    if trades:
        trades_placeholder.table(trades[::-1])  # show latest first
    else:
        trades_placeholder.text("No trades yet.")

    # --- Config (from config.json) ---
    if config:
        config_placeholder.markdown(
            f"""
            ### ⚙️ Bot Settings
            - Mode: **{config.get("mode", "N/A")}**
            - Trade Symbol: **{config.get("trade_symbol", "N/A")}**
            - Trade Amount: **{config.get("trade_amount", "N/A")}**
            - Dip Percentage: **{config.get("dip_percentage", "N/A")}%**
            - Stop Loss: **{config.get("stop_loss", "N/A")}%**
            - Take Profit: **{config.get("take_profit", "N/A")}%**
            - Trailing Stop: **{config.get("trailing_stop", "N/A")}%**
            - Cooldown: **{config.get("cooldown_minutes", "N/A")} minutes**
            - Max Trades/Day: **{config.get("max_trades_per_day", "N/A")}**
            - Paper Trading: **{config.get("paper_trading", True)}**
            """
        )
    else:
        config_placeholder.text("⚠️ Config not found")

    time.sleep(5)
