"""Reusable Streamlit controls, Plotly charts, and formatting."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import DATE_FORMAT, PLOT_DATE_FORMAT, WINDOWS
from analytics import valid_number

# display_date() — Convert a timestamp to the shared short date format.
def display_date(value):
    """Date-only sources never acquire an invented observation time."""
    ts = pd.Timestamp(value)
    return ts.strftime(DATE_FORMAT)

# observed_at() — Build a readable last-observation timestamp from the data index.
def observed_at(index):
    if len(index) == 0:
        return "No observation"
    ts = pd.Timestamp(index[-1])
    # Only show a time if the source actually provides one.
    if ts.hour or ts.minute or ts.second:
        return ts.strftime(DATE_FORMAT + " %H:%M:%S")
    return display_date(ts)

# format_time_axis() — Apply consistent date ticks and two-decimal hover labels to Plotly traces.
def format_time_axis(fig, *, date_axis=True):
    """Limit numeric display to two decimals without rounding source data."""
    if date_axis:
        fig.update_xaxes(tickformat=PLOT_DATE_FORMAT, hoverformat=PLOT_DATE_FORMAT)
    fig.update_yaxes(tickformat=",.2f", hoverformat=",.2f")
    for trace in fig.data:
        if trace.type in ("scatter", "scattergl", "bar"):
            trace.update(hovertemplate="%{y:,.2f}<extra>%{fullData.name}</extra>")
    return fig

# remembered_widget() — Store sidebar selections in session_state so switching pages does not reset them.
def remembered_widget(kind, label, *, key, options=None, default=None, **kwargs):
    """Keep user selections while pages/widgets are temporarily not rendered.

    Streamlit removes a widget's own state when navigating away; the independent
    saved key survives for the lifetime of the browser session.
    """
    saved_key = f"saved_{key}"
    widget_key = f"widget_{key}"
    if saved_key not in st.session_state:
        st.session_state[saved_key] = default
    saved = st.session_state[saved_key]
    if options is not None:
        if kind == "multiselect":
            saved = [x for x in (saved or []) if x in options]
        elif saved not in options:
            saved = default if default in options else None
        st.session_state[saved_key] = saved
    # Rehydrate the widget on every visit, including after Streamlit cleans its key.
    st.session_state[widget_key] = saved

    def save():
        st.session_state[saved_key] = st.session_state[widget_key]

    fn = getattr(st.sidebar, kind)
    if kind == "text_input":
        return fn(label, key=widget_key, on_change=save, **kwargs)
    return fn(label, options, key=widget_key, on_change=save, **kwargs)

# sidebar_window() — Create the lookback selector using the reusable session-state helper.
def sidebar_window(key):
    return remembered_widget("selectbox", "Lookback", key=f"window_{key}",
                             options=list(WINDOWS), default="1Y")

# plot_layout() — Apply the shared Plotly template, dimensions, margins and axis titles.
def plot_layout(fig, *, height=390, ytitle=None, title=None, xtitle="Date", top=50, hover=False):
    """Consistent layout for all Plotly figures; does not alter chart data."""
    fig.update_layout(
        template="plotly_white", height=height, title=title or ytitle or "Market chart",
        xaxis_title=xtitle,
        yaxis_title=ytitle, margin=dict(l=12, r=12, t=top, b=12),
        **({"hovermode": "x unified"} if hover else {}),
    )
    return fig

# chart() — Build a reusable line/bar Plotly chart from a Pandas Series and display it.
def chart(series,title=None,ytitle=None,kind="line",height=390):
    fig=go.Figure()
    if kind=="bar":fig.add_trace(go.Bar(x=series.index,y=series.values,marker_color="#2463ac"))
    else:fig.add_trace(go.Scatter(x=series.index,y=series.values,mode="lines",line=dict(color="#2463ac",width=2.4),name=title or "Value"))
    plot_layout(fig, height=height, ytitle=ytitle, title=title or ("Calendar-year price changes" if kind == "bar" else ytitle),
                xtitle="Year" if kind == "bar" else "Date", hover=True)
    st.plotly_chart(format_time_axis(fig, date_axis=kind != "bar"), width="stretch")

# source() — Show the data source and last observation in a collapsible Streamlit panel.
def source(series,label):
    if not series.empty:
        with st.expander("Data source", expanded=False):
            st.write(f"{label} | Last observation: {observed_at(series.index)}")

# fmt() — Format a finite number for display, capped at two decimal places.
def fmt(value,digits=2):
    digits=min(max(int(digits),0),2)
    return f"{value:,.{digits}f}" if pd.notna(value) and np.isfinite(value) else ""

# compact() — Scale large numbers to millions/billions/trillions without changing raw data.
def compact(value,currency=""):
    if not isinstance(value,(int,float)) or not np.isfinite(value):return ""
    a=abs(value)
    if a>=1e12:return f"{value/1e12:,.2f} tn {currency}".strip()
    if a>=1e9:return f"{value/1e9:,.2f} bn {currency}".strip()
    if a>=1e6:return f"{value/1e6:,.2f} mn {currency}".strip()
    return f"{value:,.0f} {currency}".strip()

# format_number() — Format a financial value with its unit while hiding missing values.
def format_number(value, suffix="", decimals=2):
    return f"{value:,.{decimals}f}{suffix}" if valid_number(value) else None

# financial_table() — Render a simple Metric/Value/Period table, omitting unavailable entries.
def financial_table(items, title):
    """Omit missing metrics, not just their values; never print N/A."""
    rows = [dict(Metric=label, Value=value, Period=period)
            for label, value, period in items
            if value is not None and period]
    if rows:
        st.subheader(title)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# financial_comparison_table() — Compare current/prior fiscal values and choose % change, pp or x by unit.
def financial_comparison_table(title, entries):
    """entries: (metric, current, prior, current_date, prior_date, display_type)."""
    rows=[]
    for metric, current, prior, current_date, prior_date, unit in entries:
        if not valid_number(current) or current_date is None:
            continue
        formatter = (lambda x: compact(x, unit[4:])) if unit.startswith("amt:") else (lambda x: fmt(x) + unit)
        change = ""
        if valid_number(prior) and prior_date is not None:
            if unit == "%":
                change = f"{fmt(current-prior)} pp"
            elif unit == "x":
                change = f"{fmt(current-prior)}x"
            elif prior > 0:
                change = f"{fmt((current/prior-1)*100)}%"
        rows.append({"Metric": metric,
                     f"Value for {display_date(current_date)}": formatter(current),
                     f"Previous · {display_date(prior_date)}" if valid_number(prior) and prior_date is not None else "Previous":
                         formatter(prior) if valid_number(prior) else "",
                     "Change": change})
    if rows:
        st.subheader(title)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

