"""Streamlit visual theme. Applied once from app.py."""
import streamlit as st

def apply_styles():
    st.markdown("""<style>
    .stApp {background:#fff;color:#10213a}
    [data-testid="stSidebar"] {background:#0b1930}
    [data-testid="stSidebar"] * {color:#f2f6fd!important}
    h1,h2,h3 {color:#0b1930!important}
    [data-testid="stMetric"] {background:#eef3f9;border:1px solid #d9e5f2;border-radius:10px;padding:12px}
    [data-testid="stMetricValue"] {font-size:1.65rem!important;overflow-wrap:anywhere}
    [data-testid="stMetricLabel"] {font-size:.84rem!important}
    [data-testid="stSidebar"] [data-baseweb="select"]>div {background:#fff!important}
    [data-testid="stSidebar"] [data-baseweb="select"]>div * {color:#10213a!important}
    [data-testid="stSidebar"] input {color:#10213a!important}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {color:#f2f6fd!important}
    /* High-contrast refresh button in every state */
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
     background:#e7f1ff!important;border:1px solid #91b9e8!important;color:#0b1930!important;
     font-weight:750!important;min-height:43px;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] * {color:#0b1930!important}
    [data-testid="stSidebar"] .stButton button[kind="primary"]:hover {background:#c8e2ff!important}
    /* Compact navigation, scoped to the main page selector only. */
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] {gap:2px!important}
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] label {
     padding:5px 9px!important;min-height:32px!important;margin:1px 0!important;
     border:0!important;border-radius:5px!important;cursor:pointer;
     background:transparent!important;
    }
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] label:has(input:checked) {
     background:#27374e!important;font-weight:600!important;
    }
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] label:hover {
     background:#1b2d47!important;
    }
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
     font-size:.88rem!important;line-height:1.25!important;
    }
    [data-testid="stSidebar"] .st-key-main_navigation div[role="radiogroup"] label > div:first-child {
     display:none!important;
    }
    /* Captions are deliberately readable, not pale grey */
    .stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
     color:#334a67!important;font-size:.88rem!important;
    }
    /* Four aligned risk cards; all drawdown details stay inside their card. */
    .st-key-risk_indicators [data-testid="stMetric"] {min-height:196px;box-sizing:border-box;}
    .mdd-panel {background:#eef3f9;border:1px solid #d9e5f2;border-radius:10px;
      padding:12px;min-height:196px;box-sizing:border-box;color:#10213a;}
    .mdd-label {font-size:.84rem;margin-bottom:7px;}
    .mdd-value {font-size:1.65rem;line-height:1.35;margin-bottom:14px;}
    .mdd-detail {font-size:.79rem;line-height:1.55;white-space:nowrap;}
    .mdd-detail strong {font-weight:650;}
    </style>""", unsafe_allow_html=True)
