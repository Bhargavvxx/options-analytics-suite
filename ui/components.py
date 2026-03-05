"""
Shared sidebar controls and reusable UI components.

Every page imports ``render_sidebar()`` to get consistent parameter
inputs.  This avoids duplicated widget logic across tabs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import streamlit as st


@dataclass
class SidebarParams:
    """Parameters collected from the sidebar."""
    ticker: str
    spot: float
    strike: float
    expiry_years: float
    risk_free_rate: float
    volatility: float
    dividend_yield: float
    option_type: str
    history_period: str


def render_sidebar() -> SidebarParams:
    """Draw the sidebar and return user-selected parameters."""
    st.sidebar.header("📊 Parameters")

    ticker = st.sidebar.text_input("Ticker", value="AAPL").upper()

    st.sidebar.subheader("Pricing Inputs")
    spot = st.sidebar.number_input("Spot Price (S)", value=150.0, min_value=0.01, step=1.0)
    strike = st.sidebar.number_input("Strike Price (K)", value=150.0, min_value=0.01, step=1.0)
    expiry = st.sidebar.slider("Time to Expiry (years)", 0.01, 3.0, 0.25, step=0.01)
    r = st.sidebar.slider("Risk-Free Rate", 0.0, 0.15, 0.05, step=0.005, format="%.3f")
    sigma = st.sidebar.slider("Volatility (σ)", 0.01, 1.50, 0.20, step=0.01, format="%.2f")
    q = st.sidebar.slider("Dividend Yield (q)", 0.0, 0.10, 0.0, step=0.005, format="%.3f")
    opt_type = st.sidebar.selectbox("Option Type", ["call", "put"])
    period = st.sidebar.selectbox("History Period", ["6mo", "1y", "2y", "5y"], index=1)

    return SidebarParams(
        ticker=ticker,
        spot=spot,
        strike=strike,
        expiry_years=expiry,
        risk_free_rate=r,
        volatility=sigma,
        dividend_yield=q,
        option_type=opt_type,
        history_period=period,
    )


def metric_row(cols: int, labels: list, values: list, deltas: list | None = None):
    """Render a row of ``st.metric`` widgets."""
    columns = st.columns(cols)
    for i, col in enumerate(columns):
        if i < len(labels):
            d = deltas[i] if deltas and i < len(deltas) else None
            col.metric(labels[i], values[i], delta=d)
