"""Charts for strategy payoff diagrams."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from strategies.definitions import StrategyDefinition, STRATEGY_CATALOG
from strategies.pricing import price_strategy, strategy_payoff


def plot_strategy_payoff(
    definition: StrategyDefinition,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    *,
    range_pct: float = 0.30,
    n: int = 200,
) -> go.Figure:
    """Expiration payoff diagram for a single strategy."""
    entry = price_strategy(definition, S, K, T, r, sigma, q)
    S_range = np.linspace(K * (1 - range_pct), K * (1 + range_pct), n)
    pnl = strategy_payoff(definition, S_range, K, entry)

    fig = go.Figure()
    # Colour fill: green above 0, red below
    fig.add_trace(go.Scatter(
        x=S_range, y=pnl, mode="lines", name="P&L",
        fill="tozeroy",
        fillcolor="rgba(0,200,0,0.15)",
        line=dict(color="green", width=2),
    ))
    fig.add_hline(y=0, line_color="grey", line_dash="dash")
    fig.add_vline(x=K, line_color="blue", line_dash="dot",
                   annotation_text=f"K={K:.0f}")
    fig.add_vline(x=S, line_color="orange", line_dash="dot",
                   annotation_text=f"S={S:.1f}")

    fig.update_layout(
        title=f"{definition.name} — Payoff at Expiry (entry cost={entry:.2f})",
        xaxis_title="Underlying Price at Expiry",
        yaxis_title="Profit / Loss",
        height=450,
    )
    return fig


def plot_strategy_comparison(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    *,
    strategies: list[str] | None = None,
    range_pct: float = 0.30,
    n: int = 200,
) -> go.Figure:
    """Overlay payoff diagrams for multiple strategies."""
    keys = strategies or list(STRATEGY_CATALOG.keys())
    S_range = np.linspace(K * (1 - range_pct), K * (1 + range_pct), n)

    fig = go.Figure()
    for key in keys:
        defn = STRATEGY_CATALOG.get(key)
        if defn is None:
            continue
        entry = price_strategy(defn, S, K, T, r, sigma, q)
        pnl = strategy_payoff(defn, S_range, K, entry)
        fig.add_trace(go.Scatter(x=S_range, y=pnl, mode="lines", name=defn.name))

    fig.add_hline(y=0, line_color="grey", line_dash="dash")
    fig.update_layout(
        title="Strategy Comparison — Payoff at Expiry",
        xaxis_title="Underlying Price at Expiry",
        yaxis_title="Profit / Loss",
        height=500,
    )
    return fig
