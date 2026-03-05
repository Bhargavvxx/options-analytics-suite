"""
Option Analytics Suite — Main Streamlit Entry Point.

This is a **thin** orchestrator that:
1. Configures logging.
2. Renders the sidebar.
3. Dispatches to the selected page module.

All business logic lives in the ``analytics/``, ``strategies/``,
``backtesting/``, ``ml/``, ``sentiment/``, and ``visualization/`` packages.
"""
from __future__ import annotations

import streamlit as st

from config.logging_config import setup_logging
from ui.components import render_sidebar

# ---------- bootstrap ----------
setup_logging()

st.set_page_config(
    page_title="Option Analytics Suite",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 Option Analytics Suite")

# ---------- sidebar ----------
params = render_sidebar()

# ---------- page dispatch ----------
PAGES = {
    "Pricing & Greeks": "ui.pages.pricing",
    "Volatility Analytics": "ui.pages.volatility",
    "Strategy Analysis": "ui.pages.strategies",
    "Backtesting": "ui.pages.backtesting",
    "ML Predictions": "ui.pages.ml",
    "Sentiment": "ui.pages.sentiment",
    "Educational": "ui.pages.educational",
}

page = st.sidebar.radio("Navigate", list(PAGES.keys()))

# Dynamic import to keep startup fast
import importlib
mod = importlib.import_module(PAGES[page])
mod.render(params)
