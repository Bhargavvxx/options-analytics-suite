"""
Implied-volatility solvers — production-grade.

Features
~~~~~~~~
* **Newton-Raphson** with analytical vega for fast convergence.
* **Bisection** as a safe fallback.
* **Brent's method** (scipy) as a third-tier fallback.
* Arbitrage-bounds check *before* solving (rejects impossible prices).
* Near-zero vega guard to prevent Newton blow-up.
* Structured ``IVResult`` output with convergence diagnostics.
* Batch solver for full option chains.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Union

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from analytics.pricing import OptionType, black_scholes_price, _d1d2
from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
_CFG = Settings()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class IVMethod(str, Enum):
    NEWTON = "newton"
    BISECTION = "bisection"
    BRENT = "brent"


@dataclass(frozen=True, slots=True)
class IVResult:
    """Structured output from an IV solve."""
    iv: Optional[float]          # None if non-convergent
    converged: bool
    iterations: int
    method: IVMethod
    error: float                 # absolute price error at solution
    message: str = ""


# ---------------------------------------------------------------------------
# Arbitrage bounds
# ---------------------------------------------------------------------------

def _arbitrage_bounds(
    S: float, K: float, T: float, r: float, q: float,
    option_type: OptionType,
) -> tuple[float, float]:
    """Return (lower, upper) no-arbitrage price bounds for a European option.

    Any market price outside these bounds is impossible under BSM and the
    solver should refuse to run.
    """
    disc_K = K * math.exp(-r * T)
    disc_S = S * math.exp(-q * T)

    if option_type is OptionType.CALL:
        lower = max(disc_S - disc_K, 0.0)
        upper = disc_S
    else:
        lower = max(disc_K - disc_S, 0.0)
        upper = disc_K

    return lower, upper


# ---------------------------------------------------------------------------
# Vega helper
# ---------------------------------------------------------------------------

def _bs_vega(S: float, K: float, T: float, r: float, sigma: float, q: float) -> float:
    """Raw vega (not per 1 pp) = dV/dσ used inside Newton iterations."""
    T = max(T, _CFG.min_time_to_expiry)
    d1, _ = _d1d2(S, K, T, r, sigma, q)
    return S * math.exp(-q * T) * math.sqrt(T) * float(norm.pdf(d1))


# ---------------------------------------------------------------------------
# Newton-Raphson
# ---------------------------------------------------------------------------

def _newton_iv(
    target: float,
    S: float, K: float, T: float, r: float,
    option_type: OptionType, q: float,
    x0: float = 0.25,
    tol: float | None = None,
    max_iter: int | None = None,
) -> IVResult:
    tol = tol or _CFG.iv_newton_tol
    max_iter = max_iter or _CFG.iv_newton_max_iter
    sigma = x0

    for i in range(1, max_iter + 1):
        price = black_scholes_price(S, K, T, r, sigma, option_type, q, validate=False)
        diff = price - target
        if abs(diff) < tol:
            return IVResult(iv=sigma, converged=True, iterations=i,
                            method=IVMethod.NEWTON, error=abs(diff))
        vega = _bs_vega(S, K, T, r, sigma, q)
        if abs(vega) < 1e-12:
            # Near-zero vega: Newton is unstable, bail out
            logger.debug("Newton: near-zero vega at σ=%.6f, aborting", sigma)
            break
        sigma -= diff / vega
        # Clamp to valid range
        sigma = max(sigma, _CFG.iv_low_bound)
        sigma = min(sigma, _CFG.iv_high_bound)

    return IVResult(iv=None, converged=False, iterations=max_iter,
                    method=IVMethod.NEWTON, error=abs(diff),
                    message="Newton did not converge")


# ---------------------------------------------------------------------------
# Bisection
# ---------------------------------------------------------------------------

def _bisection_iv(
    target: float,
    S: float, K: float, T: float, r: float,
    option_type: OptionType, q: float,
    lo: float | None = None,
    hi: float | None = None,
    tol: float | None = None,
    max_iter: int | None = None,
) -> IVResult:
    lo = lo or _CFG.iv_low_bound
    hi = hi or _CFG.iv_high_bound
    tol = tol or _CFG.iv_bisection_tol
    max_iter = max_iter or _CFG.iv_bisection_max_iter

    for i in range(1, max_iter + 1):
        mid = (lo + hi) / 2.0
        price = black_scholes_price(S, K, T, r, mid, option_type, q, validate=False)
        diff = price - target
        if abs(diff) < tol:
            return IVResult(iv=mid, converged=True, iterations=i,
                            method=IVMethod.BISECTION, error=abs(diff))
        if diff > 0:
            hi = mid
        else:
            lo = mid

    mid = (lo + hi) / 2.0
    final_err = abs(black_scholes_price(S, K, T, r, mid, option_type, q, validate=False) - target)
    return IVResult(iv=mid if final_err < 0.01 else None,
                    converged=False, iterations=max_iter,
                    method=IVMethod.BISECTION, error=final_err,
                    message="Bisection did not converge")


# ---------------------------------------------------------------------------
# Brent
# ---------------------------------------------------------------------------

def _brent_iv(
    target: float,
    S: float, K: float, T: float, r: float,
    option_type: OptionType, q: float,
    lo: float | None = None,
    hi: float | None = None,
    tol: float | None = None,
    max_iter: int | None = None,
) -> IVResult:
    lo = lo or _CFG.iv_low_bound
    hi = hi or _CFG.iv_high_bound
    tol = tol or _CFG.iv_brent_tol
    max_iter = max_iter or _CFG.iv_brent_max_iter

    def objective(sigma: float) -> float:
        return black_scholes_price(S, K, T, r, sigma, option_type, q, validate=False) - target

    try:
        iv, result = brentq(objective, lo, hi, xtol=tol, maxiter=max_iter, full_output=True)
        return IVResult(
            iv=float(iv), converged=result.converged,
            iterations=result.iterations, method=IVMethod.BRENT,
            error=abs(objective(iv)),
        )
    except ValueError as exc:
        return IVResult(iv=None, converged=False, iterations=0,
                        method=IVMethod.BRENT, error=float("inf"),
                        message=str(exc))


# ---------------------------------------------------------------------------
# Public API — single solve
# ---------------------------------------------------------------------------

def solve_iv(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType | str = OptionType.CALL,
    q: float = 0.0,
    *,
    initial_guess: float = 0.25,
) -> IVResult:
    """Solve for implied volatility with cascading solvers.

    Order: Newton-Raphson → Bisection → Brent.

    Rejects market prices outside no-arbitrage bounds.

    Parameters
    ----------
    market_price : float
        Observed option mid-price.
    S, K, T, r, q : float
        Standard BS inputs.
    option_type : OptionType or str
    initial_guess : float
        Starting sigma for Newton.

    Returns
    -------
    IVResult
        Structured result with ``iv``, ``converged``, ``iterations``,
        ``method``, ``error``, and ``message``.
    """
    option_type = OptionType(option_type)

    if market_price <= 0:
        return IVResult(iv=None, converged=False, iterations=0,
                        method=IVMethod.NEWTON, error=float("inf"),
                        message=f"Market price must be positive, got {market_price}")

    lo_bound, hi_bound = _arbitrage_bounds(S, K, T, r, q, option_type)
    if market_price < lo_bound - 1e-6:
        return IVResult(
            iv=None, converged=False, iterations=0,
            method=IVMethod.NEWTON, error=float("inf"),
            message=f"Price {market_price:.4f} below arbitrage lower bound {lo_bound:.4f}",
        )
    if market_price > hi_bound + 1e-6:
        return IVResult(
            iv=None, converged=False, iterations=0,
            method=IVMethod.NEWTON, error=float("inf"),
            message=f"Price {market_price:.4f} above arbitrage upper bound {hi_bound:.4f}",
        )

    # Tier 1: Newton
    result = _newton_iv(market_price, S, K, T, r, option_type, q, x0=initial_guess)
    if result.converged:
        return result

    # Tier 2: Bisection
    logger.info("Newton failed for S=%.2f K=%.2f T=%.4f; trying bisection", S, K, T)
    result = _bisection_iv(market_price, S, K, T, r, option_type, q)
    if result.converged:
        return result

    # Tier 3: Brent
    logger.info("Bisection failed; trying Brent for S=%.2f K=%.2f T=%.4f", S, K, T)
    return _brent_iv(market_price, S, K, T, r, option_type, q)


# ---------------------------------------------------------------------------
# Public API — batch solve
# ---------------------------------------------------------------------------

def batch_solve_iv(
    market_prices: Sequence[float],
    strikes: Sequence[float],
    S: float,
    T: float,
    r: float,
    option_type: OptionType | str = OptionType.CALL,
    q: float = 0.0,
) -> List[IVResult]:
    """Solve IV for an entire option chain.

    Parameters
    ----------
    market_prices, strikes : sequence of float
        Parallel arrays of prices and strikes.
    S, T, r, q : float
        Common parameters for the chain.

    Returns
    -------
    list[IVResult]
        One ``IVResult`` per strike.
    """
    option_type = OptionType(option_type)
    results: List[IVResult] = []
    for price, K in zip(market_prices, strikes):
        results.append(solve_iv(price, S, K, T, r, option_type, q))
    return results
