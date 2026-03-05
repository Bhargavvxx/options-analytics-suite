"""Portfolio Risk & Stress Testing page."""
from __future__ import annotations

import streamlit as st

from analytics.pricing import OptionType
from risk.portfolio import Portfolio, Position, PortfolioValuation
from risk.stress import run_stress_test
from visualization.vol_charts import plot_stress_heatmap
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Portfolio Risk & Stress Testing")

    # ---- build demo portfolio from sidebar params ----------------------
    st.subheader("Portfolio Builder")
    st.caption("Add option positions below. The sidebar spot, rate, and dividend yield apply to all.")

    if "risk_positions" not in st.session_state:
        st.session_state.risk_positions: list = []

    with st.form("add_position"):
        cols = st.columns(5)
        pos_type = cols[0].selectbox("Type", ["call", "put", "stock"], key="rp_type")
        pos_strike = cols[1].number_input("Strike", value=p.strike, min_value=0.01, key="rp_k")
        pos_T = cols[2].number_input("T (yrs)", value=p.expiry_years, min_value=0.01, key="rp_t")
        pos_sigma = cols[3].number_input("IV", value=p.volatility, min_value=0.01, key="rp_iv")
        pos_qty = cols[4].number_input("Qty (±)", value=1, step=1, key="rp_qty")
        submitted = st.form_submit_button("Add Position")
        if submitted:
            st.session_state.risk_positions.append(
                Position(
                    instrument=p.ticker,
                    option_type=pos_type,
                    strike=pos_strike,
                    T=pos_T,
                    sigma=pos_sigma,
                    quantity=int(pos_qty),
                )
            )

    positions = st.session_state.risk_positions

    if not positions:
        st.info("Add at least one position to see risk analytics.")
        return

    # Show current positions table
    import pandas as pd
    pos_rows = [
        {"#": i + 1, "Type": pos.option_type, "Strike": pos.strike,
         "T": pos.T, "IV": pos.sigma, "Qty": pos.quantity}
        for i, pos in enumerate(positions)
    ]
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

    if st.button("Clear All Positions"):
        st.session_state.risk_positions = []
        st.rerun()

    # ---- Portfolio valuation -------------------------------------------
    st.subheader("Portfolio Valuation")
    portfolio = Portfolio(positions)
    val = portfolio.valuate(p.spot, p.risk_free_rate, p.dividend_yield)

    metric_row(6,
        ["Total Value", "Delta", "Gamma", "Theta", "Vega", "Rho"],
        [f"${val.total_value:,.2f}", f"{val.total_delta:,.2f}",
         f"{val.total_gamma:,.4f}", f"{val.total_theta:,.2f}",
         f"{val.total_vega:,.2f}", f"{val.total_rho:,.2f}"],
    )

    # Contribution breakdown
    with st.expander("Per-Position Breakdown"):
        breakdown = pd.DataFrame(val.positions)
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

    # ---- Stress testing -----------------------------------------------
    st.subheader("Stress Test")
    st.caption("Re-values the portfolio across spot × vol shock grid.")

    result = run_stress_test(portfolio, p.spot, p.risk_free_rate, p.dividend_yield)

    sc1, sc2 = st.columns(2)
    sc1.metric("Worst P&L", f"${result.worst_pnl:,.2f}")
    sc2.metric("Best P&L", f"${result.best_pnl:,.2f}")

    fig_stress = plot_stress_heatmap(result.spot_shocks, result.vol_shocks, result.pnl_matrix)
    st.plotly_chart(fig_stress, use_container_width=True)
