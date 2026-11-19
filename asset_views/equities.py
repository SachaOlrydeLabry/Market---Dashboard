"""Asset-specific Streamlit page."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import INDEX_CURRENCY, INDICES
from data import prices, prices_in_usd
from analytics import cut, drawdown_details, risk_metrics
from ui import chart, display_date, fmt, observed_at, remembered_widget, sidebar_window, source

# 5. DASHBOARD PAGES — One function per asset class
# EQUITIES — Fetch only the chosen index, then pass its prices to shared risk/chart helpers.
# equities() — Read sidebar selections, fetch index prices, compute risk metrics and render widgets.
def equities():
    window=sidebar_window("equities")
    st.header("Equities")
    name=remembered_widget("selectbox", "Index", options=[None,*INDICES], key="equity_index", format_func=lambda x: x or "Select an index…")
    if name is None:
        st.info("Select an index in the sidebar to start the analysis.")
        return
    frame=prices(INDICES[name])
    if frame.empty:st.error("Index data unavailable.");return
    series=cut(frame.Close,window)
    if len(series)<3:st.warning("Insufficient observations for this lookback.");return
    total_return=(series.iloc[-1]/series.iloc[0]-1)*100
    st.subheader("Latest price")
    st.dataframe(pd.DataFrame([{"Asset":name,"Last price":fmt(frame.Close.iloc[-1]),"Observed at":observed_at(frame.index)}]),hide_index=True,use_container_width=True)
    st.metric(f"Price return — {window} lookback",fmt(total_return)+"%")
    chart(series,ytitle="Index Price")
    # Convert index returns to USD before comparing them with the US 2Y rate.
    usd_series = prices_in_usd(frame.Close, INDEX_CURRENCY[name])
    usd_window = cut(usd_series, window)
    native_vol, native_mdd, native_var, _, _ = risk_metrics(series, "")
    _, _, _, sharpe, rf_label = risk_metrics(usd_window, "USD") if len(usd_window) >= 3 else (np.nan,)*4+("",)
    vol, mdd, var = native_vol, native_mdd, native_var
    dd_info = drawdown_details(series)
    st.subheader("Risk indicators")
    with st.container(key="risk_indicators"):
        a,b,c,d=st.columns(4)
        a.metric("Realised volatility (annualised)",fmt(vol)+"%")
        if dd_info is not None:
            recovery = (f'Recovered on {display_date(dd_info["recovery_date"])}'
                        if dd_info["recovery_date"] is not None else 'Not yet recovered')
            b.markdown(f"""
<div class="mdd-panel">
  <div class="mdd-label">Maximum drawdown</div>
  <div class="mdd-value">{fmt(dd_info['mdd'])}%</div>
  <div class="mdd-detail"><strong>Peak:</strong> {fmt(dd_info['peak_price'])} · {display_date(dd_info['peak_date'])}</div>
  <div class="mdd-detail"><strong>Trough:</strong> {fmt(dd_info['trough_price'])} · {display_date(dd_info['trough_date'])}</div>
  <div class="mdd-detail"><strong>Recovery:</strong> {recovery}</div>
</div>""", unsafe_allow_html=True)
        if np.isfinite(var):c.metric("Historical VaR 95% (1D)",fmt(var)+"%")
        if np.isfinite(sharpe):
            d.metric("Sharpe (USD, US 2Y Rf)",fmt(sharpe))
    st.caption("Volatility, VaR, drawdown and price return: native index units. Sharpe: USD-converted returns, US 2Y yield as an approximate funding-rate proxy.")
    source(series,"Yahoo Finance via yfinance; daily adjusted prices, 252 trading days/year")

