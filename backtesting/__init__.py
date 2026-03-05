"""Backtesting framework — engine, metrics, simulation."""
from backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    ExecutionMode,
    Trade,
)
from backtesting.metrics import compute_metrics, PerformanceMetrics
from backtesting.simulation import run_educational_simulation

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "ExecutionMode",
    "Trade",
    "compute_metrics",
    "PerformanceMetrics",
    "run_educational_simulation",
]
