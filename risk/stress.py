"""
Scenario-based stress testing for option portfolios.

Generates a grid of spot / volatility / rate shocks, re-values the
portfolio under each scenario, and produces a structured result with
P&L heatmaps and Greeks sensitivity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from risk.portfolio import Portfolio, PortfolioValuation
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Output from a stress-test run."""
    base_value: float
    spot_shocks: np.ndarray        # 1-D array of relative shocks (e.g. -0.20 … +0.20)
    vol_shocks: np.ndarray         # 1-D array of absolute vol shocks
    pnl_matrix: np.ndarray         # (n_spot, n_vol) P&L vs base
    delta_matrix: np.ndarray       # (n_spot, n_vol) portfolio delta under shock
    gamma_matrix: np.ndarray
    vega_matrix: np.ndarray
    worst_pnl: float = 0.0
    best_pnl: float = 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_stress_test(
    portfolio: Portfolio,
    S: float,
    r: float,
    q: float = 0.0,
    spot_shocks: Optional[Sequence[float]] = None,
    vol_shocks: Optional[Sequence[float]] = None,
) -> ScenarioResult:
    """Re-value the portfolio across a spot × vol shock grid.

    Parameters
    ----------
    portfolio : Portfolio
    S : float
        Current spot.
    r : float
        Risk-free rate.
    q : float
        Dividend yield.
    spot_shocks : sequence of float, optional
        Relative spot shocks (e.g. ``[-0.20, -0.10, 0, 0.10, 0.20]``).
        Defaults to ±25 % in 5 % steps.
    vol_shocks : sequence of float, optional
        Absolute vol shocks (e.g. ``[-0.10, -0.05, 0, 0.05, 0.10]``).
        Defaults to ±15 pp in 5 pp steps.

    Returns
    -------
    ScenarioResult
    """
    if spot_shocks is None:
        spot_shocks = np.arange(-0.25, 0.26, 0.05)
    else:
        spot_shocks = np.asarray(spot_shocks, dtype=float)

    if vol_shocks is None:
        vol_shocks = np.arange(-0.15, 0.16, 0.05)
    else:
        vol_shocks = np.asarray(vol_shocks, dtype=float)

    # Base valuation
    base_val = portfolio.valuate(S, r, q)
    base_value = base_val.total_value

    ns = len(spot_shocks)
    nv = len(vol_shocks)
    pnl = np.zeros((ns, nv))
    delta = np.zeros((ns, nv))
    gamma = np.zeros((ns, nv))
    vega = np.zeros((ns, nv))

    for si, ds in enumerate(spot_shocks):
        S_shocked = S * (1.0 + ds)
        S_shocked = max(S_shocked, 1e-6)

        for vi, dv in enumerate(vol_shocks):
            # Create a shocked copy of the portfolio
            shocked_portfolio = Portfolio()
            for pos in portfolio.positions:
                from copy import copy
                p = copy(pos)
                if p.option_type != "stock":
                    p.sigma = max(p.sigma + dv, 1e-6)
                shocked_portfolio.add(p)

            val = shocked_portfolio.valuate(S_shocked, r, q)
            pnl[si, vi] = val.total_value - base_value
            delta[si, vi] = val.total_delta
            gamma[si, vi] = val.total_gamma
            vega[si, vi] = val.total_vega

    result = ScenarioResult(
        base_value=base_value,
        spot_shocks=spot_shocks,
        vol_shocks=vol_shocks,
        pnl_matrix=pnl,
        delta_matrix=delta,
        gamma_matrix=gamma,
        vega_matrix=vega,
        worst_pnl=float(np.min(pnl)),
        best_pnl=float(np.max(pnl)),
    )

    logger.info(
        "Stress test: %dx%d grid, base=%.2f, worst=%.2f, best=%.2f",
        ns, nv, base_value, result.worst_pnl, result.best_pnl,
    )
    return result
