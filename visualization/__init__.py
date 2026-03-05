"""Visualization layer — all Plotly chart factories."""
from visualization.pricing_charts import plot_option_price_surface, plot_greeks_dashboard
from visualization.vol_charts import (
    plot_volatility_cone,
    plot_volatility_term_structure,
    plot_iv_surface_3d,
    plot_arbitrage_heatmap,
    plot_rate_curve,
    plot_stress_heatmap,
)
from visualization.strategy_charts import plot_strategy_payoff, plot_strategy_comparison
from visualization.backtest_charts import plot_equity_curve, plot_drawdown
from visualization.ml_charts import plot_model_comparison, plot_feature_importance

__all__ = [
    "plot_option_price_surface",
    "plot_greeks_dashboard",
    "plot_volatility_cone",
    "plot_volatility_term_structure",
    "plot_iv_surface_3d",
    "plot_arbitrage_heatmap",
    "plot_rate_curve",
    "plot_stress_heatmap",
    "plot_strategy_payoff",
    "plot_strategy_comparison",
    "plot_equity_curve",
    "plot_drawdown",
    "plot_model_comparison",
    "plot_feature_importance",
]
