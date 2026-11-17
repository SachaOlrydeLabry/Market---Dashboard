"""Market Dashboard — Sacha Olry de Labry."""
from datetime import date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market Dashboard", page_icon="📊", layout="wide")
st.markdown('''<style>
.stApp{background:#fff;color:#10213a} [data-testid="stSidebar"]{background:#0b1930}
[data-testid="stSidebar"] *{color:#f2f6fd!important}
h1,h2,h3{color:#0b1930!important}
[data-testid="stMetric"]{background:#eef3f9;border:1px solid #d9e5f2;border-radius:10px;padding:12px}
[data-testid="stSidebar"] .stRadio label{font-size:0.95rem}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#fff!important;color:#10213a!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div *{color:#10213a!important}
[data-testid="stSidebar"] input{color:#10213a!important}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *{color:#f2f6fd!important}
[data-testid="stMetricValue"]{font-size:1.65rem!important;overflow-wrap:anywhere}
[data-testid="stMetricLabel"]{font-size:.84rem!important}
</style>''', unsafe_allow_html=True)

INDICES={"S&P 500":"^GSPC","Nasdaq 100":"^NDX","Dow Jones":"^DJI","Russell 2000":"^RUT","STOXX Europe 600":"^STOXX","EURO STOXX 50":"^STOXX50E","CAC 40":"^FCHI","DAX":"^GDAXI","FTSE 100":"^FTSE","SMI":"^SSMI","Nikkei 225":"^N225","TOPIX":"^TOPX","Hang Seng":"^HSI","CSI 300":"000300.SS","Nifty 50":"^NSEI"}
COMMODITY_UNITS={"Gold":("USD","troy oz"),"Silver":("USD","troy oz"),"Copper":("USD","lb"),"WTI crude":("USD","barrel"),"Brent crude":("USD","barrel"),"Natural gas":("USD","MMBtu"),"Wheat":("US cents","bushel"),"Corn":("US cents","bushel")}
COMMODITIES={"Gold":"GC=F","Silver":"SI=F","Copper":"HG=F","WTI crude":"CL=F","Brent crude":"BZ=F","Natural gas":"NG=F","Wheat":"ZW=F","Corn":"ZC=F"}
FX_CODES=["USD","EUR","GBP","JPY","CHF","AUD","CAD","NZD"]
US_CURVE={"3M":"DGS3MO","2Y":"DGS2","5Y":"DGS5","10Y":"DGS10","30Y":"DGS30"}
# FRED OECD long-term government bond yields: monthly observations, generally 10-year benchmark.
COUNTRY_10Y={"US":"DGS10","UK":"IRLTLT01GBM156N","France":"IRLTLT01FRM156N","Germany":"IRLTLT01DEM156N","Japan":"IRLTLT01JPM156N","Switzerland":"IRLTLT01CHM156N"}
WINDOWS={"1M":pd.DateOffset(months=1),"3M":pd.DateOffset(months=3),"6M":pd.DateOffset(months=6),"1Y":pd.DateOffset(years=1),"3Y":pd.DateOffset(years=3),"5Y":pd.DateOffset(years=5),"10Y":pd.DateOffset(years=10),"Max":None}

@st.cache_data(persist="disk",show_spinner=False)
def prices(symbol):
    try:
        frame=yf.Ticker(symbol).history(period="max",auto_adjust=True)
        if frame.empty or "Close" not in frame:return pd.DataFrame()
        frame.index=pd.to_datetime(frame.index).tz_localize(None) if frame.index.tz is not None else pd.to_datetime(frame.index)
        return frame.sort_index()
    except Exception:return pd.DataFrame()

@st.cache_data(persist="disk",show_spinner=False)
def fred(series_id):
    if not series_id:return pd.Series(dtype=float)
    try:
        frame=pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",index_col=0,parse_dates=True,na_values=["."])
        series=pd.to_numeric(frame.iloc[:,0],errors="coerce").dropna()
        series.index=pd.to_datetime(series.index)
        return series.sort_index()
    except Exception:return pd.Series(dtype=float)

def cut(series,window):
    series=series.dropna().sort_index()
    if series.empty or WINDOWS[window] is None:return series
    return series.loc[series.index>=series.index[-1]-WINDOWS[window]]

def observed_at(index, frequency="daily"):
    """Do not invent a time for date-only daily or monthly source observations."""
    if len(index)==0:return "Unavailable"
    ts=pd.Timestamp(index[-1])
    if frequency=="intraday" and (ts.hour or ts.minute or ts.second):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return ts.strftime("%Y-%m-%d") + (" (monthly)" if frequency=="monthly" else " (daily)")

def sidebar_window(key):
    return st.sidebar.selectbox("Lookback",list(WINDOWS),index=3,key=f"window_{key}")

