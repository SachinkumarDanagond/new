import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper

st.set_page_config(page_title="BankNifty OI Strategy + PCR", layout="wide")

st.title("📊 BankNifty Option Strategy with PCR (Live Data)")
st.markdown("Live Open Interest signals with Buy/Target/SL + PCR Analysis")

@st.cache_data(ttl=300)
def fetch_option_chain():
    try:
        data = nse_optionchain_scrapper("BANKNIFTY")
        records = data['records']['data']
        underlying = data['records']['underlyingValue']

        rows = []
        ce_oi_total = 0
        pe_oi_total = 0

        for item in records:
            strike = item['strikePrice']
            ce = item.get("CE")
            pe = item.get("PE")

            if ce:
                ce_oi_total += ce.get("openInterest", 0)
                rows.append({
                    "strike": strike, "type": "CE", "oi": ce.get("openInterest", 0),
                    "change_oi": ce.get("changeinOpenInterest", 0), "ltp": ce.get("lastPrice", 0)
                })
            if pe:
                pe_oi_total += pe.get("openInterest", 0)
                rows.append({
                    "strike": strike, "type": "PE", "oi": pe.get("openInterest", 0),
                    "change_oi": pe.get("changeinOpenInterest", 0), "ltp": pe.get("lastPrice", 0)
                })

        df = pd.DataFrame(rows)
        df["oi_change_pct"] = (df["change_oi"] / df["oi"].replace(0, 1)) * 100
        df["strategy"] = df.apply(analyze_strategy, axis=1)
        df = pd.concat([df.drop(["strategy"], axis=1), df["strategy"].apply(pd.Series)], axis=1)

        pcr = round(pe_oi_total / ce_oi_total, 2) if ce_oi_total else 0
        return df.sort_values(by="oi", ascending=False), underlying, pcr
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return None, None, None

def analyze_strategy(row):
    if row["change_oi"] > 0 and row["oi_change_pct"] > 10:
        signal = "Call Long Buildup" if row["type"] == "CE" else "Put Long Buildup"
        buy_price = row["ltp"]
        return {
            "signal": signal,
            "buy_price": buy_price,
            "target": round(buy_price * 1.3, 2),
            "stop_loss": round(buy_price * 0.85, 2)
        }
    elif row["change_oi"] < 0:
        signal = "Call Short Covering" if row["type"] == "CE" else "Put Short Covering"
        return {
            "signal": signal,
            "buy_price": row["ltp"],
            "target": None,
            "stop_loss": None
        }
    return {"signal": "Neutral", "buy_price": None, "target": None, "stop_loss": None}

# Fetch and display
df, spot, pcr = fetch_option_chain()
if df is not None:
    st.subheader(f"📈 BANKNIFTY Spot Price: {spot}")
    st.metric("Put Call Ratio (PCR)", pcr, help="PCR > 1 is bullish, < 1 is bearish")

    st.dataframe(df[["strike", "type", "ltp", "oi", "change_oi", "oi_change_pct",
                     "signal", "buy_price", "target", "stop_loss"]].reset_index(drop=True),
                 use_container_width=True)
else:
    st.warning("No data available.")
