# app_live_banknifty.py

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import time
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from nsepython import nse_optionchain_scrapper

st.set_page_config(page_title="Live Bank Nifty Option Buys", layout="wide")
st.title("Live Bank Nifty Intraday + 2-Buy Signals Dashboard")

# Persistent session for NSE access
session = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
}

def fetch_intraday(symbol="BANKNIFTY", interval="5"):
    try:
        # initialize cookies
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol}&interval={interval}"
        resp = session.get(url, headers=HEADERS, timeout=5)
        data = resp.json()
        timestamps = data["metadata"]["times"]
        ohlcvs = data["data"]
        df = pd.DataFrame(ohlcvs, columns=["Open", "High", "Low", "Close", "Volume"])
        df["Datetime"] = pd.to_datetime(timestamps, unit="ms")
        return df.set_index("Datetime")
    except Exception as e:
        st.error(f"Intraday fetch error: {e}")
        return pd.DataFrame()

def fetch_option_chain(symbol="BANKNIFTY"):
    try:
        df = nse_optionchain_scrapper(symbol)["records"]["data"]
        return pd.json_normalize(df)
    except Exception as e:
        st.error(f"Option chain fetch error: {e}")
        return pd.DataFrame()

def compute_indicators(df):
    if df.empty:
        return df
    vwap = VolumeWeightedAveragePrice(df["High"], df["Low"], df["Close"], df["Volume"], window=14)
    df["VWAP"] = vwap.volume_weighted_average_price()
    rsi = RSIIndicator(df["Close"], window=14)
    df["RSI"] = rsi.rsi()
    return df

def pick_top_buy(oc_df, side="CE"):
    key = f"{side}.changeinOpenInterest"
    if oc_df.empty or key not in oc_df.columns:
        return None
    col = oc_df[[f"{side}.strikePrice", key, f"{side}.lastPrice", f"{side}.impliedVolatility"]].dropna()
    if col.empty:
        return None
    best = col.sort_values(by=key, ascending=False).iloc[0]
    return best

# Sidebar refresh control
refresh = st.sidebar.slider("Auto-refresh every (s)", 30, 300, 60)
manual_refresh = st.sidebar.button("Refresh Now")

# Main loop with placeholder for live update
placeholder = st.empty()

def render():
    df_intraday = fetch_intraday()
    df_intraday = compute_indicators(df_intraday)

    oc = fetch_option_chain()
    best_ce = pick_top_buy(oc, "CE")
    best_pe = pick_top_buy(oc, "PE")

    with placeholder.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Intraday Price vs VWAP")
            if not df_intraday.empty:
                st.line_chart(df_intraday[["Close", "VWAP"]])
                st.subheader("RSI")
                st.line_chart(df_intraday["RSI"])
            else:
                st.write("No intraday data.")

        with col2:
            st.subheader("Top Buy Call Signal")
            if best_ce is not None:
                st.write(f"Strike: {best_ce[f'CE.strikePrice']}")
                st.write(f"OI Change: {best_ce[f'CE.changeinOpenInterest']}")
                st.write(f"IV: {best_ce[f'CE.impliedVolatility']:.2f}")
                st.write(f"LTP: {best_ce[f'CE.lastPrice']}")
            else:
                st.write("No Call signal.")

            st.subheader("Top Buy Put Signal")
            if best_pe is not None:
                st.write(f"Strike: {best_pe[f'PE.strikePrice']}")
                st.write(f"OI Change: {best_pe[f'PE.changeinOpenInterest']}")
                st.write(f"IV: {best_pe[f'PE.impliedVolatility']:.2f}")
                st.write(f"LTP: {best_pe[f'PE.lastPrice']}")
            else:
                st.write("No Put signal.")

            st.markdown(f"**Last update**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initial render
render()

# Auto-refresh loop
while True:
    if manual_refresh:
        render()
    else:
        time.sleep(refresh)
        render()
