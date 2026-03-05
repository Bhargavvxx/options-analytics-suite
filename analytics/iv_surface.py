"""
Implied-volatility surface construction and diagnostics.

Builds a structured IV surface from option-chain data, with
interpolation for sparse chains and diagnostic metrics for
smile/skew analysis.  Includes a QC report for production use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from analytics.implied_vol import IVResult, solve_iv
from analytics.pricing import OptionType
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class IVSurfacePoint:
    strike: float
    expiry: str
    T: float          # year-fraction
    iv: Optional[float]
    converged: bool
    moneyness: float   # K / S


@dataclass
class SurfaceQC:
    """Quality-control diagnostics for an IV surface build."""
    total_points: int = 0
    converged_points: int = 0
    failed_points: int = 0
    pct_missing: float = 0.0
    used_market_iv: int = 0       # how many used pre-supplied IV
    used_solver: int = 0          # how many needed IV solving
    solver_failures: int = 0
    crossed_markets: int = 0      # bid > ask rows dropped
    wide_spreads: int = 0         # spread > threshold
    expiries_count: int = 0
    min_iv: float = 0.0
    max_iv: float = 0.0
    mean_iv: float = 0.0


@dataclass
class IVSurface:
    """Structured IV surface with metadata."""
    spot: float
    points: List[IVSurfacePoint]
    strike_grid: Optional[np.ndarray] = None
    time_grid: Optional[np.ndarray] = None
    iv_grid: Optional[np.ndarray] = None
    is_market_data: bool = False
    diagnostics: Dict[str, float] = field(default_factory=dict)
    qc: Optional[SurfaceQC] = None


# ---------------------------------------------------------------------------
# Surface builder
# ---------------------------------------------------------------------------

def build_iv_surface(
    option_chains: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]],
    S: float,
    r: float,
    q: float = 0.0,
    option_type: OptionType | str = OptionType.CALL,
    moneyness_range: Tuple[float, float] = (0.7, 1.3),
    use_market_iv: bool = True,
) -> IVSurface:
    """Build an IV surface from multiple expiry option chains.

    Parameters
    ----------
    option_chains : dict
        ``{expiry_str: (calls_df, puts_df)}`` where each DataFrame has
        at least ``'strike'``, ``'lastPrice'`` (or ``'mid'``), and
        optionally ``'impliedVolatility'`` columns.
    S : float
        Current spot price.
    r : float
        Risk-free rate (decimal).
    q : float
        Dividend yield (decimal).
    option_type : OptionType or str
        Which side of the chain to use.
    moneyness_range : tuple
        (lower, upper) K/S filter.
    use_market_iv : bool
        If True and ``'impliedVolatility'`` column exists, use it
        directly instead of re-solving.

    Returns
    -------
    IVSurface
    """
    option_type = OptionType(option_type)
    points: List[IVSurfacePoint] = []
    expiry_list = sorted(option_chains.keys())
    now = datetime.now()

    qc = SurfaceQC(expiries_count=len(expiry_list))

    for expiry_str in expiry_list:
        calls, puts = option_chains[expiry_str]
        chain = calls if option_type is OptionType.CALL else puts
        if chain.empty:
            continue

        try:
            days = (datetime.strptime(expiry_str, "%Y-%m-%d") - now).days
        except ValueError:
            logger.warning("Cannot parse expiry '%s'; skipping", expiry_str)
            continue
        T = max(days, 1) / 365.0

        for _, row in chain.iterrows():
            K = float(row["strike"])
            moneyness = K / S
            if not (moneyness_range[0] <= moneyness <= moneyness_range[1]):
                continue

            qc.total_points += 1

            # Try market-supplied IV first
            iv_val: Optional[float] = None
            converged = False

            if use_market_iv and "impliedVolatility" in row.index:
                mkt_iv = row["impliedVolatility"]
                if pd.notna(mkt_iv) and mkt_iv > 0:
                    iv_val = float(mkt_iv)
                    converged = True
                    qc.used_market_iv += 1

            # Fall back to solving if needed
            if iv_val is None:
                price_col = "mid" if "mid" in row.index else "lastPrice"
                if price_col in row.index and pd.notna(row[price_col]) and row[price_col] > 0:
                    result: IVResult = solve_iv(
                        float(row[price_col]), S, K, T, r, option_type, q
                    )
                    if result.converged and result.iv is not None:
                        iv_val = result.iv
                        converged = True
                        qc.used_solver += 1
                    else:
                        qc.solver_failures += 1

            if iv_val is None:
                qc.failed_points += 1
            else:
                qc.converged_points += 1

            points.append(IVSurfacePoint(
                strike=K, expiry=expiry_str, T=T,
                iv=iv_val, converged=converged, moneyness=moneyness,
            ))

    # Finalise QC stats
    if qc.total_points > 0:
        qc.pct_missing = qc.failed_points / qc.total_points * 100.0
    valid_ivs = [p.iv for p in points if p.iv is not None]
    if valid_ivs:
        qc.min_iv = float(np.min(valid_ivs))
        qc.max_iv = float(np.max(valid_ivs))
        qc.mean_iv = float(np.mean(valid_ivs))

    surface = IVSurface(spot=S, points=points, is_market_data=True, qc=qc)

    # Build interpolated grid if we have enough data
    valid = [p for p in points if p.iv is not None]
    if len(valid) >= 4:
        surface = _interpolate_surface(surface, valid)
        surface.diagnostics = _compute_diagnostics(surface, S)

    logger.info(
        "IV surface built: %d/%d converged (%.1f%% missing), %d market-IV, %d solved, %d failed",
        qc.converged_points, qc.total_points, qc.pct_missing,
        qc.used_market_iv, qc.used_solver, qc.solver_failures,
    )
    return surface


def _interpolate_surface(
    surface: IVSurface,
    valid_points: List[IVSurfacePoint],
) -> IVSurface:
    """Create a regular grid and interpolate sparse IV data."""
    try:
        from scipy.interpolate import griddata
    except ImportError:
        logger.warning("scipy not available for interpolation")
        return surface

    strikes = np.array([p.strike for p in valid_points])
    times = np.array([p.T for p in valid_points])
    ivs = np.array([p.iv for p in valid_points])

    strike_lin = np.linspace(strikes.min(), strikes.max(), 30)
    time_lin = np.linspace(times.min(), times.max(), 20)
    strike_grid, time_grid = np.meshgrid(strike_lin, time_lin)

    iv_grid = griddata(
        np.column_stack([strikes, times]),
        ivs,
        (strike_grid, time_grid),
        method="linear",
    )
    # Fill remaining NaN with nearest
    still_nan = np.isnan(iv_grid)
    if still_nan.any():
        nearest = griddata(
            np.column_stack([strikes, times]),
            ivs,
            (strike_grid[still_nan], time_grid[still_nan]),
            method="nearest",
        )
        iv_grid[still_nan] = nearest

    surface.strike_grid = strike_grid
    surface.time_grid = time_grid
    surface.iv_grid = iv_grid
    return surface


def _compute_diagnostics(surface: IVSurface, S: float) -> Dict[str, float]:
    """Smile / skew diagnostics from the surface."""
    diags: Dict[str, float] = {}
    valid = [p for p in surface.points if p.iv is not None]
    if not valid:
        return diags

    ivs = np.array([p.iv for p in valid])
    moneyness = np.array([p.moneyness for p in valid])

    atm_ivs = [p.iv for p in valid if 0.95 <= p.moneyness <= 1.05]
    if atm_ivs:
        diags["atm_iv"] = float(np.mean(atm_ivs))
    diags["avg_iv"] = float(np.mean(ivs))

    # Skew = Δ(IV) per Δ(moneyness) — simple linear regression
    if len(valid) >= 3:
        coeffs = np.polyfit(moneyness, ivs, 1)
        diags["skew_slope"] = float(coeffs[0])

    # Smile curvature (second-order)
    if len(valid) >= 5:
        coeffs2 = np.polyfit(moneyness, ivs, 2)
        diags["smile_curvature"] = float(coeffs2[0])

    return diags


# ---------------------------------------------------------------------------
# Simulated surface (educational / fallback)
# ---------------------------------------------------------------------------

def simulated_iv_surface(
    S: float,
    base_vol: float = 0.20,
    n_strikes: int = 20,
    n_tenors: int = 20,
) -> IVSurface:
    """Generate a synthetic IV surface with realistic smile / skew.

    Clearly marked as SIMULATED — not market data.
    """
    strikes = np.linspace(0.7 * S, 1.3 * S, n_strikes)
    times = np.linspace(0.1, 2.0, n_tenors)
    strike_grid, time_grid = np.meshgrid(strikes, times)

    # Parametric smile model
    moneyness = strike_grid / S
    skew = -0.10 * (moneyness - 1.0)          # downside skew
    smile = 0.05 * (moneyness - 1.0) ** 2     # curvature
    term = 0.03 * (1 - np.exp(-time_grid))    # term-structure effect
    iv_grid = base_vol + skew + smile + term
    iv_grid = np.clip(iv_grid, 0.01, 2.0)

    return IVSurface(
        spot=S,
        points=[],
        strike_grid=strike_grid,
        time_grid=time_grid,
        iv_grid=iv_grid,
        is_market_data=False,
        diagnostics={"note": "simulated_surface"},
    )
