"""
SVI (Stochastic Volatility Inspired) smile calibration.

Implements the *raw SVI* parameterisation (Gatheral 2004):

    w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))

where
    k   = log(K/F)  (log-moneyness)
    w   = sigma_BS^2 * T  (total implied variance)

Usage
-----
Fit one smile per expiry, then optionally replace the scattered
market IVs on the ``IVSurface`` with the smooth SVI fit.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SVI parameter container
# ---------------------------------------------------------------------------

@dataclass
class SVIParams:
    """Raw SVI parameters for one expiry slice."""
    a: float       # vertical shift (overall variance level)
    b: float       # slope (≥ 0)
    rho: float     # rotation (-1, 1)
    m: float       # horizontal shift
    sigma: float   # curvature (> 0)
    T: float       # tenor this slice was calibrated to
    rmse: float = 0.0  # root-mean-square error of the fit


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def svi_total_variance(k: np.ndarray, params: SVIParams) -> np.ndarray:
    """Evaluate the raw SVI total variance w(k) = a + b*(rho*(k-m) + sqrt((k-m)^2 + sigma^2))."""
    km = k - params.m
    return params.a + params.b * (params.rho * km + np.sqrt(km ** 2 + params.sigma ** 2))


def svi_implied_vol(k: np.ndarray, params: SVIParams) -> np.ndarray:
    """Convert SVI total variance to Black-Scholes implied vol."""
    w = svi_total_variance(k, params)
    w = np.maximum(w, 1e-8)  # avoid negative variance
    return np.sqrt(w / params.T)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

def _svi_residuals(
    x: np.ndarray,
    k: np.ndarray,
    w_market: np.ndarray,
) -> np.ndarray:
    """Residual vector for least-squares fitting."""
    a, b, rho, m, sigma = x
    km = k - m
    w_model = a + b * (rho * km + np.sqrt(km ** 2 + sigma ** 2))
    return w_model - w_market


def calibrate_svi(
    strikes: np.ndarray,
    ivs: np.ndarray,
    T: float,
    forward: float,
) -> Optional[SVIParams]:
    """Calibrate raw SVI to a single expiry smile slice.

    Parameters
    ----------
    strikes : array
        Strike prices.
    ivs : array
        Market Black-Scholes implied volatilities.
    T : float
        Time to expiry in years.
    forward : float
        Forward price F = S * exp(rT).

    Returns
    -------
    SVIParams or None if calibration fails.
    """
    try:
        from scipy.optimize import least_squares
    except ImportError:
        logger.warning("scipy not available; SVI calibration skipped")
        return None

    if len(strikes) < 5:
        logger.info("Need >= 5 strike/IV pairs for SVI; got %d", len(strikes))
        return None

    k = np.log(strikes / forward)
    w_market = ivs ** 2 * T

    # Initial guess
    a0 = float(np.mean(w_market))
    b0 = 0.1
    rho0 = -0.3
    m0 = 0.0
    sigma0 = 0.1
    x0 = np.array([a0, b0, rho0, m0, sigma0])

    # Bounds: a free, b >= 0, -1 < rho < 1, m free, sigma > 0
    lower = [-np.inf, 1e-8, -0.999, -np.inf, 1e-8]
    upper = [np.inf, np.inf, 0.999, np.inf, np.inf]

    result = least_squares(
        _svi_residuals,
        x0,
        args=(k, w_market),
        bounds=(lower, upper),
        method="trf",
        max_nfev=2000,
    )

    if not result.success:
        logger.warning("SVI calibration did not converge: %s", result.message)
        return None

    a, b, rho, m, sigma = result.x
    rmse = float(np.sqrt(np.mean(result.fun ** 2)))

    return SVIParams(a=a, b=b, rho=rho, m=m, sigma=sigma, T=T, rmse=rmse)


def calibrate_surface_svi(
    points: list,
    spot: float,
    r: float = 0.05,
) -> List[SVIParams]:
    """Calibrate SVI to each expiry slice of an IVSurface's point list.

    Parameters
    ----------
    points : list[IVSurfacePoint]
        Points with ``strike``, ``T``, ``iv``, ``converged``.
    spot : float
    r : float

    Returns
    -------
    List of SVIParams, one per expiry with enough data.
    """
    from collections import defaultdict

    by_expiry: dict[float, Tuple[List[float], List[float]]] = defaultdict(lambda: ([], []))

    for p in points:
        if p.iv is not None and p.converged:
            ks, ivs = by_expiry[p.T]
            ks.append(p.strike)
            ivs.append(p.iv)

    results: List[SVIParams] = []
    for T_val in sorted(by_expiry.keys()):
        ks, ivs = by_expiry[T_val]
        strikes = np.array(ks)
        iv_arr = np.array(ivs)
        forward = spot * np.exp(r * T_val)
        params = calibrate_svi(strikes, iv_arr, T_val, forward)
        if params is not None:
            results.append(params)
            logger.info("SVI fit T=%.3f: a=%.4f b=%.4f rho=%.3f m=%.4f sigma=%.4f RMSE=%.6f",
                         T_val, params.a, params.b, params.rho, params.m, params.sigma, params.rmse)

    return results
