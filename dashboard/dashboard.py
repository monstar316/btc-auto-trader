import streamlit as st
import json
import os
import krakenex
from pykrakenapi import KrakenAPI
from streamlit_autorefresh import st_autorefresh

# Load config
with open("config.json") as f:
    config = json.load(f)

# Kraken connection
api = krakenex.API()
api.load_key('kraken.key')  # Make sure you have your key file
k = KrakenAPI(api)

# Auto refresh every 10s
count = st_autorefresh(interval=10000, key="Refresh")

st.title("Defensive Stock Bot Dashboard")

# Display config
st.subheader("Configuration")
st.json(config)

# Fetch ticker data
pair = config["trading"]["pair"]

try:
    ticker, _ = k.get_ticker_information(pair)
    current_price = float(ticker["c"][0][0])  # last trade price
    st.metric(label=f"{pair} Price", value=f"${current_price:.2f}")
except Exception as e:
    st.error(f"Error fetching price: {e}")

# Fetch open orders
st.subheader("Open Orders")
try:
    open_orders, _ = k.get_open_orders()
    if open_orders.empty:
        st.write("✅ No open orders")
    else:
        st.dataframe(open_orders)
except Exception as e:
    st.error(f"Error fetching open orders: {e}")

# Fetch closed orders (history)
st.subheader("Closed Orders")
try:
    closed_orders, _ = k.get_closed_orders()
    if closed_orders.empty:
        st.write("ℹ️ No closed orders yet")
    else:
        st.dataframe(closed_orders.tail(10))
except Exception as e:
    st.error(f"Error fetching closed orders: {e}")
