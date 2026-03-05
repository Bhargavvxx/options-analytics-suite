"""Charts for option pricing and Greeks."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics.pricing import OptionType, black_scholes_price
from analytics.greeks import analytical_greeks


def plot_option_price_surface(
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    q: float = 0.0,
    *,
    spot_range: tuple[float, float] = (0.7, 1.3),
    vol_range: tuple[float, float] = (0.05, 0.80),
    n: int = 50,
) -> go.Figure:
    """3-D surface: option price as f(spot, vol)."""
    opt = OptionType.CALL if option_type == "call" else OptionType.PUT
    spots = np.linspace(K * spot_range[0], K * spot_range[1], n)
    vols = np.linspace(vol_range[0], vol_range[1], n)
    S_grid, V_grid = np.meshgrid(spots, vols)

    prices = np.vectorize(
        lambda s, v: black_scholes_price(s, K, T, r, v, opt, q, validate=False)
    )(S_grid, V_grid)

    fig = go.Figure(data=[go.Surface(
        x=S_grid, y=V_grid, z=prices,
        colorscale="Viridis",
        colorbar=dict(title="Price"),
    )])
    fig.update_layout(
        title=f"{option_type.title()} Price Surface (K={K:.0f}, T={T:.2f}y)",
        scene=dict(
            xaxis_title="Spot Price",
            yaxis_title="Volatility",
            zaxis_title="Option Price",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def plot_greeks_dashboard(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    q: float = 0.0,
    *,
    spot_range_pct: float = 0.30,
    n: int = 100,
) -> go.Figure:
    """2x2 dashboard: Delta, Gamma, Theta, Vega vs spot."""
    opt = OptionType.CALL if option_type == "call" else OptionType.PUT
    spots = np.linspace(S * (1 - spot_range_pct), S * (1 + spot_range_pct), n)

    deltas, gammas, thetas, vegas = [], [], [], []
    for s in spots:
        g = analytical_greeks(s, K, T, r, sigma, opt, q)
        deltas.append(g.delta)
        gammas.append(g.gamma)
        thetas.append(g.theta)
        vegas.append(g.vega)

    fig = make_subplots(rows=2, cols=2, subplot_titles=("Delta", "Gamma", "Theta", "Vega"))
    line_kw = dict(mode="lines")

    fig.add_trace(go.Scatter(x=spots, y=deltas, name="Delta", **line_kw), row=1, col=1)
    fig.add_trace(go.Scatter(x=spots, y=gammas, name="Gamma", **line_kw), row=1, col=2)
    fig.add_trace(go.Scatter(x=spots, y=thetas, name="Theta", **line_kw), row=2, col=1)
    fig.add_trace(go.Scatter(x=spots, y=vegas, name="Vega", **line_kw), row=2, col=2)

    # Add vertical line at current spot
    for row, col in [(1, 1), (1, 2), (2, 1), (2, 2)]:
        fig.add_vline(x=S, line_dash="dash", line_color="grey", row=row, col=col)

    fig.update_layout(
        title=f"Greeks Dashboard — {option_type.title()} (K={K:.0f}, σ={sigma:.0%})",
        showlegend=False,
        height=600,
    )
    return fig
