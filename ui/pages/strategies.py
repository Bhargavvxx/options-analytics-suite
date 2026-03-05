"""Strategy Analysis page."""
from __future__ import annotations

import streamlit as st

from strategies.definitions import STRATEGY_CATALOG
from strategies.pricing import price_strategy
from strategies.signals import generate_trading_signals
from visualization.strategy_charts import plot_strategy_payoff, plot_strategy_comparison
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Options Strategy Analysis")

    # Strategy selector
    strat_keys = list(STRATEGY_CATALOG.keys())
    strat_labels = [STRATEGY_CATALOG[k].name for k in strat_keys]
    selected_idx = st.selectbox("Select Strategy", range(len(strat_labels)), format_func=lambda i: strat_labels[i])
    selected_key = strat_keys[selected_idx]
    defn = STRATEGY_CATALOG[selected_key]

    st.markdown(f"**{defn.name}**: {defn.description}")
    st.markdown(f"Legs: {len(defn.legs)}")

    # Pricing
    entry = price_strategy(defn, p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, p.dividend_yield)
    cost_type = "Debit" if entry > 0 else "Credit"
    st.metric("Net Entry Cost", f"${entry:.4f}", delta=cost_type)

    # Payoff chart
    st.subheader("Payoff at Expiry")
    fig = plot_strategy_payoff(defn, p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, p.dividend_yield)
    st.plotly_chart(fig, use_container_width=True)

    # Comparison
    st.subheader("Strategy Comparison")
    compare_keys = st.multiselect(
        "Compare strategies",
        strat_keys,
        default=["straddle", "iron_condor", "bull_call_spread"],
        format_func=lambda k: STRATEGY_CATALOG[k].name,
    )
    if compare_keys:
        fig_cmp = plot_strategy_comparison(
            p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility, p.dividend_yield,
            strategies=compare_keys,
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    # Trading signals
    st.subheader("Trading Signals (IV vs HV)")
    hv_input = st.number_input("Historical Vol for signal", value=p.volatility, min_value=0.01, step=0.01, format="%.2f")
    iv_input = st.number_input("Implied Vol for signal", value=p.volatility, min_value=0.01, step=0.01, format="%.2f")
    sig = generate_trading_signals(p.spot, p.strike, p.expiry_years, p.risk_free_rate, hv_input, iv_input, p.dividend_yield)

    col1, col2 = st.columns(2)
    col1.info(f"**Vol Assessment**: {sig.volatility_assessment}\n\n{sig.vol_action}")
    col2.info(f"**Recommended**: {sig.recommended_strategy}")
    st.markdown(f"- **Calls**: {sig.call_assessment} → {sig.call_action}")
    st.markdown(f"- **Puts**: {sig.put_assessment} → {sig.put_action}")
