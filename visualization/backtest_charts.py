"""Charts for backtesting results."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backtesting.engine import BacktestResult


def plot_equity_curve(result: BacktestResult) -> go.Figure:
    """Equity curve with trade markers."""
    eq = result.equity_curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eq.index, y=eq.values, mode="lines", name="Equity",
        line=dict(color="steelblue", width=2),
    ))

    # Mark trade entries / exits
    for t in result.trades:
        fig.add_trace(go.Scatter(
            x=[t.entry_date], y=[eq.asof(t.entry_date)],
            mode="markers", marker=dict(symbol="triangle-up", color="green", size=8),
            name="Entry", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[t.exit_date], y=[eq.asof(t.exit_date)],
            mode="markers", marker=dict(symbol="triangle-down", color="red", size=8),
            name="Exit", showlegend=False,
        ))

    fig.update_layout(
        title=f"Equity Curve — {result.num_trades} trades, "
              f"PnL={result.total_pnl:+,.0f}",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=400,
    )
    return fig


def plot_drawdown(result: BacktestResult) -> go.Figure:
    """Drawdown chart as percentage from peak."""
    eq = result.equity_curve
    running_max = eq.cummax()
    dd = (eq - running_max) / running_max * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values, mode="lines",
        fill="tozeroy", fillcolor="rgba(255,0,0,0.15)",
        line=dict(color="red", width=1),
        name="Drawdown",
    ))
    fig.update_layout(
        title="Drawdown from Peak",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        height=300,
    )
    return fig
