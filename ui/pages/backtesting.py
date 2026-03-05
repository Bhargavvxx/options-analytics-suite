"""Backtesting page."""
from __future__ import annotations

import io
import json
from dataclasses import asdict
from datetime import date, timedelta

import streamlit as st
import pandas as pd

from data.market_data import get_default_provider
from analytics.volatility import historical_volatility
from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics
from backtesting.simulation import run_educational_simulation
from visualization.backtest_charts import plot_equity_curve, plot_drawdown
from ui.components import SidebarParams, metric_row


def _trades_to_df(trades) -> pd.DataFrame:
    """Convert list of Trade objects to a detailed DataFrame."""
    rows = []
    for t in trades:
        rows.append({
            "Entry": t.entry_date,
            "Exit": t.exit_date,
            "Direction": t.direction,
            "Type": t.option_type,
            "Strike": t.strike,
            "Entry$": round(t.entry_price, 4),
            "Exit$": round(t.exit_price, 4),
            "Qty": t.quantity,
            "PnL": round(t.pnl, 2),
            "Cost": round(t.cost, 2),
            "Entry_IV": round(t.entry_iv, 4),
            "Exit_IV": round(t.exit_iv, 4),
            "Entry_T": round(t.entry_T, 4),
            "Exit_T": round(t.exit_T, 4),
            "Entry_Spread": round(t.entry_spread, 4),
            "Exit_Spread": round(t.exit_spread, 4),
            "Entry_Exec": t.entry_exec_mode,
            "Exit_Exec": t.exit_exec_mode,
        })
    return pd.DataFrame(rows)


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

        col4, col5 = st.columns(2)
        use_expiry = col4.checkbox("Use decaying time-to-expiry", value=True)
        expiry_date = col5.date_input(
            "Option expiry date",
            value=date.today() + timedelta(days=30),
            disabled=not use_expiry,
        )

        if st.button("Run Backtest"):
            provider = get_default_provider()
            try:
                prices, _ = provider.get_stock_data(p.ticker, period=p.history_period)
            except Exception as e:
                st.error(f"Data fetch failed: {e}")
                return

            if prices.empty:
                st.warning("No price data.")
                return

            # Compute IV proxy & HV and add to frame
            import numpy as np
            log_returns = np.log(prices["Close"] / prices["Close"].shift(1))
            hv = historical_volatility(log_returns, window=20)
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
                expiry_date=expiry_date if use_expiry else None,
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

            # ---- Trade Blotter ----
            with st.expander("Trade Blotter", expanded=False):
                blotter_df = _trades_to_df(result.trades)
                st.dataframe(blotter_df, use_container_width=True)

                dl_col1, dl_col2 = st.columns(2)
                csv_buf = blotter_df.to_csv(index=False)
                dl_col1.download_button(
                    "Download CSV",
                    data=csv_buf,
                    file_name="blotter.csv",
                    mime="text/csv",
                )

                report_dict = {
                    "config": asdict(result.config) if result.config else {},
                    "summary": {
                        "total_return_pct": metrics.total_return_pct,
                        "sharpe_ratio": metrics.sharpe_ratio,
                        "sortino_ratio": metrics.sortino_ratio,
                        "max_drawdown_pct": metrics.max_drawdown_pct,
                        "win_rate": metrics.win_rate,
                        "num_trades": metrics.num_trades,
                        "total_pnl": result.total_pnl,
                        "total_costs": result.total_costs,
                    },
                    "trades": [asdict(t) for t in result.trades],
                }
                # Convert date objects for JSON serialisation
                json_buf = json.dumps(report_dict, indent=2, default=str)
                dl_col2.download_button(
                    "Download Report JSON",
                    data=json_buf,
                    file_name="backtest_report.json",
                    mime="application/json",
                )

            # ---- Backtest Config ----
            if result.config:
                with st.expander("Backtest Configuration (reproducible)"):
                    st.json(asdict(result.config))

    # ---- Monte-Carlo simulation ----
    with tab_sim:
        st.markdown(
            "**Educational only** — simulates GBM paths, not real market dynamics."
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
