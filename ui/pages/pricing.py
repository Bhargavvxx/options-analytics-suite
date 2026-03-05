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

    # ---- American pricing (Track 2) ------------------------------------
    st.subheader("American Option Pricing (Binomial Tree)")
    from analytics.american import binomial_price, ExerciseStyle
    import numpy as np

    am_steps = st.slider("Binomial steps", 50, 500, 200, step=50)
    am_result = binomial_price(
        p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility,
        option_type=opt, q=p.dividend_yield,
        exercise=ExerciseStyle.AMERICAN, steps=am_steps,
    )
    eu_result = binomial_price(
        p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility,
        option_type=opt, q=p.dividend_yield,
        exercise=ExerciseStyle.EUROPEAN, steps=am_steps,
    )
    early_ex_premium = am_result.price - eu_result.price

    metric_row(4,
        ["BS (European)", "Binomial (European)", "Binomial (American)", "Early-Exercise Premium"],
        [f"${price:.4f}", f"${eu_result.price:.4f}", f"${am_result.price:.4f}", f"${early_ex_premium:.4f}"],
    )

    # ---- Rate curve (Track 3) ------------------------------------------
    with st.expander("Interest Rate Term Structure"):
        from analytics.rates import RateCurve, flat_curve
        from visualization.vol_charts import plot_rate_curve

        st.caption("Flat curve from sidebar risk-free rate; edit pillars for a custom curve.")
        curve = flat_curve(p.risk_free_rate, label=f"Flat {p.risk_free_rate:.2%}")
        fig_rc = plot_rate_curve(curve.pillars, curve.rates, label=curve.label)
        st.plotly_chart(fig_rc, use_container_width=True)
        st.markdown(f"Discount factor at T={p.expiry_years:.2f}y: **{curve.df(p.expiry_years):.6f}**")
