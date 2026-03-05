"""
Portfolio risk aggregation.

A ``Portfolio`` holds a collection of option/stock ``Position`` objects
and provides:
* Mark-to-market valuation.
* Aggregated portfolio-level Greeks.
* Per-position contribution breakdown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from analytics.greeks import Greeks, analytical_greeks
from analytics.pricing import OptionType, black_scholes_price
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """A single option or equity position.

    Parameters
    ----------
    instrument : str
        Ticker or descriptive label.
    option_type : str
        ``'call'``, ``'put'``, or ``'stock'``.
    strike : float
        Strike price (ignored for stock).
    T : float
        Time to expiry in years (ignored for stock).
    sigma : float
        Implied volatility (ignored for stock).
    quantity : int
        Signed: positive = long, negative = short.
    multiplier : float
        Contract multiplier (default 100 for equity options).
    """
    instrument: str
    option_type: str          # "call" | "put" | "stock"
    strike: float = 0.0
    T: float = 0.0
    sigma: float = 0.0
    quantity: int = 1
    multiplier: float = 100.0


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

@dataclass
class PortfolioValuation:
    """Snapshot of a portfolio's value and risk."""
    total_value: float = 0.0
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    total_rho: float = 0.0
    positions: List[Dict] = field(default_factory=list)  # per-position breakdown


class Portfolio:
    """Collection of positions with aggregation methods."""

    def __init__(self, positions: Optional[List[Position]] = None) -> None:
        self.positions: List[Position] = positions or []

    def add(self, pos: Position) -> None:
        self.positions.append(pos)

    def valuate(self, S: float, r: float, q: float = 0.0) -> PortfolioValuation:
        """Mark-to-market all positions and aggregate Greeks.

        Parameters
        ----------
        S : float
            Current spot price.
        r : float
            Risk-free rate.
        q : float
            Dividend yield.

        Returns
        -------
        PortfolioValuation
        """
        val = PortfolioValuation()
        for pos in self.positions:
            entry: Dict = {
                "instrument": pos.instrument,
                "type": pos.option_type,
                "quantity": pos.quantity,
            }

            if pos.option_type == "stock":
                px = S * pos.quantity * pos.multiplier
                entry.update(value=px, delta=pos.quantity * pos.multiplier,
                             gamma=0.0, theta=0.0, vega=0.0, rho=0.0)
                val.total_value += px
                val.total_delta += pos.quantity * pos.multiplier
            else:
                opt = OptionType(pos.option_type)
                px = black_scholes_price(
                    S, pos.strike, pos.T, r, pos.sigma, opt, q, validate=False,
                )
                greeks = analytical_greeks(
                    S, pos.strike, pos.T, r, pos.sigma, opt, q,
                )
                notional = pos.quantity * pos.multiplier
                entry.update(
                    strike=pos.strike, T=pos.T, sigma=pos.sigma,
                    value=px * notional,
                    delta=greeks.delta * notional,
                    gamma=greeks.gamma * notional,
                    theta=greeks.theta * notional,
                    vega=greeks.vega * notional,
                    rho=greeks.rho * notional,
                )
                val.total_value += px * notional
                val.total_delta += greeks.delta * notional
                val.total_gamma += greeks.gamma * notional
                val.total_theta += greeks.theta * notional
                val.total_vega += greeks.vega * notional
                val.total_rho += greeks.rho * notional

            val.positions.append(entry)

        logger.info(
            "Portfolio valued: %d positions, total=%.2f, delta=%.2f, gamma=%.4f",
            len(self.positions), val.total_value, val.total_delta, val.total_gamma,
        )
        return val
