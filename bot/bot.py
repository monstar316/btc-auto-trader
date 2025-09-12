import os
import json
import time
from datetime import datetime, date
import krakenex
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Connect to Kraken
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

# Paths
DATA_DIR = "/app/data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")

# Load JSON safely
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# Load config/state/trades
config = load_json(CONFIG_FILE, {})
state = load_json(STATE_FILE, {
    "last_price": None,
    "last_trade_time": None,
    "open_position": False,
    "trades_today": 0,
    "cooldown_until": None,
    "last_reset_date": str(date.today()),
    "daily_trade_count": 0,
    "open_trades": []
})
trades = load_json(TRADES_FILE, [])

# Helpers
def save_state(): save_json(STATE_FILE, state)
def save_trades(): save_json(TRADES_FILE, trades)

def get_current_price(symbol="XXBTZGBP"):
    try:
        resp = kraken.query_public("Ticker", {"pair": symbol})
        return float(resp["result"][symbol]["c"][0])
    except Exception as e:
        print(f"⚠️ Error fetching price: {e}")
        return None

def kraken_market_order(side, symbol, amount):
    """Execute live market order"""
    try:
        resp = kraken.query_private("AddOrder", {
            "pair": symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(amount)
        })
        if "error" in resp and resp["error"]:
            print(f"❌ Kraken order error: {resp['error']}")
            return None
        txid = resp["result"]["txid"][0] if "txid" in resp["result"] else None
        print(f"✅ LIVE {side.upper()} order placed: txid={txid}")
        return {"resp": resp["result"], "txid": txid}
    except Exception as e:
        print(f"❌ Failed to place live {side} order: {e}")
        return None

def place_order(side, symbol, amount, paper=True):
    """Place real or paper trade"""
    if paper:
        print(f"📊 Paper {side.upper()} order for {amount} {symbol} at {state['last_price']}")
        result = {"resp": "paper-trade", "txid": None}
    else:
        result = kraken_market_order(side, symbol, amount)

    order = {
        "id": len(trades) + 1,
        "timestamp_open": str(datetime.now()),
        "symbol": symbol,
        "amount": amount,
        "price_open": state["last_price"],
        "side": side,
        "paper": paper,
        "status": "OPEN",
        "order_txid": result["txid"] if result else None,
        "exchange_result": result
    }
    state["open_trades"].append(order)
    trades.append(order)
    state["open_position"] = True
    state["daily_trade_count"] += 1
    save_state()
    save_trades()
    return order

def close_order(order, price_close, pnl, paper=True):
    """Close trade and optionally place live SELL"""
    if not paper:
        result = kraken_market_order("sell", order["symbol"], order["amount"])
    else:
        result = {"resp": "paper-trade", "txid": None}
        print(f"📊 Paper SELL for {order['amount']} {order['symbol']} at {price_close}")

    order["status"] = "CLOSED"
    order["timestamp_close"] = str(datetime.now())
    order["price_close"] = price_close
    order["pnl"] = pnl
    order["close_txid"] = result["txid"] if result else None
    order["close_result"] = result

    state["open_position"] = False
    state["open_trades"] = []
    save_state()
    save_trades()
    print(f"💰 Closed trade {order['id']} with PnL {pnl:.2f}%")

def sync_open_orders(symbol="XXBTZGBP"):
    """Import manually opened Kraken positions"""
    try:
        resp = kraken.query_private("OpenOrders")
        if "error" in resp and resp["error"]:
            print(f"⚠️ Error fetching open orders: {resp['error']}")
            return

        for oid, details in resp["result"]["open"].items():
            pair = details["descr"]["pair"]
            side = details["descr"]["type"]
            vol = float(details["vol"])
            price = float(details["descr"].get("price", 0)) or state["last_price"]

            # Check if already tracked
            exists = any(o.get("order_txid") == oid for o in state["open_trades"])
            if not exists:
                order = {
                    "id": len(trades) + 1,
                    "timestamp_open": str(datetime.now()),
                    "symbol": pair,
                    "amount": vol,
                    "price_open": price,
                    "side": side,
                    "paper": False,
                    "status": "OPEN",
                    "order_txid": oid,
                    "exchange_result": details
                }
                state["open_trades"].append(order)
                trades.append(order)
                state["open_position"] = True
                save_state()
                save_trades()
                print(f"🔄 Imported manual {side.upper()} order from Kraken: txid={oid}")

    except Exception as e:
        print(f"⚠️ Failed to sync open orders: {e}")

print("🚀 Kraken Bot starting...")

# --- Main Loop ---
while True:
    now = datetime.now()

    # Daily reset
    today_str = str(date.today())
    if state.get("last_reset_date") != today_str:
        state["daily_trade_count"] = 0
        state["last_reset_date"] = today_str
        save_state()
        print(f"🔄 Daily reset applied at {now}")

    # Sync open trades from Kraken
    sync_open_orders()

    # Always update price
    price = get_current_price(config.get("symbol", "XXBTZGBP"))
    if price:
        state["last_price"] = price
        state["last_trade_time"] = str(now)
        save_state()
        print(f"[{now}] 📈 Price: £{price:,.2f}")
    else:
        print(f"[{now}] ⚠️ Failed to fetch price")
        time.sleep(30)
        continue

    # --- Trading Logic ---
    trade_amount = config.get("trade_amount", 0.001)
    dip_pct = config.get("dip_percentage", 2) / 100
    take_profit_pct = config.get("take_profit_pct", 5) / 100
    stop_loss_pct = config.get("stop_loss_pct", 3) / 100
    paper_mode = config.get("paper_trading", True)

    if not state["open_position"]:
        if state["last_price"] and len(trades) > 0:
            last_trade_price = trades[-1]["price_open"]
            drop = (last_trade_price - price) / last_trade_price
            if drop >= dip_pct:
                place_order("buy", config.get("symbol", "XXBTZGBP"), trade_amount, paper=paper_mode)
    else:
        open_trade = state["open_trades"][0]
        entry_price = open_trade["price_open"]
        pnl = ((price - entry_price) / entry_price) * 100

        if pnl >= (take_profit_pct * 100):
            close_order(open_trade, price, pnl, paper=paper_mode)
        elif pnl <= -(stop_loss_pct * 100):
            close_order(open_trade, price, pnl, paper=paper_mode)

    # Heartbeat
    max_trades = config.get("max_daily_trades", 3)
    print(f"[{now}] Bot heartbeat. Trades today: {state['daily_trade_count']} / {max_trades}")

    time.sleep(30)
