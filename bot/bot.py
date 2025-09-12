import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths (shared volume with dashboard)
DATA_DIR = "/app/data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def load_json_file(path, default):
    """Safely load a JSON file or return default if missing/corrupt."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {path} was corrupt, resetting.")
            return default
    return default

def save_json_file(path, data):
    """Save dictionary/list safely to JSON."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# -------------------------------------------------------------------
# Load / initialize files
# -------------------------------------------------------------------

state = load_json_file(STATE_FILE, {})

if "last_reset_date" not in state:
    state["last_reset_date"] = datetime.utcnow().strftime("%Y-%m-%d")

if "daily_trade_count" not in state:
    state["daily_trade_count"] = 0

if "open_trades" not in state:
    state["open_trades"] = []

save_json_file(STATE_FILE, state)

trades = load_json_file(TRADES_FILE, [])
save_json_file(TRADES_FILE, trades)

config = load_json_file(CONFIG_FILE, {
    "paper_trading": True,
    "base_currency": "GBP",
    "trade_amount": 100,
    "max_daily_trades": 5,
    "symbol": "BTC/GBP"
})
save_json_file(CONFIG_FILE, config)

# -------------------------------------------------------------------
# Daily reset
# -------------------------------------------------------------------

def reset_daily_trade_count():
    """Reset daily trade count if the date has changed (UTC)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if state["last_reset_date"] != today:
        print(f"🔄 New day detected ({today}), resetting daily trade count.")
        state["daily_trade_count"] = 0
        state["last_reset_date"] = today
        save_json_file(STATE_FILE, state)

# -------------------------------------------------------------------
# Trade management
# -------------------------------------------------------------------

def can_trade():
    """Check if the bot can place a trade today."""
    if state["daily_trade_count"] >= config.get("max_daily_trades", 5):
        print(f"⛔ Max daily trades ({config['max_daily_trades']}) reached. No more trades today.")
        return False
    return True

def open_trade(symbol, amount, price):
    """Record an open trade in state."""
    trade = {
        "id": len(trades) + len(state["open_trades"]) + 1,
        "timestamp_open": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "amount": amount,
        "price_open": price,
        "paper": config["paper_trading"],
        "status": "OPEN"
    }
    state["open_trades"].append(trade)
    state["daily_trade_count"] += 1
    save_json_file(STATE_FILE, state)
    print(f"✅ Opened trade: {trade}")

def close_trade(trade, exit_price):
    """Close a trade, calculate P&L, and move it to trades history."""
    trade["timestamp_close"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    trade["price_close"] = exit_price
    trade["status"] = "CLOSED"

    # P&L calculation
    entry = trade["price_open"]
    pnl_pct = ((exit_price - entry) / entry) * 100
    pnl_value = (exit_price - entry) * trade["amount"]

    trade["pnl_pct"] = round(pnl_pct, 2)
    trade["pnl_value"] = round(pnl_value, 2)

    trades.append(trade)
    save_json_file(TRADES_FILE, trades)

    # Remove from open trades
    state["open_trades"] = [t for t in state["open_trades"] if t["id"] != trade["id"]]
    save_json_file(STATE_FILE, state)

    print(f"📊 Closed trade {trade['id']} | P&L: {trade['pnl_pct']}% ({trade['pnl_value']} {config['base_currency']})")

# -------------------------------------------------------------------
# Example strategy (toy logic for demo)
# -------------------------------------------------------------------

def strategy(price):
    """Dummy strategy to demonstrate open/close trades."""
    # Open trade if no open trades exist
    if can_trade() and len(state["open_trades"]) == 0:
        open_trade(config["symbol"], config["trade_amount"], price)

    # If trade exists, close it if price moves >1% up
    elif state["open_trades"]:
        trade = state["open_trades"][0]
        entry = trade["price_open"]
        if price >= entry * 1.01:
            close_trade(trade, price)

# -------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------

print("🚀 Kraken Bot starting...")

while True:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    reset_daily_trade_count()

    print(f"[{now}] Bot heartbeat. Trades today: {state['daily_trade_count']} / {config['max_daily_trades']}")

    # Fetch BTC/GBP price
    try:
        response = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCGBP")
        data = response.json()
        price = float(data["result"]["XXBTZGBP"]["c"][0])
        print(f"📈 Current BTC/GBP: {price}")
    except Exception as e:
        print(f"⚠️ Price fetch failed: {e}")
        price = None

    if price:
        strategy(price)

    time.sleep(30)
