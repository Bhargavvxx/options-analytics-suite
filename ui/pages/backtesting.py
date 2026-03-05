"""Backtesting page."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from data.market_data import get_default_provider
from analytics.volatility import historical_volatility
from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics
from backtesting.simulation import run_educational_simulation
from visualization.backtest_charts import plot_equity_curve, plot_drawdown
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Backtesting")

    tab_bt, tab_sim = st.tabs(["Vol-Signal Backtest", "Monte-Carlo Simulation"])

    # ---- Vol-signal backtest ----
    with tab_bt:
        st.markdown(
            "Backtest a **short-vol** strategy that sells options when IV / HV "
            "exceeds a threshold and closes when the ratio normalises."
        )

        col1, col2, col3 = st.columns(3)
        entry_thresh = col1.number_input("Entry IV/HV threshold", value=1.10, step=0.05)
        exit_thresh = col2.number_input("Exit IV/HV threshold", value=1.00, step=0.05)
        capital = col3.number_input("Initial capital ($)", value=100_000, step=10_000)

        if st.button("Run Backtest"):
            provider = get_default_provider()
            try:
                prices, _ = provider.fetch_history(p.ticker, period=p.history_period)
            except Exception as e:
                st.error(f"Data fetch failed: {e}")
                return

            if prices.empty:
                st.warning("No price data.")
                return

            # Compute IV proxy & HV and add to frame
            hv = historical_volatility(prices["Close"], window=20)
            prices["HV"] = hv
            prices["IV"] = p.volatility  # placeholder — real IV requires chain data

            prices = prices.dropna(subset=["HV", "IV"])
            if prices.empty:
                st.warning("Not enough data after computing HV.")
                return

            engine = BacktestEngine(
                prices,
                initial_capital=float(capital),
                cost_per_contract=1.50,
                slippage_pct=0.001,
            )
            result = engine.run_vol_signal_backtest(
                strike=p.strike,
                T=p.expiry_years,
                entry_threshold=entry_thresh,
                exit_threshold=exit_thresh,
                option_type=p.option_type,
            )
            metrics = compute_metrics(result)

            st.subheader("Performance Summary")
            metric_row(4,
                ["Total Return", "Sharpe", "Max DD", "Win Rate"],
                [
                    f"{metrics.total_return_pct:.2f}%",
                    f"{metrics.sharpe_ratio:.2f}",
                    f"{metrics.max_drawdown_pct:.2f}%",
                    f"{metrics.win_rate:.1%}",
                ],
            )
            metric_row(4,
                ["Num Trades", "Avg PnL", "Total Costs", "Sortino"],
                [
                    str(metrics.num_trades),
                    f"${metrics.avg_win + metrics.avg_loss:.2f}",
                    f"${metrics.total_costs:.2f}",
                    f"{metrics.sortino_ratio:.2f}",
                ],
            )

            fig_eq = plot_equity_curve(result)
            st.plotly_chart(fig_eq, use_container_width=True)

            fig_dd = plot_drawdown(result)
            st.plotly_chart(fig_dd, use_container_width=True)

            with st.expander("Trade Log"):
                trades_data = [{
                    "Entry": t.entry_date, "Exit": t.exit_date,
                    "Dir": t.direction, "Type": t.option_type,
                    "K": t.strike, "Entry$": f"{t.entry_price:.4f}",
                    "Exit$": f"{t.exit_price:.4f}", "PnL": f"{t.pnl:+.2f}",
                } for t in result.trades]
                st.dataframe(pd.DataFrame(trades_data), use_container_width=True)

    # ---- Monte-Carlo simulation ----
    with tab_sim:
        st.markdown(
            "⚠️ **Educational only** — simulates GBM paths, not real market dynamics."
        )
        n_paths = st.slider("Number of paths", 1000, 50_000, 10_000, step=1000)
        if st.button("Run Simulation"):
            sim = run_educational_simulation(
                p.spot, p.strike, p.expiry_years, p.risk_free_rate, p.volatility,
                p.option_type, n_paths=n_paths,
            )
            metric_row(3,
                ["MC Price", "BS Price", "Difference"],
                [
                    f"${sim.pv_mean_payoff:.4f}",
                    f"${sim.parameters['bs_price']:.4f}",
                    f"${sim.pv_mean_payoff - sim.parameters['bs_price']:.4f}",
                ],
            )
            # Show a few sample paths
            import plotly.graph_objects as go
            fig = go.Figure()
            for i in range(min(50, n_paths)):
                fig.add_trace(go.Scatter(y=sim.price_paths[i], mode="lines",
                                          opacity=0.3, showlegend=False))
            fig.update_layout(title=f"Sample GBM Paths (n={n_paths})",
                              xaxis_title="Day", yaxis_title="Price", height=400)
            st.plotly_chart(fig, use_container_width=True)
