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
from data import prices, prices_in_usd, stock_financials, stock_info
from analytics import cut, fin_value, valid_number
from ui import chart, compact, display_date, financial_comparison_table, financial_table, format_number, format_time_axis, plot_layout, remembered_widget, sidebar_window, source

# SINGLE STOCK — Combine prices, annual statements and comparison-table helpers.
# single_stock() — Read ticker and fiscal selections, derive ratios and render company comparisons.
def single_stock():
    window = sidebar_window("single")
    st.header("Single Stock Analysis")
    ticker = remembered_widget("text_input", "Ticker", key="stock_ticker", default="",
                                     placeholder="e.g. AAPL, MC.PA").strip().upper()
    if not ticker:
        st.info("Enter a stock ticker in the sidebar to start the analysis.")
        return
    df = prices(ticker)
    if df.empty:
        st.error("No historical prices were retrieved for this ticker.")
        return
    info = stock_info(ticker)
    currency = info.get("currency") or ""
    st.subheader(info.get("longName") or ticker)
    overview = [("Last adjusted close", format_number(df.Close.iloc[-1], f" {currency}")),
                ("Market cap", compact(info["marketCap"], currency) if valid_number(info.get("marketCap")) else None),
                ("Sector", info.get("sector")),
                ("Exchange", info.get("fullExchangeName") or info.get("exchange"))]
    overview = [(label, value) for label, value in overview if value]
    if overview:
        for col, (label, value) in zip(st.columns(len(overview)), overview):
            col.metric(label, value)
    chart(cut(df.Close, window), ytitle=f"Adjusted close ({currency})")
    # Read annual income statement, balance sheet, and cash flow statement.
    inc, bal, cf = stock_financials(ticker)
    # Fiscal statements are annual. Do not relabel Yahoo's TTM/forward multiples
    # as historical fiscal-year metrics: their underlying periods differ.
    if inc.empty or not any(pd.notna(pd.to_datetime(c, errors="coerce")) for c in inc.columns):
        st.warning("Annual financial statements unavailable; historical ratios cannot be verified.")
        fiscal_dates = []
    else:
        fiscal_dates = [pd.Timestamp(c) for c in inc.columns if pd.notna(pd.to_datetime(c, errors="coerce"))]
        fiscal_dates = sorted(set(fiscal_dates), reverse=True)

    st.subheader("Financial statement horizons")
    if fiscal_dates:
        fy_date = remembered_widget(
            "selectbox", "Fiscal year end", key="stock_fiscal_year",
            options=fiscal_dates, default=fiscal_dates[0],
            format_func=lambda d: f"FY ending {display_date(d)}")
        st.write("Historical financial metrics use the selected fiscal year. "
                 "TTM and forward vendor estimates remain current and are labelled separately.")

        def at_date(table, names, dt):
            if table is None or table.empty or dt not in table.columns:
                return np.nan
            return fin_value(table, names, table.columns.get_loc(dt))

        def period_label(dt):
            return f"FY ended {display_date(dt)}"

        revenue_names = ["Total Revenue", "Operating Revenue"]
        rev = at_date(inc, revenue_names, fy_date)
        op_income = at_date(inc, ["Operating Income", "EBIT"], fy_date)
        ebitda = at_date(inc, ["EBITDA", "Normalized EBITDA"], fy_date)
        fcf = at_date(cf, ["Free Cash Flow"], fy_date)
        if not valid_number(fcf):
            ocf = at_date(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"], fy_date)
            capex = at_date(cf, ["Capital Expenditure"], fy_date)
            if valid_number(ocf) and valid_number(capex) and capex <= 0:
                fcf = ocf + capex

        growth = []
        if valid_number(rev):
            growth.append(("Revenue", compact(rev, currency), period_label(fy_date)))
        prev_date = next((d for d in fiscal_dates if 330 <= (fy_date - d).days <= 400), None)
        if prev_date is not None:
            prev_rev = at_date(inc, revenue_names, prev_date)
            if valid_number(rev) and valid_number(prev_rev) and prev_rev > 0:
                growth.append(("Revenue growth YoY", format_number((rev / prev_rev - 1) * 100, "%"),
                               f"{display_date(prev_date)} → {display_date(fy_date)}"))
        if valid_number(fcf):
            growth.append(("Free cash flow", compact(fcf, currency), period_label(fy_date)))
        # Comparisons are calculated from the same named line items on adjacent fiscal dates.
        def previous(table, names):
            return at_date(table, names, prev_date) if prev_date is not None else np.nan
        def fcf_at(dt):
            value=at_date(cf,["Free Cash Flow"],dt)
            if valid_number(value):return value
            ocf=at_date(cf,["Operating Cash Flow","Total Cash From Operating Activities"],dt)
            capex=at_date(cf,["Capital Expenditure"],dt)
            return ocf+capex if valid_number(ocf) and valid_number(capex) and capex<=0 else np.nan
        prev_fcf=fcf_at(prev_date) if prev_date is not None else np.nan
        eps_names=["Diluted EPS", "Diluted EPS Continuous Operations"]
        eps=at_date(inc,eps_names,fy_date)
        prev_eps=previous(inc,eps_names)
        entries=[("Revenue",rev,previous(inc,revenue_names),fy_date,prev_date,"amt:"+currency),
                 ("Diluted EPS",eps,prev_eps,fy_date,prev_date," "+currency),
                 ("Free cash flow",fcf,prev_fcf,fy_date,prev_date,"amt:"+currency)]
        # Compare revenue, diluted EPS, and cash flow with the previous fiscal year.
        financial_comparison_table("Growth — fiscal comparison",entries)
        profit = []
        if valid_number(rev) and rev > 0 and valid_number(op_income):
            profit.append(("Operating margin", format_number(op_income / rev * 100, "%"), period_label(fy_date)))
        if valid_number(rev) and rev > 0 and valid_number(fcf):
            profit.append(("FCF margin", format_number(fcf / rev * 100, "%"), period_label(fy_date)))
        prev_rev=previous(inc,revenue_names)
        prev_op=previous(inc,["Operating Income","EBIT"])
        # Compare operating and free cash flow margins across fiscal years.
        financial_comparison_table("Profitability — fiscal comparison",[
            ("Operating margin",op_income/rev*100 if valid_number(op_income) and valid_number(rev) and rev>0 else np.nan,
             prev_op/prev_rev*100 if valid_number(prev_op) and valid_number(prev_rev) and prev_rev>0 else np.nan,
             fy_date,prev_date,"%"),
            ("FCF margin",fcf/rev*100 if valid_number(fcf) and valid_number(rev) and rev>0 else np.nan,
             prev_fcf/prev_rev*100 if valid_number(prev_fcf) and valid_number(prev_rev) and prev_rev>0 else np.nan,
             fy_date,prev_date,"%")])

        risk = []
        total_debt = at_date(bal, ["Total Debt"], fy_date)
        cash = at_date(bal, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"], fy_date)
        net_debt = total_debt - cash if valid_number(total_debt) and valid_number(cash) else np.nan
        if valid_number(net_debt):
            risk.append(("Net debt", compact(net_debt, currency), f"Balance sheet {display_date(fy_date)}"))
        if valid_number(net_debt) and valid_number(ebitda) and ebitda > 0:
            risk.append(("Net debt / EBITDA", format_number(net_debt / ebitda, "x"),
                         f"Debt at {display_date(fy_date)} / EBITDA FY ended {display_date(fy_date)}"))
        prev_debt=previous(bal,["Total Debt"])
        prev_cash=previous(bal,["Cash Cash Equivalents And Short Term Investments","Cash And Cash Equivalents"])
        prev_net=prev_debt-prev_cash if valid_number(prev_debt) and valid_number(prev_cash) else np.nan
        prev_ebitda=previous(inc,["EBITDA","Normalized EBITDA"])
        # Compare net debt and leverage using aligned fiscal dates.
        financial_comparison_table("Financial Risk — fiscal comparison",[
            ("Net debt",net_debt,prev_net,fy_date,prev_date,"amt:"+currency),
            ("Net debt / EBITDA",net_debt/ebitda if valid_number(net_debt) and valid_number(ebitda) and ebitda>0 else np.nan,
             prev_net/prev_ebitda if valid_number(prev_net) and valid_number(prev_ebitda) and prev_ebitda>0 else np.nan,
             fy_date,prev_date,"x")])

    # Provider's TTM and forward metrics cannot be assigned to a selected FY.
    estimates = []
    for key, label, suffix, period in [
        ("trailingEps", "EPS (TTM)", f" {currency}", "TTM · Yahoo Finance"),
        ("trailingPE", "Trailing P/E", "x", "TTM · Yahoo Finance")]:
        val = info.get(key)
        if valid_number(val) and (key.endswith("Eps") or val > 0):
            estimates.append((label, format_number(val, suffix), period))
    financial_table(estimates, "Current market multiples & estimates — independent of fiscal selection")

    # A current-price/historical-FCF yield is a mixed-date metric, not a FY yield.
    if fiscal_dates:
        market_cap = info.get("marketCap")
        if valid_number(fcf) and valid_number(market_cap) and market_cap > 0:
            financial_table([("Historical FCF / current market cap",
                              format_number(fcf / market_cap * 100, "%"),
                              f"FCF FY ended {display_date(fy_date)} / current market cap")],
                            "Valuation — mixed-date reference")
    # Rebase both assets to 100; convert to USD if currencies differ.
    st.subheader("Relative performance")
    comparison = remembered_widget("radio", "Compare against", key="stock_compare_type",
                                   options=["Equity index", "Another stock"], default="Equity index")
    if comparison == "Equity index":
        name = remembered_widget("selectbox", "Benchmark", options=[None,*INDICES],
                                         key="stock_benchmark", format_func=lambda x: x or "Select a benchmark…")
        symbol = INDICES[name] if name else None
    else:
        symbol = remembered_widget("text_input", "Comparison stock ticker", key="stock_comparison_ticker",
                                                   default="", placeholder="e.g. MSFT").strip().upper()
        name = symbol
    if not symbol:
        st.info("Select a benchmark or enter a comparison ticker in the sidebar.")
        source(df.Close, "Yahoo Finance via yfinance; fundamental data from third-party vendor")
        return
    other = prices(symbol)
    if not other.empty:
        other_ccy = INDEX_CURRENCY[name] if comparison == "Equity index" else (stock_info(symbol).get("currency") or "")
        if not currency or not other_ccy:
            st.warning("Currency metadata unavailable; comparison withheld.")
        else:
            target_ccy = currency if currency == other_ccy else "USD"
            lhs = df.Close if target_ccy == currency else prices_in_usd(df.Close, currency)
            rhs = other.Close if target_ccy == other_ccy else prices_in_usd(other.Close, other_ccy)
            joined = pd.concat([cut(lhs, window).rename(ticker),
                                cut(rhs, window).rename(name)], axis=1).dropna()
            if len(joined)>1 and (joined.iloc[0]>0).all():
                rebased = joined / joined.iloc[0] * 100
                fig = go.Figure()
                for label, color in [(ticker,"#2463ac"),(name,"#72a8dc")]:
                    fig.add_trace(go.Scatter(x=rebased.index,y=rebased[label],name=label,
                                             mode="lines",line=dict(color=color,width=2)))
                plot_layout(fig,ytitle=f"Adjusted price, base 100 ({target_ccy})",
                            title=f"Relative performance — {ticker} vs {name}",hover=True)
                st.plotly_chart(format_time_axis(fig),use_container_width=True)
                if comparison == "Equity index":
                    st.caption("Price-index benchmark: dividends may be excluded. This is NOT a verified total-return comparison.")
                else:
                    st.caption("Yahoo adjusted closes generally reflect dividends/splits for stocks; check corporate-action data for full total-return validation.")
                st.caption(f"Currency: {target_ccy}. Different native currencies are converted to USD using historical daily FX.")
            else:
                st.warning("Insufficient overlapping observations for comparison.")
    source(df.Close, "Yahoo Finance via yfinance; fundamental data from third-party vendor")

