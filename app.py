"""UBS Market Dashboard — launch with: uv run streamlit run app.py"""
import streamlit as st
from ui_theme import apply_styles
from asset_views.equities import equities
from asset_views.bonds import bonds
from asset_views.commodities import commodities
from asset_views.currencies import currencies
from asset_views.single_stock import single_stock

# Streamlit must configure the page before rendering any widgets.
st.set_page_config(page_title="Market Dashboard", page_icon="📊", layout="wide")
apply_styles()

# The sidebar controls navigation and manually clears cached market data.
with st.sidebar:
    st.markdown("## MARKET DASHBOARD")
    st.markdown("Sacha Olry de Labry")
    NAV = {"📈  Stocks": "Equities", "📉  Bonds": "Bonds", "⚖️  Commodities": "Commodities", "💱  Currencies": "Currencies", "🔎  Single Stock": "Single Stock Analysis"}
    page = NAV[st.radio("Explore", list(NAV), label_visibility="collapsed", key="main_navigation")]
    st.divider()
    if st.button("↻  Refresh market data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Only the selected asset page is rendered on each Streamlit rerun.
{"Equities": equities, "Bonds": bonds, "Commodities": commodities, "Currencies": currencies, "Single Stock Analysis": single_stock}[page]()