def chart(series,title=None,ytitle=None,kind="line",height=390):
    fig=go.Figure()
    if kind=="bar":fig.add_trace(go.Bar(x=series.index,y=series.values,marker_color="#2463ac"))
    else:fig.add_trace(go.Scatter(x=series.index,y=series.values,mode="lines",line=dict(color="#2463ac",width=2.4),name=title or "Value"))
    fig.update_layout(template="plotly_white",height=height,margin=dict(l=12,r=12,t=30,b=12),title=title,yaxis_title=ytitle,hovermode="x unified")
    st.plotly_chart(fig,use_container_width=True)

def source(series,label):
    if not series.empty:st.caption(f"Source: {label} | Last observation: {observed_at(series.index)}")

def fmt(value,digits=2):
    return f"{value:,.{digits}f}" if pd.notna(value) and np.isfinite(value) else "N/A"

def compact(value,currency=""):
    if not isinstance(value,(int,float)) or not np.isfinite(value):return "N/A"
    a=abs(value)
    if a>=1e12:return f"{value/1e12:,.2f} tn {currency}".strip()
    if a>=1e9:return f"{value/1e9:,.2f} bn {currency}".strip()
    if a>=1e6:return f"{value/1e6:,.2f} mn {currency}".strip()
    return f"{value:,.0f} {currency}".strip()

def equities():
    window=sidebar_window("equities")
    st.header("Equities")
    name=st.sidebar.selectbox("Index",list(INDICES),key="equity_index")
    frame=prices(INDICES[name])
    if frame.empty:st.error("Index data unavailable.");return
    series=cut(frame.Close,window)
    if len(series)<3:st.warning("Insufficient observations for this lookback.");return
    st.subheader("Latest price")
    st.dataframe(pd.DataFrame([{"Asset":name,"Last price":fmt(frame.Close.iloc[-1]),"Observed at":observed_at(frame.index)}]),hide_index=True,use_container_width=True)
    chart(series,ytitle="Index Price")
    r=series.pct_change().dropna()
    volatility=r.std(ddof=1)*np.sqrt(252)*100
    drawdown=series/series.cummax()-1
    mdd=drawdown.min()*100
    mdd_date=drawdown.idxmin().strftime("%Y-%m-%d")
    var=-np.quantile(r,.05)*100 if len(r)>=20 else np.nan
    sharpe=r.mean()/r.std(ddof=1)*np.sqrt(252) if r.std(ddof=1)>0 else np.nan
    st.subheader("Risk indicators")
    a,b,c,d=st.columns(4)
    a.metric("Realised volatility (annualised)",fmt(volatility)+"%")
    b.metric("Maximum drawdown",fmt(mdd)+"%")
    b.caption(f"Trough date: {mdd_date}")
    c.metric("Historical VaR 95% (1D)",fmt(var)+"%")
    d.metric("Sharpe (rf = 0%)",fmt(sharpe))
    source(series,"Yahoo Finance via yfinance; daily adjusted prices, 252 trading days/year")

