"""Financial calculations and date/FX alignment."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from config import RF_SOURCE, WINDOWS
from data import fred, prices

# 4. SHARED TOOLS — Risk formulas, FX conversion, charts, and formatting
# risk_free_daily() — Align US 2Y yields to return dates, then approximate daily financing accrual.
def risk_free_daily(currency, dates):
    """USD 2Y Treasury yield proxy; ACT/365 daily accrual approximation.

    A 2Y bond is NOT risk-free over a one-day holding period (duration risk).
    Its quoted yield is used as a short-horizon financing-rate proxy only.
    """
    if currency != "USD":
        return pd.Series(dtype=float), ""
    annual = fred("DGS2")
    if annual.empty:
        return pd.Series(dtype=float), ""
    idx = pd.DatetimeIndex(dates).tz_localize(None)
    aligned = annual.reindex(annual.index.union(idx)).sort_index().ffill().reindex(idx)
    elapsed = pd.Series(idx, index=idx).diff().dt.total_seconds().div(86400)
    # First return date uses the previous market observation: weekends count as calendar days.
    # Approximate financing accrual, rather than a realized Treasury bond return.
    elapsed = elapsed.fillna(1).clip(lower=1)
    daily = (1 + aligned / 100).pow(elapsed / 365.25) - 1
    return daily, RF_SOURCE["USD"]

def risk_metrics(series, currency):
    r=series.pct_change().dropna()
    if len(r)<2:return (float('nan'),)*4+("Insufficient observations",)
    vol=r.std(ddof=1)*np.sqrt(252)*100
    drawdown=series/series.cummax()-1
    mdd=drawdown.min()*100
    var=-np.quantile(r,.05)*100 if len(r)>=20 else np.nan
    rf,rf_label=risk_free_daily(currency,r.index)
    paired=pd.concat([r.rename("return"),rf.rename("rf")],axis=1).dropna() if not rf.empty else pd.DataFrame()
    if len(paired)>=20:
        excess=paired["return"]-paired["rf"]
        sd=excess.std(ddof=1)
        sharpe=excess.mean()/sd*np.sqrt(252) if sd>0 else np.nan
    else:sharpe=np.nan
    return vol,mdd,var,sharpe,rf_label

# cut() — Restrict a Series to the selected lookback measured backward from its last observation.
def cut(series,window):
    series=series.dropna().sort_index()
    if series.empty or WINDOWS[window] is None:return series
    return series.loc[series.index>=series.index[-1]-WINDOWS[window]]

# drawdown_details() — Find the worst peak-to-trough loss and first later recovery within the selected window.
def drawdown_details(series):
    """Peak, trough and first recovery of the worst in-window drawdown.

    A window beginning below an earlier all-time high cannot recover that
    earlier high: the peak is intentionally restricted to the chosen window.
    """
    s = series.dropna().sort_index()
    if s.empty or (s <= 0).any():
        return None
    dd = s.div(s.cummax()).sub(1)
    trough_date = dd.idxmin()
    peak_date = s.loc[:trough_date].idxmax()
    peak_price = float(s.loc[peak_date])
    after_trough = s.loc[s.index > trough_date]
    recovered = after_trough[after_trough >= peak_price]
    return {
        "mdd": float(dd.loc[trough_date] * 100),
        "peak_date": peak_date,
        "peak_price": peak_price,
        "trough_date": trough_date,
        "trough_price": float(s.loc[trough_date]),
        "recovery_date": recovered.index[0] if not recovered.empty else None,
    }

# FX HISTORY — Divide aligned USD legs to reconstruct the selected cross-rate series.
def fx_pair(base,quote):
    if base==quote:return pd.Series(dtype=float)
    # All quotes expressed as units of currency per USD, then cross-rate = quote-per-USD / base-per-USD.
    def per_usd(ccy):
        if ccy=="USD":return None
        if ccy in ("EUR","GBP","AUD","NZD"):
            df=prices(f"{ccy}USD=X")
            return 1/df.Close if not df.empty else pd.Series(dtype=float)
        df=prices(f"USD{ccy}=X")
        return df.Close if not df.empty else pd.Series(dtype=float)
    a=per_usd(base);b=per_usd(quote)
    if a is None:return b if b is not None else pd.Series(dtype=float)
    if b is None:return 1/a
    aligned=pd.concat([a.rename("a"),b.rename("b")],axis=1).ffill().dropna()
    return aligned.b/aligned.a

# fin_value() — Look up the first available matching financial statement row and period.
def fin_value(table, names, period=0):
    if table is None or table.empty or period>=len(table.columns):return np.nan
    for name in names:
        if name in table.index:
            v=pd.to_numeric(table.loc[name].iloc[period],errors="coerce")
            if pd.notna(v):return float(v)
    return np.nan

# valid_number() — Check whether a financial input is a usable finite number.
def valid_number(value):
    return isinstance(value, (int, float, np.integer, np.floating)) and np.isfinite(value)

# dated_column() — Find a statement column by its fiscal period position.
def dated_column(table, position=0):
    """Actual fiscal statement column date; never substitute today's date."""
    if table is None or table.empty or len(table.columns) <= position:
        return None
    try:
        return pd.Timestamp(table.columns[position])
    except (ValueError, TypeError):
        return None

# fiscal_label() — Convert a financial statement column into a fiscal date label.
def fiscal_label(table, position=0):
    dt = dated_column(table, position)
    return dt.strftime("%d %b %y") if dt is not None else None

# aligned_fiscal_values() — Extract financial statement values only for matching fiscal periods.
def aligned_fiscal_values(table, row_names, positions):
    """Require the actual dates and values to exist before displaying a comparison."""
    result = []
    for pos in positions:
        value = fin_value(table, row_names, pos)
        dt = dated_column(table, pos)
        if not valid_number(value) or dt is None:
            return None
        result.append((value, dt))
    return result

