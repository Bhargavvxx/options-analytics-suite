"""
Strategy definitions as composable leg structures.

Every strategy is described declaratively as a list of ``StrategyLeg``
objects.  This makes pricing, payoff calculation, and backtesting all
derive from a single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class LegSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class LegType(str, Enum):
    CALL = "call"
    PUT = "put"
    STOCK = "stock"


@dataclass(frozen=True, slots=True)
class StrategyLeg:
    """One leg of a multi-leg options strategy.

    ``strike_offset`` is a **multiplier** applied to the base strike K.
    E.g. 1.0 = ATM, 1.1 = 10 % OTM call / 10 % ITM put, etc.
    """
    side: LegSide
    leg_type: LegType
    strike_offset: float = 1.0
    quantity: int = 1


@dataclass(frozen=True)
class StrategyDefinition:
    """Named collection of legs."""
    name: str
    legs: List[StrategyLeg]
    description: str = ""


# ---------------------------------------------------------------------------
# Catalog of pre-built strategies
# ---------------------------------------------------------------------------

STRATEGY_CATALOG: Dict[str, StrategyDefinition] = {
    "long_call": StrategyDefinition(
        name="Long Call",
        legs=[StrategyLeg(LegSide.LONG, LegType.CALL, 1.0)],
        description="Bullish directional bet.",
    ),
    "long_put": StrategyDefinition(
        name="Long Put",
        legs=[StrategyLeg(LegSide.LONG, LegType.PUT, 1.0)],
        description="Bearish directional bet.",
    ),
    "straddle": StrategyDefinition(
        name="Straddle",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.CALL, 1.0),
            StrategyLeg(LegSide.LONG, LegType.PUT, 1.0),
        ],
        description="Long vol: profit from large move in either direction.",
    ),
    "strangle": StrategyDefinition(
        name="Strangle",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.CALL, 1.10),
            StrategyLeg(LegSide.LONG, LegType.PUT, 0.90),
        ],
        description="Cheaper vol bet with wider breakevens.",
    ),
    "bull_call_spread": StrategyDefinition(
        name="Bull Call Spread",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.CALL, 1.0),
            StrategyLeg(LegSide.SHORT, LegType.CALL, 1.10),
        ],
        description="Moderately bullish with capped risk and reward.",
    ),
    "bear_put_spread": StrategyDefinition(
        name="Bear Put Spread",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.PUT, 1.0),
            StrategyLeg(LegSide.SHORT, LegType.PUT, 0.90),
        ],
        description="Moderately bearish with capped risk and reward.",
    ),
    "butterfly": StrategyDefinition(
        name="Butterfly",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.CALL, 0.90),
            StrategyLeg(LegSide.SHORT, LegType.CALL, 1.0, quantity=2),
            StrategyLeg(LegSide.LONG, LegType.CALL, 1.10),
        ],
        description="Profit from low realised vol around strike.",
    ),
    "iron_condor": StrategyDefinition(
        name="Iron Condor",
        legs=[
            StrategyLeg(LegSide.SHORT, LegType.PUT, 0.90),
            StrategyLeg(LegSide.LONG, LegType.PUT, 0.85),
            StrategyLeg(LegSide.SHORT, LegType.CALL, 1.10),
            StrategyLeg(LegSide.LONG, LegType.CALL, 1.15),
        ],
        description="Short vol: profit from range-bound market.",
    ),
    "protective_put": StrategyDefinition(
        name="Protective Put",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.STOCK, 1.0),
            StrategyLeg(LegSide.LONG, LegType.PUT, 1.0),
        ],
        description="Downside hedge on long stock position.",
    ),
    "covered_call": StrategyDefinition(
        name="Covered Call",
        legs=[
            StrategyLeg(LegSide.LONG, LegType.STOCK, 1.0),
            StrategyLeg(LegSide.SHORT, LegType.CALL, 1.0),
        ],
        description="Income generation on long stock position.",
    ),
}
