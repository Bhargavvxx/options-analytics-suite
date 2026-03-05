"""Charts for volatility analytics."""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go


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
