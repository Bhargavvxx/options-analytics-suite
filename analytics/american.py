"""
American option pricing via the Cox-Ross-Rubinstein binomial tree.

Supports:
* European and American exercise (call and put).
* Continuous dividend yield *q*.
* Discrete cash dividends via PV-adjusted spot (escrowed dividend method).

The CRR tree uses the standard parameterisation:
    u = exp(σ √Δt),  d = 1/u,  p = (exp((r-q)Δt) - d) / (u - d)

Tree node prices are stored for early-exercise boundary analysis when
requested, but the default path returns only the root price for speed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np

from analytics.pricing import OptionType
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums / containers
# ---------------------------------------------------------------------------

class ExerciseStyle(str, Enum):
    EUROPEAN = "european"
    AMERICAN = "american"


@dataclass
class DividendSchedule:
    """Discrete cash dividends to be incorporated into the tree.

    Each entry is (time_in_years, cash_amount).  Times must lie within
    the option's life [0, T].
    """
    payments: List[tuple[float, float]]

    @property
    def total(self) -> float:
        return sum(d for _, d in self.payments)

    def pv(self, r: float) -> float:
        """Present value of all future dividends (continuously discounted)."""
        return sum(d * math.exp(-r * t) for t, d in self.payments)


@dataclass
class BinomialResult:
    """Output of binomial pricing."""
    price: float
    exercise_style: str
    option_type: str
    steps: int
    early_exercise_boundary: Optional[np.ndarray] = None  # spot level per step


# ---------------------------------------------------------------------------
# Core CRR implementation
# ---------------------------------------------------------------------------

def binomial_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType | str = OptionType.CALL,
    q: float = 0.0,
    exercise: ExerciseStyle | str = ExerciseStyle.AMERICAN,
    steps: int = 200,
    dividends: Optional[DividendSchedule] = None,
    return_boundary: bool = False,
) -> BinomialResult:
    """Price an option via the CRR binomial tree.

    Parameters
    ----------
    S : float
        Current spot price.
    K : float
        Strike price.
    T : float
        Time to expiry in years.
    r : float
        Continuously-compounded risk-free rate.
    sigma : float
        Annualised volatility.
    option_type : OptionType or str
        ``'call'`` or ``'put'``.
    q : float
        Continuous dividend yield.
    exercise : ExerciseStyle or str
        ``'american'`` or ``'european'``.
    steps : int
        Number of binomial steps (higher = more accurate, slower).
    dividends : DividendSchedule, optional
        Discrete cash dividends.  If provided, *q* should be 0 to avoid
        double-counting.
    return_boundary : bool
        If True, compute and return the early-exercise boundary.

    Returns
    -------
    BinomialResult
    """
    option_type = OptionType(option_type)
    exercise = ExerciseStyle(exercise)

    if S <= 0 or K <= 0 or sigma <= 0:
        raise ValueError("S, K, sigma must be positive")
    T = max(T, 1e-10)

    # Subtract PV of discrete dividends from spot (escrowed dividend method)
    S_adj = S
    if dividends is not None and dividends.payments:
        S_adj = S - dividends.pv(r)
        S_adj = max(S_adj, 1e-10)

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    p_up = (math.exp((r - q) * dt) - d) / (u - d)
    p_up = max(0.0, min(1.0, p_up))  # clamp for numerical safety
    p_dn = 1.0 - p_up

    is_call = option_type is OptionType.CALL
    is_american = exercise is ExerciseStyle.AMERICAN

    # Terminal spot prices  (step N)
    spots = S_adj * u ** np.arange(steps, -1, -1) * d ** np.arange(0, steps + 1, 1)

    # Terminal payoffs
    if is_call:
        values = np.maximum(spots - K, 0.0)
    else:
        values = np.maximum(K - spots, 0.0)

    # Early exercise boundary tracking
    boundary: Optional[np.ndarray] = None
    if return_boundary and is_american:
        boundary = np.full(steps + 1, np.nan)
        # At terminal step, find the critical spot
        ex_mask = values > 0
        if ex_mask.any():
            boundary[steps] = float(spots[ex_mask][0] if is_call else spots[ex_mask][-1])

    # Backward induction
    for i in range(steps - 1, -1, -1):
        spots_i = S_adj * u ** np.arange(i, -1, -1) * d ** np.arange(0, i + 1, 1)
        values = disc * (p_up * values[:-1] + p_dn * values[1:])

        if is_american:
            if is_call:
                intrinsic = np.maximum(spots_i - K, 0.0)
            else:
                intrinsic = np.maximum(K - spots_i, 0.0)
            values = np.maximum(values, intrinsic)

            if return_boundary and boundary is not None:
                ex_mask = intrinsic >= values
                if ex_mask.any():
                    boundary[i] = float(spots_i[ex_mask][0] if is_call else spots_i[ex_mask][-1])

    price = float(values[0])

    logger.debug(
        "Binomial %s %s: S=%.2f K=%.2f T=%.4f σ=%.4f → %.6f (%d steps)",
        exercise.value, option_type.value, S, K, T, sigma, price, steps,
    )

    return BinomialResult(
        price=price,
        exercise_style=exercise.value,
        option_type=option_type.value,
        steps=steps,
        early_exercise_boundary=boundary,
    )
