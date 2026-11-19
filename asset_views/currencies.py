"""Asset-specific Streamlit page."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import FX_CODES
from data import latest_prices
from analytics import cut, fx_pair
from ui import chart, sidebar_window, source

# FX SPOT MATRIX — Batch-fetch USD legs and calculate cross-rates by division.
def fx_spot_matrix():
    """Spot quotes use a short batch request; selected pair history loads separately."""
    direct = ("EUR", "GBP", "AUD", "NZD")
    symbols = {ccy: (f"{ccy}USD=X" if ccy in direct else f"USD{ccy}=X")
               for ccy in FX_CODES if ccy != "USD"}
    quotes = latest_prices(tuple(symbols.values()))
    latest = {"USD": 1.0}
    extraction_times = []
    for ccy, symbol in symbols.items():
        if symbol not in quotes:
            continue
        value, _, stamp = quotes[symbol]
        if value <= 0:
            continue
        latest[ccy] = 1 / value if ccy in direct else value
        extraction_times.append(stamp)
    matrix = pd.DataFrame(index=FX_CODES, columns=FX_CODES, dtype=float)
    for base in FX_CODES:
        for quote in FX_CODES:
            if base in latest and quote in latest:
                matrix.loc[base, quote] = latest[quote] / latest[base]
    return matrix, len(latest), extraction_times

# select_fx_pair() — Save a clicked FX pair in Streamlit session state.
def select_fx_pair(base, quote):
    """Callback executes before the next Streamlit run; no second rerun needed."""
    st.session_state.fx_base = base
    st.session_state.fx_quote = quote

# CURRENCIES — Build matrix controls, then load the selected pair chart on demand.
# currencies() — Render the FX matrix, selected pair history and quote extraction timestamps.
def currencies():
    window=sidebar_window("currencies")
    st.header("Currencies")
    st.subheader("Spot matrix")
    matrix,available_count,extraction_times=fx_spot_matrix()
    if available_count<2:st.warning("FX data unavailable.");return
    if extraction_times and len(extraction_times) == available_count - 1:
        earliest, latest = min(extraction_times), max(extraction_times)
        time_fmt = "%d %b %y — %H:%M:%S UTC"
        if earliest == latest:
            st.write(f"Yahoo Finance data extracted: {latest.strftime(time_fmt)}")
        else:
            st.write(f"Yahoo Finance data extracted: {earliest.strftime(time_fmt)} to {latest.strftime(time_fmt)}")
    else:
        st.write("Extraction timestamp not recorded in the existing cache. Use Refresh market data once to record it.")
    if "fx_base" not in st.session_state:st.session_state.fx_base=None
    if "fx_quote" not in st.session_state:st.session_state.fx_quote=None
    # Buttons are genuine Streamlit widgets: clicking a rate selects the pair.
    headers=st.columns([0.75]+[1]*len(FX_CODES),gap="small")
    for j,code in enumerate(FX_CODES):headers[j+1].markdown(f"**{code}**")
    for base_code in FX_CODES:
        cells=st.columns([0.75]+[1]*len(FX_CODES),gap="small")
        cells[0].markdown(f"**{base_code}**")
        for j,quote_code in enumerate(FX_CODES):
            rate=matrix.loc[base_code,quote_code]
            label=f"{rate:.2f}" if pd.notna(rate) else "—"
            active=(base_code==st.session_state.fx_base and quote_code==st.session_state.fx_quote)
            cells[j+1].button(
                label, key=f"fx_{base_code}_{quote_code}",
                disabled=(base_code == quote_code or pd.isna(rate)),
                type="primary" if active else "secondary", width="stretch",
                on_click=select_fx_pair, args=(base_code, quote_code),
            )
    base=st.session_state.fx_base
    quote=st.session_state.fx_quote
    if base is None or quote is None:
        st.info("Select a currency pair in the spot matrix to display its history.")
        return
    st.subheader(f"{base}/{quote}")
    if base==quote:st.info("Choose two different currencies.");return
    s=fx_pair(base,quote)
    if s.empty:st.warning("FX history unavailable.");return
    chart(cut(s,window),ytitle=f"{quote} per 1 {base}")
    source(s,"Yahoo Finance via yfinance")

