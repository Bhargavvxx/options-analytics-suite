"""Charts for volatility analytics and arbitrage diagnostics."""
from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go

if TYPE_CHECKING:
    from analytics.arbitrage import SurfaceArbitrageReport


def plot_volatility_cone(
    cone_df: pd.DataFrame,
) -> go.Figure:
    """Plot a volatility cone from ``realised_vol_cone()`` output.

    The DataFrame has rows = stat names (min, p25, median, p75, max, current)
    and columns = window sizes as strings.  We transpose so windows are on x-axis.
    """
    fig = go.Figure()
    # Transpose: windows become index, stats become columns
    df = cone_df.T
    windows = df.index.astype(str)

    if "min" in df.columns and "max" in df.columns:
        fig.add_trace(go.Scatter(
            x=windows, y=df["max"], mode="lines", name="Max",
            line=dict(dash="dot", color="rgba(200,200,200,0.6)"),
        ))
        fig.add_trace(go.Scatter(
            x=windows, y=df["min"], mode="lines", name="Min",
            fill="tonexty", fillcolor="rgba(200,200,200,0.15)",
            line=dict(dash="dot", color="rgba(200,200,200,0.6)"),
        ))
    if "p75" in df.columns and "p25" in df.columns:
        fig.add_trace(go.Scatter(
            x=windows, y=df["p75"], mode="lines", name="75th pctl",
            line=dict(color="orange"),
        ))
        fig.add_trace(go.Scatter(
            x=windows, y=df["p25"], mode="lines", name="25th pctl",
            fill="tonexty", fillcolor="rgba(255,165,0,0.15)",
            line=dict(color="orange"),
        ))
    if "median" in df.columns:
        fig.add_trace(go.Scatter(
            x=windows, y=df["median"], mode="lines", name="Median",
            line=dict(color="blue", width=2),
        ))
    if "current" in df.columns:
        fig.add_trace(go.Scatter(
            x=windows, y=df["current"], mode="lines+markers",
            name="Current", line=dict(color="red", width=2),
        ))

    fig.update_layout(
        title="Volatility Cone",
        xaxis_title="Window (days)",
        yaxis_title="Annualised Volatility",
        yaxis_tickformat=".0%",
        height=450,
    )
    return fig


def plot_volatility_term_structure(
    iv_by_expiry: Dict[str, float],
    hv: Optional[float] = None,
) -> go.Figure:
    """IV term-structure plot (IV vs days-to-expiry)."""
    expiries = list(iv_by_expiry.keys())
    ivs = list(iv_by_expiry.values())

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=expiries, y=ivs, mode="lines+markers", name="IV",
    ))
    if hv is not None:
        fig.add_hline(y=hv, line_dash="dash", line_color="red",
                       annotation_text=f"HV = {hv:.1%}")

    fig.update_layout(
        title="IV Term Structure",
        xaxis_title="Expiry",
        yaxis_title="Implied Volatility",
        yaxis_tickformat=".0%",
        height=400,
    )
    return fig


def plot_iv_surface_3d(
    strikes: np.ndarray,
    expiries: np.ndarray,
    iv_matrix: np.ndarray,
) -> go.Figure:
    """3-D IV surface (strike × expiry → IV)."""
    fig = go.Figure(data=[go.Surface(
        x=strikes,
        y=expiries,
        z=iv_matrix,
        colorscale="RdYlGn_r",
        colorbar=dict(title="IV"),
    )])
    fig.update_layout(
        title="Implied Volatility Surface",
        scene=dict(
            xaxis_title="Strike",
            yaxis_title="Expiry (yrs)",
            zaxis_title="IV",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


# ---------------------------------------------------------------------------
# Arbitrage diagnostics heatmap
# ---------------------------------------------------------------------------

def plot_arbitrage_heatmap(
    report: "SurfaceArbitrageReport",
    strike_grid: np.ndarray,
    time_grid: np.ndarray,
) -> go.Figure:
    """Overlay calendar + butterfly violations on a strike × expiry heatmap.

    Red cells = calendar violation, Blue cells = butterfly violation.
    """
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Calendar-Spread Arb", "Butterfly Arb"))

    strikes = strike_grid[0, :]
    times = time_grid[:, 0]

    # Calendar heatmap
    cal_z = report.calendar_mask.astype(float) if report.calendar_mask is not None else np.zeros_like(strike_grid)
    fig.add_trace(go.Heatmap(
        x=strikes, y=times, z=cal_z,
        colorscale=[[0, "white"], [1, "red"]],
        showscale=False, name="Calendar",
    ), row=1, col=1)

    # Butterfly heatmap
    but_z = report.butterfly_mask.astype(float) if report.butterfly_mask is not None else np.zeros_like(strike_grid)
    fig.add_trace(go.Heatmap(
        x=strikes, y=times, z=but_z,
        colorscale=[[0, "white"], [1, "blue"]],
        showscale=False, name="Butterfly",
    ), row=1, col=2)

    fig.update_xaxes(title_text="Strike", row=1, col=1)
    fig.update_xaxes(title_text="Strike", row=1, col=2)
    fig.update_yaxes(title_text="Expiry (yrs)", row=1, col=1)
    fig.update_yaxes(title_text="Expiry (yrs)", row=1, col=2)
    fig.update_layout(title="Surface Arbitrage Diagnostics", height=400)
    return fig


# ---------------------------------------------------------------------------
# Rate curve chart
# ---------------------------------------------------------------------------

def plot_rate_curve(
    pillars: np.ndarray,
    rates: np.ndarray,
    label: str = "Zero Curve",
) -> go.Figure:
    """Plot a zero-rate term structure."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pillars, y=rates, mode="lines+markers", name=label,
    ))
    fig.update_layout(
        title="Interest Rate Term Structure",
        xaxis_title="Maturity (years)",
        yaxis_title="Zero Rate",
        yaxis_tickformat=".2%",
        height=400,
    )
    return fig


# ---------------------------------------------------------------------------
# Stress-test P&L heatmap
# ---------------------------------------------------------------------------

def plot_stress_heatmap(
    spot_shocks: np.ndarray,
    vol_shocks: np.ndarray,
    pnl_matrix: np.ndarray,
) -> go.Figure:
    """Spot × Vol shock heatmap of portfolio P&L."""
    fig = go.Figure(data=go.Heatmap(
        x=[f"{v:+.0%}" for v in vol_shocks],
        y=[f"{s:+.0%}" for s in spot_shocks],
        z=pnl_matrix,
        colorscale="RdYlGn",
        colorbar=dict(title="P&L"),
    ))
    fig.update_layout(
        title="Stress Test — P&L Heatmap",
        xaxis_title="Vol Shock",
        yaxis_title="Spot Shock",
        height=450,
    )
    return fig
