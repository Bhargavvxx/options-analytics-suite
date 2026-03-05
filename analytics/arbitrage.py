"""
Surface arbitrage diagnostics — calendar-spread and butterfly checks.

Static no-arbitrage conditions on an IV surface:

1. **Calendar-spread**: total variance w(T, k) = σ²(T, k) × T must be
   non-decreasing in T for every fixed log-moneyness k.
   Violation ⟹ free calendar spread.

2. **Butterfly**: call prices must be convex in strike (equivalently, the
   second discrete difference of BS call prices w.r.t. K must be ≥ 0).
   Violation ⟹ free butterfly.

Both checks are run on the interpolated grid of an ``IVSurface`` and
produce a structured ``SurfaceArbitrageReport``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from analytics.pricing import OptionType, black_scholes_price
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Report containers
# ---------------------------------------------------------------------------

@dataclass
class ArbitrageViolation:
    """Single arbitrage violation on the grid."""
    kind: str         # "calendar" | "butterfly"
    strike_idx: int
    time_idx: int
    strike: float
    T: float
    severity: float   # negative gap (calendar) or negative 2nd-diff (butterfly)


@dataclass
class SurfaceArbitrageReport:
    """Aggregate report from arbitrage diagnostics."""
    calendar_violations: int = 0
    butterfly_violations: int = 0
    total_grid_points: int = 0
    calendar_violation_pct: float = 0.0
    butterfly_violation_pct: float = 0.0
    max_calendar_severity: float = 0.0
    max_butterfly_severity: float = 0.0
    violations: List[ArbitrageViolation] = field(default_factory=list)
    calendar_mask: Optional[np.ndarray] = None   # bool grid (time × strike)
    butterfly_mask: Optional[np.ndarray] = None  # bool grid (time × strike)


# ---------------------------------------------------------------------------
# Calendar-spread check
# ---------------------------------------------------------------------------

def _check_calendar_arbitrage(
    iv_grid: np.ndarray,
    time_grid: np.ndarray,
    strike_grid: np.ndarray,
    tol: float = -1e-10,
) -> Tuple[np.ndarray, List[ArbitrageViolation], float]:
    """Check that total variance is non-decreasing in T for each strike.

    Parameters
    ----------
    iv_grid : (n_time, n_strike) array of implied vols
    time_grid : (n_time, n_strike) meshgrid of T values
    strike_grid : (n_time, n_strike) meshgrid of strikes
    tol : negative threshold below which a decrease is flagged

    Returns
    -------
    mask : bool array, True where violation occurs
    violations : list of ArbitrageViolation
    max_severity : worst negative gap
    """
    # total variance surface
    w = iv_grid ** 2 * time_grid  # σ²·T

    # Forward differences along the T axis (axis=0)
    dw = np.diff(w, axis=0)  # shape (n_time-1, n_strike)

    mask_inner = dw < tol
    # Expand mask back to full grid shape with False for first row
    mask = np.zeros_like(iv_grid, dtype=bool)
    mask[1:, :] = mask_inner

    violations: List[ArbitrageViolation] = []
    max_sev = 0.0
    for ti, ki in zip(*np.where(mask_inner)):
        sev = float(dw[ti, ki])
        if abs(sev) > abs(max_sev):
            max_sev = sev
        violations.append(ArbitrageViolation(
            kind="calendar",
            strike_idx=ki,
            time_idx=ti + 1,  # offset by 1 because diff reduces axis
            strike=float(strike_grid[ti + 1, ki]),
            T=float(time_grid[ti + 1, ki]),
            severity=sev,
        ))

    return mask, violations, max_sev


# ---------------------------------------------------------------------------
# Butterfly check
# ---------------------------------------------------------------------------

def _check_butterfly_arbitrage(
    iv_grid: np.ndarray,
    strike_grid: np.ndarray,
    time_grid: np.ndarray,
    S: float,
    r: float,
    q: float = 0.0,
    tol: float = -1e-8,
) -> Tuple[np.ndarray, List[ArbitrageViolation], float]:
    """Check convexity of call prices in strike for each expiry row.

    For each row (fixed T), compute BS call prices from IV, then check
    that the discrete second difference  C(K-dK) - 2C(K) + C(K+dK) ≥ 0.

    Returns
    -------
    mask : bool grid, True where violation occurs
    violations : list of ArbitrageViolation
    max_severity : worst negative second difference
    """
    n_time, n_strike = iv_grid.shape
    mask = np.zeros_like(iv_grid, dtype=bool)
    violations: List[ArbitrageViolation] = []
    max_sev = 0.0

    for ti in range(n_time):
        T_val = float(time_grid[ti, 0])
        if T_val <= 0:
            continue
        strikes = strike_grid[ti, :]
        ivs = iv_grid[ti, :]

        # Compute call prices across strikes for this expiry
        valid = ~np.isnan(ivs) & (ivs > 0)
        if valid.sum() < 3:
            continue

        prices = np.full(n_strike, np.nan)
        prices[valid] = black_scholes_price(
            S, strikes[valid], T_val, r, ivs[valid],
            option_type=OptionType.CALL, q=q, validate=False,
        )

        # Second discrete difference
        for ki in range(1, n_strike - 1):
            if np.isnan(prices[ki - 1]) or np.isnan(prices[ki]) or np.isnan(prices[ki + 1]):
                continue
            d2 = prices[ki - 1] - 2.0 * prices[ki] + prices[ki + 1]
            if d2 < tol:
                mask[ti, ki] = True
                sev = float(d2)
                if abs(sev) > abs(max_sev):
                    max_sev = sev
                violations.append(ArbitrageViolation(
                    kind="butterfly",
                    strike_idx=ki,
                    time_idx=ti,
                    strike=float(strikes[ki]),
                    T=T_val,
                    severity=sev,
                ))

    return mask, violations, max_sev


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def surface_arbitrage_check(
    iv_grid: np.ndarray,
    strike_grid: np.ndarray,
    time_grid: np.ndarray,
    S: float,
    r: float,
    q: float = 0.0,
) -> SurfaceArbitrageReport:
    """Run calendar and butterfly arbitrage diagnostics on an IV surface.

    Parameters
    ----------
    iv_grid : (n_time, n_strike) array — implied vols
    strike_grid : (n_time, n_strike) meshgrid of strikes
    time_grid : (n_time, n_strike) meshgrid of T values
    S : float — current spot
    r : float — risk-free rate
    q : float — dividend yield

    Returns
    -------
    SurfaceArbitrageReport
    """
    total = iv_grid.size
    report = SurfaceArbitrageReport(total_grid_points=total)

    # Calendar
    cal_mask, cal_viols, cal_max = _check_calendar_arbitrage(
        iv_grid, time_grid, strike_grid,
    )
    report.calendar_mask = cal_mask
    report.calendar_violations = len(cal_viols)
    report.max_calendar_severity = cal_max
    if total > 0:
        report.calendar_violation_pct = len(cal_viols) / total * 100.0

    # Butterfly
    but_mask, but_viols, but_max = _check_butterfly_arbitrage(
        iv_grid, strike_grid, time_grid, S, r, q,
    )
    report.butterfly_mask = but_mask
    report.butterfly_violations = len(but_viols)
    report.max_butterfly_severity = but_max
    if total > 0:
        report.butterfly_violation_pct = len(but_viols) / total * 100.0

    report.violations = cal_viols + but_viols

    logger.info(
        "Arbitrage check: calendar=%d (%.1f%%), butterfly=%d (%.1f%%) on %d grid points",
        report.calendar_violations, report.calendar_violation_pct,
        report.butterfly_violations, report.butterfly_violation_pct,
        total,
    )
    return report
