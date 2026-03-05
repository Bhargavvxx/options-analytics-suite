"""
Black-Scholes European option pricing — production-grade.

Responsibilities
~~~~~~~~~~~~~~~~
* Price a single European call or put (scalar or vectorised).
* Put-call parity verification.
* Strict input validation and edge-case handling.
* **No** Greeks or IV logic — those live in dedicated modules.

Conventions
~~~~~~~~~~~
* *T* is in years (use ``analytics.day_count.year_fraction`` upstream).
* Continuous dividend yield *q*.
* All rates / vols expressed as decimals (0.05 = 5 %).
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Union

import numpy as np
from scipy.stats import norm

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)

# Module-level default settings (can be overridden by callers)
_CFG = Settings()

ArrayLike = Union[float, np.ndarray]


# ---------------------------------------------------------------------------
# Option type enum
# ---------------------------------------------------------------------------

class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_inputs(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    sigma: ArrayLike,
) -> None:
    """Raise ``ValueError`` for unphysical inputs."""
    S_arr = np.asarray(S)
    K_arr = np.asarray(K)
    T_arr = np.asarray(T)
    sigma_arr = np.asarray(sigma)

    if np.any(S_arr <= 0):
        raise ValueError(f"Spot price S must be positive; got min={S_arr.min()}")
    if np.any(K_arr <= 0):
        raise ValueError(f"Strike K must be positive; got min={K_arr.min()}")
    if np.any(T_arr < 0):
        raise ValueError(f"Time to expiry T must be non-negative; got min={T_arr.min()}")
    if np.any(sigma_arr <= 0):
        raise ValueError(f"Volatility sigma must be positive; got min={sigma_arr.min()}")


# ---------------------------------------------------------------------------
# Core d1 / d2
# ---------------------------------------------------------------------------

def _d1d2(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    r: ArrayLike,
    sigma: ArrayLike,
    q: ArrayLike,
) -> tuple[ArrayLike, ArrayLike]:
    """Return (d1, d2) for the Black-Scholes formula.

    *T* is floored at ``Settings.min_time_to_expiry`` to avoid division by
    zero without silently changing the caller's semantics.
    """
    T = np.maximum(T, _CFG.min_time_to_expiry)
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def black_scholes_price(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    r: ArrayLike,
    sigma: ArrayLike,
    option_type: OptionType | str = OptionType.CALL,
    q: ArrayLike = 0.0,
    *,
    validate: bool = True,
) -> ArrayLike:
    """Black-Scholes European option price.

    Parameters
    ----------
    S : float or array
        Spot price(s).
    K : float or array
        Strike price(s).
    T : float or array
        Time to expiry in **years**.
    r : float or array
        Continuously-compounded risk-free rate (decimal).
    sigma : float or array
        Annualised volatility (decimal).
    option_type : OptionType or str
        ``'call'`` or ``'put'``.
    q : float or array
        Continuous dividend yield (decimal).
    validate : bool
        If *True* run input checks (disable for inner-loop performance).

    Returns
    -------
    float or np.ndarray
        Option price(s).
    """
    option_type = OptionType(option_type)

    if validate:
        _validate_inputs(S, K, T, sigma)

    d1, d2 = _d1d2(S, K, T, r, sigma, q)

    disc_S = S * np.exp(-q * T)
    disc_K = K * np.exp(-r * T)

    if option_type is OptionType.CALL:
        price = disc_S * norm.cdf(d1) - disc_K * norm.cdf(d2)
    else:
        price = disc_K * norm.cdf(-d2) - disc_S * norm.cdf(-d1)

    return float(price) if np.ndim(price) == 0 else price


# ---------------------------------------------------------------------------
# Put-call parity
# ---------------------------------------------------------------------------

def put_call_parity_check(
    call_price: float,
    put_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    tol: float = 0.01,
) -> dict:
    """Check put-call parity: C - P = S·e^{-qT} - K·e^{-rT}.

    Returns a dict with the *lhs*, *rhs*, *difference*, and a bool
    *satisfied* (within *tol*).
    """
    lhs = call_price - put_price
    rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    diff = abs(lhs - rhs)
    return {
        "lhs": lhs,
        "rhs": rhs,
        "difference": diff,
        "satisfied": diff <= tol,
    }
