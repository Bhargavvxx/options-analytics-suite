"""Educational page — Black-Scholes intuition builder."""
from __future__ import annotations

import streamlit as st
import numpy as np

from analytics.pricing import OptionType, black_scholes_price
from analytics.greeks import analytical_greeks
from ui.components import SidebarParams


def render(p: SidebarParams) -> None:
    st.header("📚 Educational: Black-Scholes Intuition")

    st.markdown("""
    Explore how each input affects the option price.
    Use the sliders below to vary **one parameter at a time** while holding others fixed.
    """)

    opt = OptionType.CALL if p.option_type == "call" else OptionType.PUT

    tab1, tab2, tab3 = st.tabs(["Price vs Spot", "Price vs Vol", "Price vs Time"])

    with tab1:
        spots = np.linspace(p.strike * 0.5, p.strike * 1.5, 100)
        prices = [black_scholes_price(s, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, opt, p.dividend_yield, validate=False) for s in spots]
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spots, y=prices, mode="lines", name="Price"))
        fig.add_vline(x=p.spot, line_dash="dash", annotation_text="Current Spot")
        fig.add_vline(x=p.strike, line_dash="dot", line_color="red", annotation_text="Strike")
        fig.update_layout(title=f"{p.option_type.title()} Price vs Spot", xaxis_title="Spot", yaxis_title="Price")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Takeaway**: Delta measures this slope. Deep ITM → delta ≈ ±1; deep OTM → delta ≈ 0.")

    with tab2:
        vols = np.linspace(0.01, 1.0, 100)
        prices_v = [black_scholes_price(p.spot, p.strike, p.expiry_years, p.risk_free_rate, v, opt, p.dividend_yield, validate=False) for v in vols]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=vols, y=prices_v, mode="lines", name="Price"))
        fig2.add_vline(x=p.volatility, line_dash="dash", annotation_text="Current σ")
        fig2.update_layout(title=f"{p.option_type.title()} Price vs Volatility", xaxis_title="σ", yaxis_title="Price")
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("**Takeaway**: Vega measures this slope. Options gain value with higher uncertainty.")

    with tab3:
        times = np.linspace(0.01, 2.0, 100)
        prices_t = [black_scholes_price(p.spot, p.strike, t, p.risk_free_rate, p.volatility, opt, p.dividend_yield, validate=False) for t in times]
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=times, y=prices_t, mode="lines", name="Price"))
        fig3.add_vline(x=p.expiry_years, line_dash="dash", annotation_text="Current T")
        fig3.update_layout(title=f"{p.option_type.title()} Price vs Time to Expiry", xaxis_title="T (years)", yaxis_title="Price")
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("**Takeaway**: Theta measures time decay — options lose value as expiry approaches.")
