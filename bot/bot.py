import json
import os
import time
import datetime
import ccxt

# === Load Config ===
CONFIG_FILE = os.path.join("data", "config.json")

with open(CONFIG_FILE) as f:
    config = json.load(f)

TRADE_SYMBOL = config.get("trade_symbol", "XXBTZGBP")
TRADE_AMOUNT = config.get("trade_amount", 0.001)
MAX_DAILY_TRADES = config.get("max_daily_trades", 3)
PAPER_TRADING = config.get("paper_trading", False)

# === Bot State File ===
STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "last_price": None,
        "last_trade_time": None,
        "open_position": False,
        "trades_today": 0,
        "cooldown_until": None,
        "last_reset_date": str(datetime.date.today()),
        "daily_trade_count": 0,
        "open_trades": [],
        "trade_history": [],
        "mode": "paper" if PAPER_TRADING else "live"
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# === Initialize Exchange ===
exchange = ccxt.kraken({
    "enableRateLimit": True,
})

# === Bot Logic ===
def get_market_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker["last"]
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def execute_buy(state, price):
    trade = {
        "id": len(state["trade_history"]) + 1,
        "timestamp_open": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": TRADE_SYMBOL,
        "amount": TRADE_AMOUNT,
        "price_open": price,
        "paper": PAPER_TRADING,
        "status": "OPEN",
        "order_id": None
    }

    if not PAPER_TRADING:
        try:
            order = exchange.create_market_buy_order(TRADE_SYMBOL, TRADE_AMOUNT)
            trade["order_id"] = order.get("id", None)
            print(f"Live BUY executed: {order}")
        except Exception as e:
            print(f"Error placing live buy order: {e}")
            return state

    state["open_trades"].append(trade)
    state["open_position"] = True
    state["daily_trade_count"] += 1
    state["last_trade_time"] = trade["timestamp_open"]
    return state

def execute_sell(state, trade, price):
    trade["price_close"] = price
    trade["timestamp_close"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trade["status"] = "CLOSED"

    if not PAPER_TRADING:
        try:
            order = exchange.create_market_sell_order(TRADE_SYMBOL, TRADE_AMOUNT)
            trade["sell_order_id"] = order.get("id", None)
            print(f"Live SELL executed: {order}")
        except Exception as e:
            print(f"Error placing live sell order: {e}")

    state["trade_history"].append(trade)
    state["open_trades"].remove(trade)
    state["open_position"] = False
    return state

def reset_daily_trades(state):
    today = str(datetime.date.today())
    if state["last_reset_date"] != today:
        state["last_reset_date"] = today
        state["daily_trade_count"] = 0
    return state

# === Main Loop ===
def run_bot():
    state = load_state()

    while True:
        state = reset_daily_trades(state)

        price = get_market_price(TRADE_SYMBOL)
        if price:
            state["last_price"] = price

        # --- Example trading rule ---
        if not state["open_position"] and state["daily_trade_count"] < MAX_DAILY_TRADES:
            if price:  # simple condition: always buy if free
                state = execute_buy(state, price)

        elif state["open_position"]:
            # For demo: close trade after 30s
            open_trade = state["open_trades"][0]
            trade_time = datetime.datetime.strptime(open_trade["timestamp_open"], "%Y-%m-%d %H:%M:%S")
            if (datetime.datetime.now() - trade_time).seconds > 30:
                state = execute_sell(state, open_trade, price)

        # Save state every loop
        save_state(state)

        time.sleep(10)  # sync every 10 seconds

if __name__ == "__main__":
    run_bot()
