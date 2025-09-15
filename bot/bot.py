import krakenex
import os
import json
import time
from datetime import datetime, date
from dotenv import load_dotenv
from flask import Flask

# --------------------
# Setup
# --------------------
load_dotenv()

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)

# --------------------
# Load JSON helpers
# --------------------
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --------------------
# Load state/config
# --------------------
config = load_json(CONFIG_FILE, {})
state = load_json(STATE_FILE, {
    "last_price": None,
    "last_trade_time": None,
    "open_position": False,
    "open_trades": [],
    "closed_trades": [],
    "cooldown_until": None,
    "last_reset_date": str(date.today()),
    "daily_trade_count": 0
})

# --------------------
# Kraken API setup
# --------------------
mode = os.getenv("KRAKEN_MODE", "live").lower()

kraken = krakenex.API()
if mode == "sandbox":
    kraken.key = os.getenv("KRAKEN_SANDBOX_API_KEY")
    kraken.secret = os.getenv("KRAKEN_SANDBOX_API_SECRET")
    kraken.api_url = "https://api.sandbox.kraken.com"
    print("⚡ Running in SANDBOX mode")
else:
    kraken.key = os.getenv("KRAKEN_API_KEY")
    kraken.secret = os.getenv("KRAKEN_API_SECRET")
    kraken.api_url = "https://api.kraken.com"
    print("⚡ Running in LIVE mode")

# --------------------
# Health endpoint
# --------------------
@app.route("/health")
def health():
    return {"status": "ok", "last_price": state.get("last_price")}

# --------------------
# Helper functions
# --------------------
def reset_daily_state():
    today = str(date.today())
    if state.get("last_reset_date") != today:
        print("🔄 Daily reset triggered")
        state["last_reset_date"] = today
        state["daily_trade_count"] = 0
        save_json(STATE_FILE, state)

def fetch_price():
    try:
        resp = kraken.query_public("Ticker", {"pair": config["trade_symbol"]})
        result = list(resp["result"].values())[0]
        return float(result["c"][0])  # last trade closed price
    except Exception as e:
        print("⚠️ Price fetch failed:", e)
        return None

def fetch_open_orders():
    try:
        resp = kraken.query_private("OpenOrders")
        return resp.get("result", {}).get("open", {})
    except Exception as e:
        print("⚠️ Fetch open orders failed:", e)
        return {}

def place_order(side, volume):
    if config.get("paper_trading", False):
        print(f"📄 Paper {side} order placed for {volume}")
        return {"descr": {"order": "paper-trade"}, "id": f"paper-{int(time.time())}"}

    try:
        order = {
            "pair": config["trade_symbol"],
            "type": side,
            "ordertype": "market",
            "volume": volume,
        }
        resp = kraken.query_private("AddOrder", order)
        print(f"✅ Live {side} order response:", resp)
        return resp
    except Exception as e:
        print(f"⚠️ Order failed: {e}")
        return None

# --------------------
# Bot loop
# --------------------
if __name__ == "__main__":
    print("🚀 Kraken Bot starting...")

    while True:
        reset_daily_state()

        price = fetch_price()
        if price:
            state["last_price"] = price

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Bot heartbeat. Trades today: {state['daily_trade_count']} / {config.get('max_daily_trades', 3)}")

        # Sync manual Kraken trades into state (optional extension)
        open_orders = fetch_open_orders()
        for oid, details in open_orders.items():
            if oid not in [t.get("order_id") for t in state["open_trades"]]:
                state["open_trades"].append({
                    "id": len(state["open_trades"]) + 1,
                    "order_id": oid,
                    "timestamp_open": now,
                    "symbol": config["trade_symbol"],
                    "amount": float(details["vol"]),
                    "price_open": float(details["descr"]["price"]) if "descr" in details else 0,
                    "paper": config.get("paper_trading", False),
                    "status": "OPEN",
                    "source": "manual"
                })

        save_json(STATE_FILE, state)
        time.sleep(10)
