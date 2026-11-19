"""Asset-specific Streamlit page."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import COMMODITIES, COMMODITY_UNITS
from data import latest_prices, prices
from analytics import cut
from ui import chart, display_date, fmt, remembered_widget, sidebar_window, source

# COMMODITIES — Batch-fetch quotes; fetch a full history only for the selected future.
# commodities() — Fetch short futures quotes, then load full history only for the chosen contract.
def commodities():
    window=sidebar_window("commodities")
    st.header("Commodities")
    name=remembered_widget("selectbox", "Commodity", options=[None,*COMMODITIES],
                             key="commodity_choice", format_func=lambda x: x or "Select a commodity…")
    if name is None:
        st.info("Select a commodity in the sidebar to start the analysis.")
        return
    st.subheader("Latest prices")
    quotes = latest_prices(tuple(COMMODITIES.values()))
    rows = []
    for asset, symbol in COMMODITIES.items():
        if symbol in quotes:
            value, observed, _ = quotes[symbol]
            rows.append({"Asset": asset, "Last price": fmt(value) + " " + COMMODITY_UNITS[asset][0],
                         "Unit": COMMODITY_UNITS[asset][1], "Observed at": display_date(observed)})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    df=prices(COMMODITIES[name])
    if df.empty:st.warning("Data unavailable.");return
    st.subheader(f"{name} — historical price")
    chart(cut(df.Close,window),ytitle=f"Futures price ({COMMODITY_UNITS[name][0]} / {COMMODITY_UNITS[name][1]})")
    year_end=df.Close.resample("YE").last()
    returns=year_end.pct_change().dropna()*100
    # Exclude the incomplete current calendar year from annual returns.
    returns=returns[returns.index.year<date.today().year]
    st.subheader("Calendar-year price changes")
    if not returns.empty:
        bars=pd.Series(returns.values,index=returns.index.year.astype(str))
        chart(bars,ytitle="Price change (%)",kind="bar")
    source(df.Close,"Yahoo Finance via yfinance; continuous futures, not investable total returns")

