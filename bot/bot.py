import time
import os
import json
import krakenex
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from datetime import datetime

# --- Track the date for daily reset ---
if "last_reset_date" not in state:
    state["last_reset_date"] = datetime.utcnow().strftime("%Y-%m-%d")
    save_json(STATE_FILE, state)

# --- Load environment variables ---
load_dotenv()

# --- Absolute paths inside the container ---
DATA_DIR = "/app/data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
TRADE_LOG = os.path.join(DATA_DIR, "trades.json")

# --- JSON helpers ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --- Load config (static strategy rules) ---
config = load_json(CONFIG_FILE)

# --- Load state (runtime variables) ---
state = load_json(STATE_FILE)
if not state:  # initialise if missing
    state = {
        "last_price": None,
        "last_trade_time": None,
        "open_position": False,
        "trades_today": 0,
        "cooldown_until": None
    }
    save_json(STATE_FILE, state)

# --- Kraken API setup ---
mode = os.getenv("KRAKEN_MODE", "live").lower()
kraken = krakenex.API()

if mode == "sandbox":
    kraken.key = os.getenv("KRAKEN_SANDBOX_API_KEY")
    kraken.secret = os.getenv("KRAKEN_SANDBOX_API_SECRET")
    kraken.api_url = "https://api.sandbox.kraken.com"
    print("⚡ Running in SANDBOX mode", flush=True)
else:
    kraken.key = os.getenv("KRAKEN_API_KEY")
    kraken.secret = os.getenv("KRAKEN_API_SECRET")
    kraken.api_url = "https://api.kraken.com"
    print("⚡ Running in LIVE mode", flush=True)

TRADE_SYMBOL = config.get("trade_symbol", "XXBTZGBP")

# --- Flask health server ---
app = Flask(__name__)

@app.route("/health")
def health():
    return "ok", 200

def run_health_server():
    app.run(host="0.0.0.0", port=5000)

Thread(target=run_health_server, daemon=True).start()

# --- Price fetch ---
def get_price(symbol):
    try:
        res = kraken.query_public("Ticker", {"pair": symbol})
        last_trade = res["result"][symbol]["c"][0]
        return float(last_trade)
    except Exception as e:
        print(f"❌ Error fetching price: {e}", flush=True)
        return None

# --- Simulate trade ---
def simulate_trade(state, trade_type="buy", amount=0.001):
    trades = load_json(TRADE_LOG)
    price = state.get("last_price")
    if price is None:
        print("⚠️ Cannot simulate trade: last_price is None", flush=True)
        return

    trade_entry = {
        "type": trade_type,
        "amount": amount,
        "price": price,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "paper_trade": config.get("paper_trading", True)  # always from config.json
    }

    trades.append(trade_entry)
    save_json(TRADE_LOG, trades)
    state["trades_today"] = state.get("trades_today", 0) + 1
    state["last_trade_time"] = trade_entry["timestamp"]
    save_json(STATE_FILE, state)

    print(f"📝 {('Simulated' if trade_entry['paper_trade'] else 'Real')} "
          f"{trade_type.upper()} trade: {amount} {TRADE_SYMBOL} at £{price:.2f}", flush=True)

# --- Main loop ---
# --- Reset trades_today at midnight UTC ---
today = datetime.utcnow().strftime("%Y-%m-%d")
if state.get("last_reset_date") != today:
    state["trades_today"] = 0
    state["last_reset_date"] = today
    save_json(STATE_FILE, state)
    print("♻️ Daily trade count reset.", flush=True)

print("🚀 Bot started...", flush=True)
while True:
    try:
        price = get_price(TRADE_SYMBOL)
        if price:
            state["last_price"] = price
            save_json(STATE_FILE, state)
            print(f"✅ Last price updated: £{price:.2f}", flush=True)

            # Only trade if under daily limit
            if state.get("trades_today", 0) < config.get("max_trades_per_day", 3):
                if config.get("paper_trading", True):
                    simulate_trade(state, trade_type="buy", amount=config.get("trade_amount", 0.001))
        else:
            print("⚠️ Price fetch returned None", flush=True)
    except Exception as e:
        print(f"❌ Unexpected error in main loop: {e}", flush=True)

    time.sleep(60)
