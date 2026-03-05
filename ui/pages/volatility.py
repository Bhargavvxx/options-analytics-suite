"""Volatility Analytics page."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from data.market_data import get_default_provider
from analytics.volatility import (
    historical_volatility,
    ewma_volatility,
    garch_volatility,
    realised_vol_cone,
    detect_vol_regime,
)
from analytics.iv_surface import simulated_iv_surface
from visualization.vol_charts import plot_volatility_cone, plot_iv_surface_3d
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Volatility Analytics")

    provider = get_default_provider()
    try:
        prices, _ = provider.fetch_history(p.ticker, period=p.history_period)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return

    if prices.empty:
        st.warning("No price data available.")
        return

    # Realised vol
    hv_series = historical_volatility(prices["Close"], window=20)
    latest_hv = hv_series.iloc[-1] if len(hv_series) > 0 else 0.0

    # EWMA
    ewma = ewma_volatility(prices["Close"])

    # GARCH
    garch = garch_volatility(prices["Close"])

    # Regime
    regime = detect_vol_regime(prices["Close"])

    st.subheader("Current Volatility Estimates")
    metric_row(4,
        ["HV (20d)", "EWMA", "GARCH", "Regime"],
        [f"{latest_hv:.1%}", f"{ewma.value:.1%}", f"{garch.value:.1%}", regime.value],
    )

    # Vol cone
    st.subheader("Volatility Cone")
    try:
        cone = realised_vol_cone(prices["Close"])
        fig_cone = plot_volatility_cone(cone)
        st.plotly_chart(fig_cone, use_container_width=True)
    except Exception as e:
        st.warning(f"Cannot build vol cone: {e}")

    # HV time series
    st.subheader("Historical Volatility Time Series")
    hv_df = pd.DataFrame({"HV_20d": hv_series}).dropna()
    st.line_chart(hv_df)

    # IV Surface (simulated for demonstration)
    st.subheader("IV Surface (Simulated)")
    st.caption("⚠️ This surface is generated from a parametric model, not live market data.")
    surface = simulated_iv_surface(p.spot, p.volatility)
    import numpy as np
    fig_iv = plot_iv_surface_3d(
        np.array(surface.strikes),
        np.array(surface.expiries),
        np.array(surface.iv_matrix),
    )
    st.plotly_chart(fig_iv, use_container_width=True)
