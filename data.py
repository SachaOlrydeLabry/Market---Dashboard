"""Download and cache market and company data."""
from datetime import date, datetime, timezone
from io import StringIO
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=3600, show_spinner=False)
def prices(symbol):
    try:
        frame=yf.Ticker(symbol).history(period="max",auto_adjust=True)
        if frame.empty or "Close" not in frame:return pd.DataFrame()
        frame.index=pd.to_datetime(frame.index).tz_localize(None) if frame.index.tz is not None else pd.to_datetime(frame.index)
        frame.attrs["extracted_at_utc"] = datetime.now(timezone.utc).isoformat()
        return frame.sort_index()
    except Exception:return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def latest_prices(symbols):
    """Fetch short quotes in one request; full history remains on-demand."""
    try:
        data = yf.download(list(symbols), period="5d", interval="1d", auto_adjust=True,
                           progress=False, threads=True, group_by="ticker")
        stamp = datetime.now(timezone.utc)
        result = {}
        for symbol in symbols:
            try:
                close = data[symbol]["Close"].dropna() if len(symbols) > 1 else data["Close"].dropna()
                if not close.empty:
                    result[symbol] = (float(close.iloc[-1]), pd.Timestamp(close.index[-1]), stamp)
            except (KeyError, IndexError, TypeError):
                continue
        return result
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fred(series_id):
    if not series_id:return pd.Series(dtype=float)
    try:
        frame=pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",index_col=0,parse_dates=True,na_values=["."])
        series=pd.to_numeric(frame.iloc[:,0],errors="coerce").dropna()
        series.index=pd.to_datetime(series.index)
        return series.sort_index()
    except Exception:return pd.Series(dtype=float)

@st.cache_data(ttl=3600, show_spinner=False)
def boe(series_code):
    """BoE IADB CSV; values quoted in annual percent."""
    try:
        url="https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
        params={"csv.x":"1","Datefrom":"01/Jan/1990","Dateto":date.today().strftime("%d/%b/%Y"),"SeriesCodes":series_code,"CSVF":"TN","UsingCodes":"Y","VPD":"Y"}
        response=requests.get(url,params=params,timeout=25);response.raise_for_status()
        frame=pd.read_csv(StringIO(response.text),skiprows=0)
        # The BoE format can include introductory metadata: locate dated rows.
        for col in frame.columns:
            parsed=pd.to_datetime(frame[col],errors="coerce",dayfirst=True)
            if parsed.notna().sum()>10:
                other=[c for c in frame.columns if c!=col]
                if not other:break
                values=pd.to_numeric(frame[other[0]],errors="coerce")
                return pd.Series(values.to_numpy(),index=parsed,name=series_code).dropna().sort_index()
    except Exception:
        pass
    return pd.Series(dtype=float)

# usd_fx_series() — Get USD per unit of local currency; invert USD/local pairs where needed.
def usd_fx_series(currency):
    """USD received for one unit of currency, using Yahoo FX history."""
    if currency == "USD":
        return None
    if currency in ("EUR", "GBP", "AUD", "NZD"):
        frame = prices(f"{currency}USD=X")
        return frame.Close if not frame.empty else pd.Series(dtype=float)
    frame = prices(f"USD{currency}=X")
    return 1 / frame.Close.replace(0, np.nan) if not frame.empty else pd.Series(dtype=float)

# prices_in_usd() — Match each asset date to a recent FX quote and multiply to convert prices into USD.
def prices_in_usd(local_prices, currency):
    """Convert historical levels without look-ahead; no forward fill of stale FX."""
    if currency == "USD":
        return local_prices.dropna()
    fx = usd_fx_series(currency)
    if fx is None or fx.empty:
        return pd.Series(dtype=float)
    # Yahoo's daily series may be on different exchange calendars.
    # Align using the last observed FX quote, at most 4 calendar days old.
    target = local_prices.dropna().sort_index()
    quotes = fx.dropna().sort_index()
    left = pd.DataFrame({"date": target.index, "price": target.to_numpy()})
    right = pd.DataFrame({"fx_date": quotes.index, "fx": quotes.to_numpy()})
    aligned = pd.merge_asof(left, right, left_on="date", right_on="fx_date", direction="backward", tolerance=pd.Timedelta(days=4))
    values = aligned["price"] * aligned["fx"]
    return pd.Series(values.to_numpy(), index=target.index, dtype=float).dropna()

# STOCK DATA — Cache structured Yahoo metadata and financial statements separately.
@st.cache_data(ttl=3600, show_spinner=False)
def stock_info(ticker):
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def stock_financials(ticker):
    try:
        t=yf.Ticker(ticker)
        return t.income_stmt, t.balance_sheet, t.cashflow
    except Exception:return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()

