"""
Day-count convention helpers.

Provides explicit year-fraction calculations so that callers never
silently assume ACT/365 vs ACT/252.
"""
from __future__ import annotations

from enum import Enum


class DayCountConvention(Enum):
    ACT_365 = "ACT/365"
    ACT_252 = "ACT/252"


_DIVISOR = {
    DayCountConvention.ACT_365: 365.0,
    DayCountConvention.ACT_252: 252.0,
}


def year_fraction(
    calendar_days: int,
    convention: DayCountConvention = DayCountConvention.ACT_365,
) -> float:
    """Convert *calendar_days* to a year fraction under *convention*.

    Returns
    -------
    float
        Year fraction, floored at 0.0 (never negative).
    """
    divisor = _DIVISOR.get(convention)
    if divisor is None:
        raise ValueError(f"Unsupported convention: {convention}")
    return max(calendar_days, 0) / divisor
