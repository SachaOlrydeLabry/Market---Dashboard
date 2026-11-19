"""Asset-specific Streamlit page."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import COUNTRY_10Y, US_CURVE
from data import fred
from analytics import cut
from ui import display_date, fmt, format_time_axis, observed_at, plot_layout, sidebar_window

# BONDS — Download 10Y yield series and align observations to comparable monthly dates.
# bonds() — Load country 10Y yield series, align monthly comparisons and render the chart.
def bonds():
    st.header("Government Bonds")
    # All configured countries are always included in the 10Y comparison.
    # International comparison is monthly; the US yield curve remains daily.
    countries = list(COUNTRY_10Y)
    window = sidebar_window("bonds")
    history = {country: fred(COUNTRY_10Y[country]) for country in countries}
    international = True  # Always compare all countries at monthly frequency.
    comparable = {country: (series.resample("MS").mean() if country == "US" and international else series)
                  for country, series in history.items()}
    if international:
        valid = [v.dropna() for v in comparable.values() if not v.empty]
        if len(valid) == len(countries):
            common_months = set(valid[0].index.to_period("M"))
            for v in valid[1:]:
                common_months &= set(v.index.to_period("M"))
            # Remove current unfinished month even if US has observations.
            current_month = pd.Timestamp.now().to_period("M")
            common_months = {m for m in common_months if m < current_month}
            latest_common = max(common_months) if common_months else None
        else:
            latest_common = None
        if latest_common is None:
            st.warning("No common completed monthly observation across the selected countries.")
            comparable = {}
        else:
            comparable = {k: v.loc[v.index.to_period("M") <= latest_common] for k, v in comparable.items()}
    rows = []
    for country, series in comparable.items():
        series = series.dropna()
        if not series.empty:
            rows.append({"Country": country, "Yield (%)": fmt(series.iloc[-1]),
                         "Observed at": observed_at(series.index),
                         "Frequency": "Monthly" if international else ("Daily" if country == "US" else "Monthly")})
    st.subheader("Latest 10Y government yields")
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.error("No comparable government yield observations available.")
    st.subheader("Government yield comparison — 10Y")
    fig = go.Figure()
    for country, series in comparable.items():
        selected = cut(series.dropna(), window)
        if not selected.empty:
            fig.add_trace(go.Scatter(x=selected.index, y=selected.values,
                                     mode="lines+markers" if international else "lines", name=country))
    if fig.data:
        plot_layout(fig, height=430, ytitle="Yield (%)", title="Government yield comparison — 10Y", hover=True)
        fig.update_xaxes(title="Date")
        st.plotly_chart(format_time_axis(fig), use_container_width=True)
    else:
        st.info("No comparable bond history for the selected period.")

    # Show the US yield curve separately, using daily observations.
    st.subheader("US Treasury Yield Curve")
    us_treasury_curve()

# US YIELD CURVE — Join maturity series by date before plotting one cross-section.
# us_treasury_curve() — Align US Treasury maturities on a common date and plot yield against tenor.
def us_treasury_curve():
    tenor_years = {"3M": 0.25, "2Y": 2., "5Y": 5., "10Y": 10., "30Y": 30.}
    curves = {tenor: fred(series_id) for tenor, series_id in US_CURVE.items()}
    available = {tenor: series for tenor, series in curves.items() if not series.empty}
    if len(available) >= 2:
        aligned = pd.concat(available, axis=1, join="inner").dropna()
        if not aligned.empty:
            last_date = aligned.index[-1]
            labels = [t for t in US_CURVE if t in aligned.columns]
            fig = go.Figure(go.Scatter(
                x=[tenor_years[t] for t in labels],
                y=[float(aligned.loc[last_date, t]) for t in labels],
                mode="lines+markers+text", text=labels, textposition="top center",
                line=dict(color="#2463ac", width=3), marker=dict(size=9)
            ))
            plot_layout(fig, height=380, ytitle="Yield (%)", title="US Treasury Yield Curve", xtitle="Maturity (years)")
            fig.update_xaxes(title="Maturity (years)")
            st.plotly_chart(format_time_axis(fig, date_axis=False), use_container_width=True)
            st.write(f"US Treasury curve · {display_date(last_date)}")
        else:
            st.warning("No common observation date across US Treasury maturities.")
    else:
        st.warning("Insufficient US Treasury observations.")

