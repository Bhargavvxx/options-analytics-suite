"""
Performance metrics computed from a BacktestResult.

All helpers are pure functions; they consume a ``BacktestResult`` or
plain return series and return metrics in a frozen dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import Settings


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    total_return_pct: float
    annualised_return_pct: float
    annualised_vol_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    num_trades: int
    total_pnl: float
    total_costs: float


def compute_metrics(
    result,  # BacktestResult
    *,
    risk_free_rate: Optional[float] = None,
    periods_per_year: int = 252,
) -> PerformanceMetrics:
    """Compute risk / return metrics from a ``BacktestResult``."""
    cfg = Settings()
    rf = risk_free_rate if risk_free_rate is not None else cfg.default_risk_free_rate
    eq = result.equity_curve
    ret = result.daily_returns

    if len(ret) < 2:
        return PerformanceMetrics(
            total_return_pct=0, annualised_return_pct=0, annualised_vol_pct=0,
            sharpe_ratio=0, sortino_ratio=0, max_drawdown_pct=0, calmar_ratio=0,
            win_rate=0, profit_factor=0, avg_win=0, avg_loss=0,
            num_trades=result.num_trades, total_pnl=result.total_pnl,
            total_costs=result.total_costs,
        )

    # ----- return-based -----
    total_ret = (eq.iloc[-1] / eq.iloc[0]) - 1.0
    n_days = max(len(ret), 1)
    ann_ret = (1 + total_ret) ** (periods_per_year / n_days) - 1
    ann_vol = float(ret.std() * np.sqrt(periods_per_year))

    daily_rf = rf / periods_per_year
    excess = ret - daily_rf
    sharpe = float(excess.mean() / ret.std() * np.sqrt(periods_per_year)) if ret.std() > 0 else 0.0

    downside = ret[ret < daily_rf]
    down_std = float(downside.std() * np.sqrt(periods_per_year)) if len(downside) > 1 else 1e-8
    sortino = float((ret.mean() - daily_rf) * np.sqrt(periods_per_year) / down_std)

    # ----- drawdown -----
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max
    max_dd = float(drawdown.min())

    calmar = ann_ret / abs(max_dd) if abs(max_dd) > 1e-8 else 0.0

    # ----- trade-based -----
    wins = [t.pnl for t in result.trades if t.pnl > 0]
    losses = [t.pnl for t in result.trades if t.pnl <= 0]
    wr = len(wins) / len(result.trades) if result.trades else 0.0
    avg_w = float(np.mean(wins)) if wins else 0.0
    avg_l = float(np.mean(losses)) if losses else 0.0
    pf = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")

    return PerformanceMetrics(
        total_return_pct=round(total_ret * 100, 4),
        annualised_return_pct=round(ann_ret * 100, 4),
        annualised_vol_pct=round(ann_vol * 100, 4),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        max_drawdown_pct=round(max_dd * 100, 4),
        calmar_ratio=round(calmar, 4),
        win_rate=round(wr, 4),
        profit_factor=round(pf, 4),
        avg_win=round(avg_w, 2),
        avg_loss=round(avg_l, 2),
        num_trades=result.num_trades,
        total_pnl=round(result.total_pnl, 2),
        total_costs=round(result.total_costs, 2),
    )
