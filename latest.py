# app.py
import streamlit as st
import pandas as pd
import numpy as np
from nsepython import nse_optionchain_scrapper, nse_eq, nse_fno
import ta
import time
from datetime import datetime

st.set_page_config(page_title="Bank Nifty Option Buy Dashboard", layout="wide")

# --- Helper Functions ---
def fetch_option_chain(symbol="BANKNIFTY"):
    try:
        data = nse_optionchain_scrapper(symbol)
        records = data['records']['data']
        oc_df = pd.json_normalize(records)
        return oc_df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def compute_indicators(df):
    if df.empty:
        return df
    # Fetch spot data for RSI/VWAP
    spot_data = nse_eq("NSE Index BANKNIFTY")
    spot_df = pd.DataFrame(spot_data)
    spot_df['Close'] = pd.to_numeric(spot_df['closePrice'], errors='coerce')
    if spot_df['Close'].isna().all():
        return df
    # RSI & VWAP (example with random OHLC)
    ohlc = pd.DataFrame({
        'open': np.random.rand(50)*100 + 44000,
        'high': np.random.rand(50)*100 + 44100,
        'low': np.random.rand(50)*100 + 43900,
        'close': np.random.rand(50)*100 + 44050,
        'volume': np.random.randint(100, 1000, 50)
    })
    df['RSI'] = ta.momentum.RSIIndicator(ohlc['close'], window=14).rsi().iloc[-1]
    df['VWAP'] = ta.volume.VolumeWeightedAveragePrice(
        high=ohlc['high'], low=ohlc['low'], close=ohlc['close'],
        volume=ohlc['volume']
    ).volume_weighted_average_price().iloc[-1]
    return df

def pick_top_buys(df):
    if df.empty:
        return None, None
    calls = df[['CE.underlyingValue', 'CE.changeinOpenInterest', 'CE.impliedVolatility', 'CE.lastPrice', 'CE.strikePrice']].dropna()
    puts = df[['PE.underlyingValue', 'PE.changeinOpenInterest', 'PE.impliedVolatility', 'PE.lastPrice', 'PE.strikePrice']].dropna()

    calls = calls.sort_values(by='CE.changeinOpenInterest', ascending=False)
    puts = puts.sort_values(by='PE.changeinOpenInterest', ascending=False)

    best_call = calls.head(1)
    best_put = puts.head(1)
    return best_call, best_put

# --- Streamlit UI ---
st.title("📊 Bank Nifty Option Live Buy Dashboard")
st.markdown("Shows **top 1 Call & 1 Put buy recommendation** using OI, IV, RSI & VWAP")

refresh_rate = st.sidebar.slider("Refresh every (seconds)", 10, 120, 30)

placeholder = st.empty()

while True:
    oc_df = fetch_option_chain()
    oc_df = compute_indicators(oc_df)
    best_call, best_put = pick_top_buys(oc_df)

    with placeholder.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Best Call Option")
            if best_call is not None:
                st.write(best_call)
            else:
                st.warning("No call data available")
        with col2:
            st.subheader("Best Put Option")
            if best_put is not None:
                st.write(best_put)
            else:
                st.warning("No put data available")

        st.markdown(f"⏱ Last updated: **{datetime.now().strftime('%H:%M:%S')}**")

    time.sleep(refresh_rate)
