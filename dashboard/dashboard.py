import streamlit as st
import json
import os
from datetime import datetime

DATA_DIR = "/app/data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")

# 🔄 Auto-refresh every 10 seconds
st_autorefresh = st.experimental_autorefresh(interval=10 * 1000, key="refresh")

# Helper to load JSON safely
def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default
    return default

# Load files
config = load_json(CONFIG_FILE, {})
state = load_json(STATE_FILE, {})
trades = load_json(TRADES_FILE, [])

# Dashboard UI
st.set_page_config(page_title="Kraken Bot Dashboard (GBP)", layout="wide")
st.title("💹 Kraken Bot Dashboard (GBP)")

# Sidebar settings
st.sidebar.header("⚙️ Bot Settings")
if config:
    st.sidebar.write(f"**Mode:** {config.get('mode', 'N/A')}")
    st.sidebar.write(f"**Trade Symbol:** {config.get('symbol', 'N/A')}")
    st.sidebar.write(f"**Trade Amount:** {config.get('trade_amount', 'N/A')}")
    st.sidebar.write(f"**Take Profit %:** {config.get('take_profit_pct', 'N/A')}")
    st.sidebar.write(f"**Stop Loss %:** {config.get('stop_loss_pct', 'N/A')}")
    st.sidebar.write(f"**Max Trades/Day:** {config.get('max_daily_trades', 'N/A')}")
    st.sidebar.write(f"**Paper Trading:** {config.get('paper_trading', True)}")
else:
    st.sidebar.error("⚠️ Config not found")

# --- PERFORMANCE SUMMARY ---
st.subheader("📊 Performance Summary")

# Trades today
trades_today = state.get("daily_trade_count", 0)

# Closed trades stats
total_pnl_pct = 0.0
total_pnl_gbp = 0.0
profitable_trades = 0
if trades:
    pnl_pct_values = []
    for t in trades:
        price_open = t.get("price_open", 0.0)
        price_close = t.get("price_close", 0.0)
        amount = t.get("amount", 0.0)

        if price_open and price_close:
            pnl_pct = ((price_close - price_open) / price_open) * 100
            pnl_gbp = (price_close - price_open) * amount
            pnl_pct_values.append(pnl_pct)
            total_pnl_pct += pnl_pct
            total_pnl_gbp += pnl_gbp
            if pnl_pct > 0:
                profitable_trades += 1

    win_rate = (profitable_trades / len(pnl_pct_values)) * 100 if pnl_pct_values else 0
else:
    win_rate = 0

# Open trades count
open_trades_count = len(state.get("open_trades", []))

# Display summary metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📆 Trades Today", trades_today)
col2.metric("💰 Total Closed P&L %", f"{total_pnl_pct:.2f}%")
col3.metric("💷 Total Closed P&L £", f"£{total_pnl_gbp:.2f}")
col4.metric("🏆 Win Rate", f"{win_rate:.1f}%")
col5.metric("🔓 Open Trades", open_trades_count)

# Last price
last_price = state.get("last_price", None)
if last_price:
    st.metric("📈 Last Price", f"£{last_price:,.2f}")
else:
    st.write("Fetching price...")

# --- OPEN TRADES ---
open_trades = state.get("open_trades", [])
if open_trades:
    st.subheader("🔓 Open Trades")
    open_trades_data = []
    for t in open_trades:
        trade_id = t.get("id", "N/A")
        symbol = t.get("symbol", "N/A")
        amount = t.get("amount", 0.0)
        price_open = t.get("price_open", 0.0)
        status = t.get("status", "OPEN")
        timestamp_open = t.get("timestamp_open", "N/A")

        # Unrealized P&L if last_price is available
        if last_price and price_open:
            pnl_pct = ((last_price - price_open) / price_open) * 100
            pnl_gbp = (last_price - price_open) * amount
        else:
            pnl_pct = None
            pnl_gbp = None

        open_trades_data.append({
            "ID": trade_id,
            "Symbol": symbol,
            "Amount": amount,
            "Open Price (£)": price_open,
            "Current Price (£)": last_price if last_price else "N/A",
            "Unrealized P&L %": f"{pnl_pct:.2f}%" if pnl_pct is not None else "N/A",
            "Unrealized P&L £": f"£{pnl_gbp:.2f}" if pnl_gbp is not None else "N/A",
            "Status": status,
            "Opened": timestamp_open
        })

    st.table(open_trades_data)
else:
    st.info("✅ No open trades at the moment.")

# --- CLOSED TRADES ---
if trades:
    st.subheader("📜 Closed Trades")
    closed_trades_data = []
    for t in trades:
        trade_id = t.get("id", "N/A")
        symbol = t.get("symbol", "N/A")
        amount = t.get("amount", 0.0)
        price_open = t.get("price_open", 0.0)
        price_close = t.get("price_close", 0.0)
        timestamp_open = t.get("timestamp_open", "N/A")
        timestamp_close = t.get("timestamp_close", "N/A")

        if price_open and price_close:
            pnl_pct = ((price_close - price_open) / price_open) * 100
            pnl_gbp = (price_close - price_open) * amount
        else:
            pnl_pct = None
            pnl_gbp = None

        closed_trades_data.append({
            "ID": trade_id,
            "Symbol": symbol,
            "Amount": amount,
            "Open Price (£)": price_open,
            "Close Price (£)": price_close,
            "P&L %": f"{pnl_pct:.2f}%" if pnl_pct is not None else "N/A",
            "P&L £": f"£{pnl_gbp:.2f}" if pnl_gbp is not None else "N/A",
            "Opened": timestamp_open,
            "Closed": timestamp_close
        })

    st.dataframe(closed_trades_data)
else:
    st.info("📭 No closed trades yet.")
