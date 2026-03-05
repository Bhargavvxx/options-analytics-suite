"""
Strategy pricing — prices every leg through the analytics engine.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from analytics.pricing import OptionType, black_scholes_price
from strategies.definitions import (
    LegSide,
    LegType,
    StrategyDefinition,
    StrategyLeg,
    STRATEGY_CATALOG,
)


def _leg_price(
    leg: StrategyLeg,
    S: float,
    K_base: float,
    T: float,
    r: float,
    sigma: float,
    q: float,
) -> float:
    """Price a single leg."""
    K = K_base * leg.strike_offset
    sign = 1.0 if leg.side is LegSide.LONG else -1.0

    if leg.leg_type is LegType.STOCK:
        return sign * S * leg.quantity

    opt_type = OptionType.CALL if leg.leg_type is LegType.CALL else OptionType.PUT
    unit_price = black_scholes_price(S, K, T, r, sigma, opt_type, q, validate=False)
    return sign * unit_price * leg.quantity


def price_strategy(
    definition: StrategyDefinition,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
) -> float:
    """Net entry cost for an entire strategy.

    A positive value means the trader **pays** to enter (debit);
    a negative value means the trader **receives** premium (credit).
    """
    return sum(_leg_price(leg, S, K, T, r, sigma, q) for leg in definition.legs)


def price_all_strategies(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
) -> Dict[str, float]:
    """Price every strategy in the catalog.

    Returns ``{strategy_name: net_entry_cost}``.
    """
    return {
        defn.name: price_strategy(defn, S, K, T, r, sigma, q)
        for defn in STRATEGY_CATALOG.values()
    }


# ---------------------------------------------------------------------------
# Expiration payoff
# ---------------------------------------------------------------------------

def strategy_payoff(
    definition: StrategyDefinition,
    S_range: np.ndarray,
    K: float,
    entry_cost: float,
) -> np.ndarray:
    """Payoff at expiration across a range of spot prices.

    Parameters
    ----------
    S_range : np.ndarray
        Array of underlying prices at expiry.
    K : float
        Base strike used to compute leg strikes.
    entry_cost : float
        Net debit/credit from ``price_strategy()``.

    Returns
    -------
    np.ndarray
        Profit / loss at each underlying price.
    """
    payoff = np.zeros_like(S_range, dtype=np.float64)

    for leg in definition.legs:
        K_leg = K * leg.strike_offset
        sign = 1.0 if leg.side is LegSide.LONG else -1.0

        if leg.leg_type is LegType.STOCK:
            payoff += sign * S_range * leg.quantity
        elif leg.leg_type is LegType.CALL:
            payoff += sign * np.maximum(S_range - K_leg, 0.0) * leg.quantity
        elif leg.leg_type is LegType.PUT:
            payoff += sign * np.maximum(K_leg - S_range, 0.0) * leg.quantity

    payoff -= entry_cost
    return payoff
