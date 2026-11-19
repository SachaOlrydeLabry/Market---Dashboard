# UBS Market Dashboard — corrected Streamlit navigation

Streamlit automatically creates navigation when a folder is named `pages`.
This project uses `asset_views` instead, so only the custom sidebar is shown.

## Install on Windows

1. Stop Streamlit with Ctrl+C.
2. In your existing `market_dashboard_sacha` folder, **DELETE or rename the OLD `pages` folder**. This is essential: leaving it there will keep the extra Streamlit menu.
3. Copy `app.py`, `config.py`, `data.py`, `analytics.py`, `ui.py`, `ui_theme.py`, and the entire new `asset_views` folder from this ZIP into `market_dashboard_sacha`.
4. Keep your existing `pyproject.toml`, `uv.lock`, and `.venv`.
5. Run `uv run streamlit run app.py`.

The five dashboard sections still use the existing custom sidebar.
Syntax and local import references have been checked, but live Streamlit execution with market data has not been tested.
