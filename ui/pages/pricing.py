"""Pricing & Greeks page."""
from __future__ import annotations

import streamlit as st

from analytics.pricing import OptionType, black_scholes_price
from analytics.greeks import analytical_greeks, finite_difference_greeks
from visualization.pricing_charts import plot_option_price_surface, plot_greeks_dashboard
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Option Pricing & Greeks")

    opt = OptionType.CALL if p.option_type == "call" else OptionType.PUT
    price = black_scholes_price(p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, opt, p.dividend_yield)
    greeks = analytical_greeks(p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, opt, p.dividend_yield)
    fd = finite_difference_greeks(p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, opt, p.dividend_yield)

    # Price metric
    st.subheader(f"{p.option_type.title()} Price")
    st.metric("Black-Scholes Price", f"${price:.4f}")

    # Greeks
    st.subheader("Analytical Greeks")
    metric_row(5,
        ["Delta", "Gamma", "Theta", "Vega", "Rho"],
        [f"{greeks.delta:.4f}", f"{greeks.gamma:.6f}", f"{greeks.theta:.4f}", f"{greeks.vega:.4f}", f"{greeks.rho:.4f}"],
    )

    with st.expander("Finite-Difference Validation"):
        metric_row(5,
            ["FD Delta", "FD Gamma", "FD Theta", "FD Vega", "FD Rho"],
            [f"{fd.delta:.4f}", f"{fd.gamma:.6f}", f"{fd.theta:.4f}", f"{fd.vega:.4f}", f"{fd.rho:.4f}"],
        )

    # Charts
    st.subheader("Price Surface")
    fig_surface = plot_option_price_surface(p.strike, p.expiry_years, p.risk_free_rate, p.volatility, p.option_type, p.dividend_yield)
    st.plotly_chart(fig_surface, use_container_width=True)

    st.subheader("Greeks vs Spot")
    fig_greeks = plot_greeks_dashboard(p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, p.option_type, p.dividend_yield)
    st.plotly_chart(fig_greeks, use_container_width=True)
