"""
Option Greeks — analytical closed-form *and* finite-difference validation.

Analytical Greeks
~~~~~~~~~~~~~~~~~
Derived from the Black-Scholes model with continuous dividend yield.
Returned in a ``Greeks`` dataclass so every downstream consumer gets
typed, documented fields.

Finite-Difference Greeks
~~~~~~~~~~~~~~~~~~~~~~~~
Central-difference bumped prices.  Use these to **validate** that the
analytical formulas are correct, or to price Greeks for models that
lack a closed-form Greek.

Convention notes
~~~~~~~~~~~~~~~~
* **Theta** is per *calendar day* (÷365).
* **Vega** is per 1 percentage-point move in vol (÷100).
* **Rho** is per 1 percentage-point move in rate (÷100).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import numpy as np
from scipy.stats import norm

from analytics.pricing import OptionType, black_scholes_price, _d1d2, _CFG

ArrayLike = Union[float, np.ndarray]


# ---------------------------------------------------------------------------
# Greeks data container
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Greeks:
    """Immutable container for the five standard Black-Scholes Greeks."""
    delta: float
    gamma: float
    theta: float   # per calendar day
    vega: float    # per 1 pp vol
    rho: float     # per 1 pp rate


# ---------------------------------------------------------------------------
# Analytical Greeks
# ---------------------------------------------------------------------------

def analytical_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType | str = OptionType.CALL,
    q: float = 0.0,
) -> Greeks:
    """Closed-form Black-Scholes Greeks with continuous dividend yield.

    Parameters match ``black_scholes_price()``.  Returns a ``Greeks``
    instance.
    """
    option_type = OptionType(option_type)
    T = max(T, _CFG.min_time_to_expiry)
    sqrt_T = np.sqrt(T)

    d1, d2 = _d1d2(S, K, T, r, sigma, q)
    exp_qT = np.exp(-q * T)
    exp_rT = np.exp(-r * T)
    pdf_d1 = float(norm.pdf(d1))
    cdf_d1 = float(norm.cdf(d1))
    cdf_d2 = float(norm.cdf(d2))

    # Delta
    if option_type is OptionType.CALL:
        delta = exp_qT * cdf_d1
    else:
        delta = exp_qT * (cdf_d1 - 1.0)

    # Gamma (same for calls and puts)
    gamma = exp_qT * pdf_d1 / (S * sigma * sqrt_T)

    # Theta (per calendar day = annual theta / 365)
    common = -(S * sigma * exp_qT * pdf_d1) / (2.0 * sqrt_T)
    if option_type is OptionType.CALL:
        theta = (common
                 - r * K * exp_rT * cdf_d2
                 + q * S * exp_qT * cdf_d1) / 365.0
    else:
        theta = (common
                 + r * K * exp_rT * float(norm.cdf(-d2))
                 - q * S * exp_qT * float(norm.cdf(-d1))) / 365.0

    # Vega (per 1 pp vol move)
    vega = S * exp_qT * sqrt_T * pdf_d1 / 100.0

    # Rho (per 1 pp rate move)
    if option_type is OptionType.CALL:
        rho = K * T * exp_rT * cdf_d2 / 100.0
    else:
        rho = -K * T * exp_rT * float(norm.cdf(-d2)) / 100.0

    return Greeks(
        delta=float(delta),
        gamma=float(gamma),
        theta=float(theta),
        vega=float(vega),
        rho=float(rho),
    )


# ---------------------------------------------------------------------------
# Finite-difference Greeks (central difference)
# ---------------------------------------------------------------------------

def finite_difference_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType | str = OptionType.CALL,
    q: float = 0.0,
    *,
    dS_rel: float | None = None,
    d_sigma: float | None = None,
    d_r: float | None = None,
    d_T: float | None = None,
) -> Greeks:
    """Central-difference bumped Greeks for validation / non-BS models.

    Parameters
    ----------
    dS_rel : float, optional
        Relative spot bump (default from ``Settings.fd_bump_spot``).
    d_sigma : float, optional
        Absolute vol bump in decimal (default from ``Settings.fd_bump_vol``).
    d_r : float, optional
        Absolute rate bump in decimal (default ``Settings.fd_bump_rate``).
    d_T : float, optional
        Time bump in years (default ``Settings.fd_bump_time``).
    """
    option_type = OptionType(option_type)
    dS_rel = dS_rel or _CFG.fd_bump_spot
    d_sigma = d_sigma or _CFG.fd_bump_vol
    d_r = d_r or _CFG.fd_bump_rate
    d_T = d_T or _CFG.fd_bump_time

    kw = dict(S=S, K=K, T=T, r=r, sigma=sigma, option_type=option_type, q=q, validate=False)
    _price = lambda **overrides: black_scholes_price(**{**kw, **overrides})  # noqa: E731

    dS = S * dS_rel

    # Delta = dV/dS
    delta = (_price(S=S + dS) - _price(S=S - dS)) / (2.0 * dS)

    # Gamma = d²V/dS²
    gamma = (_price(S=S + dS) - 2.0 * _price(S=S) + _price(S=S - dS)) / (dS ** 2)

    # Vega = dV/dσ  (per 1 pp = / 100)
    vega = (_price(sigma=sigma + d_sigma) - _price(sigma=sigma - d_sigma)) / (2.0 * d_sigma) / 100.0

    # Rho = dV/dr  (per 1 pp = / 100)
    rho = (_price(r=r + d_r) - _price(r=r - d_r)) / (2.0 * d_r) / 100.0

    # Theta = -dV/dT  (per calendar day = / 365)
    T_up = max(T + d_T, _CFG.min_time_to_expiry)
    T_dn = max(T - d_T, _CFG.min_time_to_expiry)
    theta = -(_price(T=T_up) - _price(T=T_dn)) / (T_up - T_dn) / 365.0

    return Greeks(
        delta=float(delta),
        gamma=float(gamma),
        theta=float(theta),
        vega=float(vega),
        rho=float(rho),
    )
