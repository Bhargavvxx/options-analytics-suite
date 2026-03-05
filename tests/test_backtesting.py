"""Tests for backtesting module."""
import pytest
import numpy as np
import pandas as pd

from backtesting.simulation import run_educational_simulation
from backtesting.metrics import compute_metrics, PerformanceMetrics
from backtesting.engine import BacktestResult


class TestSimulation:
    def test_mc_price_converges_to_bs(self):
        sim = run_educational_simulation(100, 100, 1.0, 0.05, 0.20, "call", n_paths=50_000, seed=42)
        assert sim.pv_mean_payoff == pytest.approx(sim.parameters["bs_price"], abs=0.20)

    def test_paths_shape(self):
        sim = run_educational_simulation(100, 100, 0.5, 0.05, 0.20, n_paths=1000, n_steps=126)
        assert sim.price_paths.shape == (1000, 127)  # 126 steps + initial

    def test_put_payoff(self):
        sim = run_educational_simulation(100, 100, 1.0, 0.05, 0.20, "put", n_paths=10_000, seed=42)
        assert sim.pv_mean_payoff > 0


class TestMetrics:
    def test_compute_metrics_from_flat_equity(self):
        eq = pd.Series([100_000] * 100, index=pd.bdate_range("2023-01-01", periods=100))
        result = BacktestResult(
            trades=[], equity_curve=eq, daily_returns=eq.pct_change().dropna(),
            total_pnl=0, total_costs=0, initial_capital=100_000,
            final_capital=100_000, num_trades=0, win_rate=0, avg_pnl=0,
        )
        m = compute_metrics(result)
        assert isinstance(m, PerformanceMetrics)
        assert m.total_return_pct == pytest.approx(0, abs=0.01)
        assert m.max_drawdown_pct == pytest.approx(0, abs=0.01)
