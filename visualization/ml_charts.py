"""Charts for ML model diagnostics."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ml.training import TrainingResult


def plot_model_comparison(results: Dict[str, TrainingResult]) -> go.Figure:
    """Bar chart comparing test RMSE, MAE, R² across models."""
    names = list(results.keys())
    rmse = [r.test_rmse for r in results.values()]
    mae = [r.test_mae for r in results.values()]
    r2 = [r.test_r2 for r in results.values()]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Test RMSE", "Test MAE", "Test R²"),
    )
    fig.add_trace(go.Bar(x=names, y=rmse, name="RMSE", marker_color="steelblue"), row=1, col=1)
    fig.add_trace(go.Bar(x=names, y=mae, name="MAE", marker_color="coral"), row=1, col=2)
    fig.add_trace(go.Bar(x=names, y=r2, name="R²", marker_color="mediumseagreen"), row=1, col=3)

    fig.update_layout(
        title="Model Comparison",
        showlegend=False,
        height=400,
    )
    return fig


def plot_feature_importance(
    feature_names: List[str],
    importances: np.ndarray,
    *,
    top_n: int = 10,
) -> go.Figure:
    """Horizontal bar chart of top-N feature importances."""
    idx = np.argsort(importances)[::-1][:top_n]
    names = [feature_names[i] for i in idx]
    vals = importances[idx]

    fig = go.Figure(go.Bar(
        x=vals[::-1],
        y=names[::-1],
        orientation="h",
        marker_color="teal",
    ))
    fig.update_layout(
        title=f"Top {top_n} Feature Importances",
        xaxis_title="Importance",
        height=max(300, top_n * 30),
    )
    return fig
