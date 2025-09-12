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
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {path} was corrupt, resetting.")
            return default
    return default

def save_json_file(path, data):
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
    "symbol": "BTC/GBP",
    "take_profit_pct": 2.0,   # close trade at +2% profit
    "stop_loss_pct": 1.0      # close trade at -1% loss
})
save_json_file(CONFIG_FILE, config)

# -------------------------------------------------------------------
# Daily reset
# -------------------------------------------------------------------

def reset_daily_trade_count():
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
    if state["daily_trade_count"] >= config.get("max_daily_trades", 5):
        print(f"⛔ Max daily trades ({config['max_daily_trades']}) reached. No more trades today.")
        return False
    return True

def open_trade(symbol, amount, price):
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

def close_trade(trade, exit_price, reason):
    trade["timestamp_close"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    trade["price_close"] = exit_price
    trade["status"] = "CLOSED"
    trade["close_reason"] = reason

    entry = trade["price_open"]
    pnl_pct = ((exit_price - entry) / entry) * 100
    pnl_value = (exit_price - entry) * trade["amount"]

    trade["pnl_pct"] = round(pnl_pct, 2)
    trade["pnl_value"] = round(pnl_value, 2)

    trades.append(trade)
    save_json_file(TRADES_FILE, trades)

    state["open_trades"] = [t for t in state["open_trades"] if t["id"] != trade["id"]]
    save_json_file(STATE_FILE, state)

    print(f"📊 Closed trade {trade['id']} | {reason} | P&L: {trade['pnl_pct']}% ({trade['pnl_value']} {config['base_currency']})")

# -------------------------------------------------------------------
# Strategy logic
# -------------------------------------------------------------------

def strategy(price):
    # Open trade if none exist
    if can_trade() and not state["open_trades"]:
        open_trade(config["symbol"], config["trade_amount"], price)

    # Check open trades
    for trade in list(state["open_trades"]):
        entry = trade["price_open"]
        tp_level = entry * (1 + config["take_profit_pct"] / 100)
        sl_level = entry * (1 - config["stop_loss_pct"] / 100)

        if price >= tp_level:
            close_trade(trade, price, "TAKE_PROFIT")
        elif price <= sl_level:
            close_trade(trade, price, "STOP_LOSS")

# -------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------

print("🚀 Kraken Bot starting...")

while True:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    reset_daily_trade_count()
    print(f"[{now}] Bot heartbeat. Trades today: {state['daily_trade_count']} / {config['max_daily_trades']}")

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
