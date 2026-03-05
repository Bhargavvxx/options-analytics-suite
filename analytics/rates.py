"""
Interest-rate term structure — zero-rate curve with interpolation.

Provides:
* ``RateCurve`` — piecewise-linear interpolation on continuously-compounded
  zero rates, with discount factor and forward rate extraction.
* Flat curve factory for quick construction.

Conventions
~~~~~~~~~~~
* Rates are continuously compounded decimals (0.05 = 5 %).
* Time is in years (ACT/365 unless stated otherwise).
* Discount factor: df(T) = exp(-z(T) × T).
* Instantaneous forward: f(T) = z(T) + T × z'(T).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

import numpy as np

from config.logging_config import get_logger

logger = get_logger(__name__)

ArrayLike = Union[float, np.ndarray]


# ---------------------------------------------------------------------------
# Rate curve
# ---------------------------------------------------------------------------

@dataclass
class RateCurve:
    """Piecewise-linear zero-rate curve.

    Parameters
    ----------
    pillars : sequence of float
        Maturities in years (must be strictly increasing, pillar[0] > 0).
    rates : sequence of float
        Continuously-compounded zero rates at each pillar.
    label : str
        Human-friendly label (e.g. "USD OIS 2024-12").
    """
    pillars: np.ndarray
    rates: np.ndarray
    label: str = "flat"

    def __post_init__(self) -> None:
        self.pillars = np.asarray(self.pillars, dtype=float)
        self.rates = np.asarray(self.rates, dtype=float)
        if len(self.pillars) != len(self.rates):
            raise ValueError("pillars and rates must have the same length")
        if len(self.pillars) == 0:
            raise ValueError("Need at least one pillar")

    # ---- interpolation ----

    def zero_rate(self, T: ArrayLike) -> ArrayLike:
        """Interpolated continuously-compounded zero rate at maturity *T*.

        Flat extrapolation outside the pillar range.
        """
        return np.interp(T, self.pillars, self.rates)

    def df(self, T: ArrayLike) -> ArrayLike:
        """Discount factor(s) at maturity *T*:  exp(-z(T) × T)."""
        T_arr = np.asarray(T, dtype=float)
        z = self.zero_rate(T_arr)
        result = np.exp(-z * T_arr)
        return float(result) if np.ndim(result) == 0 else result

    def forward_rate(self, T1: float, T2: float) -> float:
        """Simply-compounded forward rate between *T1* and *T2*.

        f(T1,T2) = (z2·T2 - z1·T1) / (T2 - T1)
        """
        if T2 <= T1:
            raise ValueError(f"T2 ({T2}) must be > T1 ({T1})")
        z1, z2 = float(self.zero_rate(T1)), float(self.zero_rate(T2))
        return (z2 * T2 - z1 * T1) / (T2 - T1)

    def shift(self, bp: float) -> "RateCurve":
        """Return a new curve parallel-shifted by *bp* basis points."""
        return RateCurve(
            pillars=self.pillars.copy(),
            rates=self.rates + bp / 10_000.0,
            label=f"{self.label} +{bp}bp",
        )


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def flat_curve(rate: float, label: str = "flat") -> RateCurve:
    """Create a flat (constant) zero-rate curve."""
    pillars = np.array([0.01, 1.0, 5.0, 10.0, 30.0])
    rates = np.full_like(pillars, rate)
    return RateCurve(pillars=pillars, rates=rates, label=label)


def build_curve(
    pillars: Sequence[float],
    rates: Sequence[float],
    label: str = "custom",
) -> RateCurve:
    """Construct a curve from user-supplied pillars and rates."""
    return RateCurve(
        pillars=np.asarray(pillars, dtype=float),
        rates=np.asarray(rates, dtype=float),
        label=label,
    )