def bonds():
    st.header("Government Bonds")
    countries=st.sidebar.multiselect(
        "10Y government yields — countries",list(COUNTRY_10Y),
        default=["US","Germany","France"],key="bond_countries")
    window=sidebar_window("bonds")
    selected_country=st.sidebar.selectbox("Bond history — country",countries,key="bond_history_country") if countries else None
    if not countries:
        st.info("Select at least one country in the sidebar.")
        return

    history={country:fred(COUNTRY_10Y[country]) for country in countries}
    rows=[]
    for country,series in history.items():
        rows.append({"Country":country,"Yield (%)":fmt(series.iloc[-1]) if not series.empty else "N/A",
                     "Observed at":observed_at(series.index,"daily" if country=="US" else "monthly") if not series.empty else "Unavailable",
                     "Frequency":"Daily" if country=="US" else "Monthly"})
    st.subheader("Latest 10Y government yields")
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

    st.subheader("Government yield comparison — 10Y")
    fig=go.Figure()
    for country,series in history.items():
        # Use monthly averages for US too in the cross-country comparison.
        # The standalone US chart below retains every available daily observation.
        comparable=series.resample("MS").mean() if country=="US" else series
        selected=cut(comparable,window)
        if not selected.empty:
            fig.add_trace(go.Scatter(x=selected.index,y=selected.values,mode="lines+markers",name=country))
    if fig.data:
        fig.update_layout(template="plotly_white",height=430,yaxis_title="Yield (%)",
                          xaxis_title="Date",hovermode="x unified",
                          margin=dict(l=12,r=12,t=20,b=12))
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning("FRED data unavailable for the selected countries.")
    st.caption("Source: FRED — US DGS10 monthly averages; other countries OECD monthly 10Y yields. Definitions may differ. US daily observations are available in the country history below.")

    st.subheader("US Treasury Yield Curve")
    tenor_years={"3M":0.25,"2Y":2.0,"5Y":5.0,"10Y":10.0,"30Y":30.0}
    curves={tenor:fred(series_id) for tenor,series_id in US_CURVE.items()}
    available={tenor:series for tenor,series in curves.items() if not series.empty}
    if len(available)>=2:
        # All tenors must refer to the same observation date: never mix dates.
        aligned=pd.concat(available,axis=1,join="inner").dropna()
        if not aligned.empty:
            last_date=aligned.index[-1]
            labels=[t for t in US_CURVE if t in aligned.columns]
            fig=go.Figure(go.Scatter(
                x=[tenor_years[t] for t in labels],y=[float(aligned.loc[last_date,t]) for t in labels],
                mode="lines+markers+text",text=labels,textposition="top center",
                line=dict(color="#2463ac",width=3),marker=dict(size=9)))
            fig.update_layout(template="plotly_white",height=380,xaxis_title="Maturity (years)",
                              yaxis_title="Yield (%)",margin=dict(l=12,r=12,t=20,b=12))
            st.plotly_chart(fig,use_container_width=True)
            st.caption(f"Source: FRED — US Treasury constant-maturity yields (DGS3MO, DGS2, DGS5, DGS10, DGS30). Common observation date: {last_date.date()}.")
        else:
            st.warning("No common observation date available across US Treasury maturities.")
    else:
        st.warning("Insufficient FRED series available to display the US Treasury yield curve.")

    st.subheader("Selected government bond — 10Y history")
    selected=history[selected_country]
    if not selected.empty:
        selected_cut=cut(selected,window)
        if len(selected_cut)>0:
            fig=go.Figure(go.Scatter(x=selected_cut.index,y=selected_cut.values,mode="lines+markers" if selected_country!="US" else "lines",name=selected_country,line=dict(color="#2463ac",width=2.4)))
            fig.update_layout(template="plotly_white",height=390,yaxis_title="Yield (%)",xaxis_title="Date",margin=dict(l=12,r=12,t=20,b=12))
            st.plotly_chart(fig,use_container_width=True)
        st.caption(f"Source: FRED — {COUNTRY_10Y[selected_country]} | Last observation: {observed_at(selected.index,'daily' if selected_country=='US' else 'monthly')}")
    else:
        st.warning("No observations available for this country.")

def commodities():
    window=sidebar_window("commodities")
    st.header("Commodities")
    st.subheader("Latest prices")
    rows=[]
    for name,symbol in COMMODITIES.items():
        df=prices(symbol)
        rows.append({"Asset":name,"Last price":(fmt(df.Close.iloc[-1])+" "+COMMODITY_UNITS[name][0]) if not df.empty else "N/A","Unit":COMMODITY_UNITS[name][1],"Observed at":observed_at(df.index) if not df.empty else "Unavailable"})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    name=st.sidebar.selectbox("Commodity",list(COMMODITIES),key="commodity_choice")
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

def currencies():
    window=sidebar_window("currencies")
    st.header("Currencies")
    st.subheader("Spot matrix")
    # Build a consistent single-date matrix from common USD legs.
    latest={"USD":1.0};observations=[]
    for ccy in FX_CODES:
        if ccy=="USD":continue
        s=fx_pair("USD",ccy)
        if not s.empty:latest[ccy]=float(s.iloc[-1]);observations.append(s.index[-1])
    if len(latest)<2:st.warning("FX data unavailable.");return
    matrix=pd.DataFrame(index=FX_CODES,columns=FX_CODES,dtype=float)
    for base in FX_CODES:
        for quote in FX_CODES:
            if base in latest and quote in latest:matrix.loc[base,quote]=latest[quote]/latest[base]
    st.caption("Source: Yahoo Finance via yfinance | Cross-rates calculated from latest available USD legs; timestamps may differ")
    if "fx_base" not in st.session_state:st.session_state.fx_base="EUR"
    if "fx_quote" not in st.session_state:st.session_state.fx_quote="USD"
    # Buttons are genuine Streamlit widgets: clicking a rate selects the pair.
    headers=st.columns([0.75]+[1]*len(FX_CODES),gap="small")
    for j,code in enumerate(FX_CODES):headers[j+1].markdown(f"**{code}**")
    for base_code in FX_CODES:
        cells=st.columns([0.75]+[1]*len(FX_CODES),gap="small")
        cells[0].markdown(f"**{base_code}**")
        for j,quote_code in enumerate(FX_CODES):
            rate=matrix.loc[base_code,quote_code]
            label=f"{rate:.4f}" if pd.notna(rate) else "—"
            active=(base_code==st.session_state.fx_base and quote_code==st.session_state.fx_quote)
            if cells[j+1].button(label,key=f"fx_{base_code}_{quote_code}",disabled=(base_code==quote_code or pd.isna(rate)),type="primary" if active else "secondary",use_container_width=True):
                st.session_state.fx_base=base_code
                st.session_state.fx_quote=quote_code
                st.rerun()
    base=st.session_state.fx_base
    quote=st.session_state.fx_quote
    st.subheader(f"{base}/{quote}")
    if base==quote:st.info("Choose two different currencies.");return
    s=fx_pair(base,quote)
    if s.empty:st.warning("FX history unavailable.");return
    chart(cut(s,window),ytitle=f"{quote} per 1 {base}")
    source(s,"Yahoo Finance via yfinance")

