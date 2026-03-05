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
        prices, _ = provider.get_stock_data(p.ticker, period=p.history_period)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return

    if prices.empty:
        st.warning("No price data available.")
        return

    import numpy as np
    log_returns = np.log(prices["Close"] / prices["Close"].shift(1)).dropna()

    # Realised vol
    hv_series = historical_volatility(log_returns, window=20)
    latest_hv = hv_series.dropna().iloc[-1] if len(hv_series.dropna()) > 0 else 0.0

    # EWMA
    ewma = ewma_volatility(log_returns)

    # GARCH
    garch = garch_volatility(log_returns)

    # Regime
    hv_full = hv_series.dropna()
    regime = detect_vol_regime(latest_hv, hv_full)

    st.subheader("Current Volatility Estimates")
    metric_row(4,
        ["HV (20d)", "EWMA", "GARCH", "Regime"],
        [f"{latest_hv:.1%}", f"{ewma.value:.1%}", f"{garch.value:.1%}", regime.value],
    )

    # Vol cone
    st.subheader("Volatility Cone")
    try:
        cone = realised_vol_cone(log_returns)
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
    if surface.strike_grid is not None and surface.time_grid is not None and surface.iv_grid is not None:
        fig_iv = plot_iv_surface_3d(
            surface.strike_grid,
            surface.time_grid,
            surface.iv_grid,
        )
        st.plotly_chart(fig_iv, use_container_width=True)
    else:
        st.warning("Could not generate IV surface.")