@st.cache_data(persist="disk",show_spinner=False)
def stock_info(ticker):
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}

def single_stock():
    window=sidebar_window("single")
    st.header("Single Stock Analysis")
    ticker=st.sidebar.text_input("Ticker",value="MC.PA").strip().upper()
    if not ticker:return
    df=prices(ticker)
    if df.empty:st.warning("Ticker not found or price history unavailable.");return
    info=stock_info(ticker)
    currency=info.get("currency") or "Currency N/A"
    st.subheader(info.get("longName") or ticker)
    a,b,c,d=st.columns(4)
    a.metric("Last adjusted close",f"{fmt(df.Close.iloc[-1])} {currency}")
    b.metric("Market cap",compact(info.get("marketCap"),currency))
    c.metric("Sector",str(info.get("sector") or "N/A"))
    d.metric("Exchange",str(info.get("fullExchangeName") or info.get("exchange") or "N/A"))
    chart(cut(df.Close,window),ytitle=f"Adjusted close ({currency})")
    st.subheader("Financial snapshot — reported periods")
    fields={"Trailing P/E":("trailingPE","TTM"),"Forward P/E":("forwardPE","Forward estimate; provider horizon"),"EV / EBITDA":("enterpriseToEbitda","Provider-reported; period not guaranteed"),"Operating margin":("operatingMargins","TTM, where available"),"Revenue growth":("revenueGrowth","Provider-reported; period may vary"),"ROE":("returnOnEquity","Provider-reported; period may vary"),"Debt / equity":("debtToEquity","Latest available balance sheet") }
    rows=[]
    for label,(key,horizon) in fields.items():
        v=info.get(key)
        if isinstance(v,(int,float)) and key in ("operatingMargins","revenueGrowth","returnOnEquity"):v=f"{v*100:.2f}%"
        elif isinstance(v,(int,float)):v=fmt(v)
        rows.append({"Metric":label,"Value":v if v is not None else "N/A","Period / definition":horizon})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.subheader("Relative performance")
    comparison=st.sidebar.radio("Compare against",["Equity index","Another stock"],horizontal=False)
    if comparison=="Equity index":
        name=st.sidebar.selectbox("Benchmark",list(INDICES));symbol=INDICES[name]
    else:
        symbol=st.sidebar.text_input("Comparison stock ticker",value="OR.PA").strip().upper();name=symbol
    other=prices(symbol) if symbol else pd.DataFrame()
    if other.empty:st.warning("Comparison history unavailable.")
    else:
        # Base 100 in each asset's own trading currency; not currency-hedged.
        joined=pd.concat([cut(df.Close,window).rename(ticker),cut(other.Close,window).rename(name)],axis=1).dropna()
        if len(joined)>1:
            rebased=joined/joined.iloc[0]*100
            fig=go.Figure()
            for label,color in [(ticker,"#2463ac"),(name,"#72a8dc")]:fig.add_trace(go.Scatter(x=rebased.index,y=rebased[label],name=label,mode="lines",line=dict(color=color,width=2)))
            fig.update_layout(template="plotly_white",height=390,yaxis_title="Rebased price (100 = start)",hovermode="x unified")
            st.plotly_chart(fig,use_container_width=True)
        else:st.warning("Not enough overlapping observations.")
    source(df.Close,"Yahoo Finance via yfinance; fundamental data from third-party vendor")

with st.sidebar:
    st.markdown("## MARKET DASHBOARD")
    st.markdown("Sacha Olry de Labry")
    page=st.radio("Explore",["Equities","Bonds","Commodities","Currencies","Single Stock Analysis"])
    st.divider()
    if st.button("Refresh market data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

{"Equities":equities,"Bonds":bonds,"Commodities":commodities,"Currencies":currencies,"Single Stock Analysis":single_stock}[page]()
