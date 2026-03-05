"""
Volatility analytics — realised, EWMA, GARCH, regime detection.

Every function clearly documents whether the output is **daily** or
**annualised**, preventing the silent mismatch that plagued the old code.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
_CFG = Settings()


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

class VolRegime(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True, slots=True)
class VolEstimate:
    """Typed volatility output that is never ambiguous about units."""
    value: float
    is_annualised: bool
    method: str
    window: Optional[int] = None


# ---------------------------------------------------------------------------
# Historical (realised) volatility
# ---------------------------------------------------------------------------

def historical_volatility(
    returns: pd.Series,
    window: int = 30,
    annualise: bool = True,
    trading_days: int = 252,
) -> pd.Series:
    """Rolling close-to-close realised volatility.

    Parameters
    ----------
    returns : pd.Series
        Log or simple returns (caller decides).
    window : int
        Rolling window size.
    annualise : bool
        Multiply by sqrt(trading_days).
    trading_days : int
        Number used in annualisation (default 252).

    Returns
    -------
    pd.Series
        Rolling volatility; first *window-1* values are NaN.
    """
    vol = returns.rolling(window=window).std()
    if annualise:
        vol = vol * np.sqrt(trading_days)
    return vol


def realised_vol_cone(
    returns: pd.Series,
    windows: tuple[int, ...] = (10, 21, 63, 126, 252),
    trading_days: int = 252,
) -> pd.DataFrame:
    """Realised-vol cone across multiple look-back windows.

    Returns a DataFrame with columns = windows, and rows for
    min / 25th / median / 75th / max / current.
    """
    records: dict[str, dict] = {}
    for w in windows:
        vol = historical_volatility(returns, window=w, trading_days=trading_days).dropna()
        if vol.empty:
            continue
        records[str(w)] = {
            "min": vol.min(),
            "p25": vol.quantile(0.25),
            "median": vol.median(),
            "p75": vol.quantile(0.75),
            "max": vol.max(),
            "current": vol.iloc[-1],
        }
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# EWMA
# ---------------------------------------------------------------------------

def ewma_volatility(
    returns: pd.Series | np.ndarray,
    lambda_: float = 0.94,
    annualise: bool = True,
    trading_days: int = 252,
) -> VolEstimate:
    """Exponentially weighted moving average volatility (RiskMetrics-style).

    Parameters
    ----------
    returns : array-like
        Return series.
    lambda_ : float
        Decay factor (0 < λ < 1).
    annualise : bool
        Multiply by sqrt(trading_days).
    trading_days : int
        Annualisation factor.

    Returns
    -------
    VolEstimate
        Typed volatility value.
    """
    arr = np.asarray(returns, dtype=np.float64)
    n = len(arr)
    weights = np.array([(1 - lambda_) * lambda_ ** i for i in range(n)])
    weights = weights[::-1]
    weights /= weights.sum()
    daily_var = float(np.sum(weights * arr ** 2))
    daily_vol = np.sqrt(daily_var)
    value = daily_vol * np.sqrt(trading_days) if annualise else daily_vol
    return VolEstimate(
        value=value,
        is_annualised=annualise,
        method="ewma",
        window=n,
    )


# ---------------------------------------------------------------------------
# GARCH(p,q)
# ---------------------------------------------------------------------------

def garch_volatility(
    returns: pd.Series | np.ndarray,
    p: int = 1,
    q: int = 1,
    annualise: bool = True,
    trading_days: int = 252,
) -> VolEstimate:
    """Fit GARCH(p,q) and return the 1-step-ahead volatility forecast.

    Uses the ``arch`` library.  Falls back to historical vol on failure.

    Parameters
    ----------
    returns : array-like
        Return series.
    p, q : int
        GARCH / ARCH lag orders.
    annualise : bool
        If True, output is annualised.
    trading_days : int
        Annualisation factor.

    Returns
    -------
    VolEstimate
    """
    try:
        from arch import arch_model  # lazy import — heavy dependency
    except ImportError:
        logger.warning("arch package not installed; falling back to historical vol")
        arr = np.asarray(returns, dtype=np.float64)
        daily = float(np.std(arr))
        val = daily * np.sqrt(trading_days) if annualise else daily
        return VolEstimate(value=val, is_annualised=annualise, method="garch_fallback_hist")

    try:
        arr = np.asarray(returns, dtype=np.float64)
        scale = _CFG.garch_scale_factor
        scaled = arr * scale
        model = arch_model(scaled, vol="GARCH", p=p, q=q, rescale=False)
        result = model.fit(disp="off", show_warning=False)
        forecast = result.forecast(horizon=1)
        daily_vol = float(forecast.variance.iloc[-1, 0]) ** 0.5 / scale
        value = daily_vol * np.sqrt(trading_days) if annualise else daily_vol
        return VolEstimate(value=value, is_annualised=annualise, method=f"garch({p},{q})")
    except Exception as exc:
        logger.warning("GARCH fitting failed: %s — falling back to historical vol", exc)
        daily = float(np.std(arr))
        val = daily * np.sqrt(trading_days) if annualise else daily
        return VolEstimate(value=val, is_annualised=annualise, method="garch_fallback_hist")


# ---------------------------------------------------------------------------
# Forward vol estimate (simple flat extrapolation)
# ---------------------------------------------------------------------------

def forward_vol_estimate(
    short_vol: float,
    long_vol: float,
    short_T: float,
    long_T: float,
) -> float:
    """Estimate forward variance / vol between two tenors.

    Uses: σ_f² = (σ_L² T_L – σ_S² T_S) / (T_L – T_S)

    Returns annualised forward vol.  Returns NaN if the result
    would be imaginary (inverted term-structure artefact).
    """
    if long_T <= short_T:
        raise ValueError("long_T must exceed short_T")
    fwd_var = (long_vol**2 * long_T - short_vol**2 * short_T) / (long_T - short_T)
    if fwd_var < 0:
        logger.warning("Negative forward variance (%.4f); returning NaN", fwd_var)
        return float("nan")
    return float(np.sqrt(fwd_var))


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

def detect_vol_regime(
    current_vol: float,
    historical_vols: pd.Series,
) -> VolRegime:
    """Label the current vol regime by percentile rank.

    * ≤25th  → LOW
    * 25th–75th → NORMAL
    * 75th–95th → HIGH
    * >95th → EXTREME
    """
    if historical_vols.empty:
        return VolRegime.NORMAL
    rank = float((historical_vols < current_vol).mean())
    if rank <= 0.25:
        return VolRegime.LOW
    if rank <= 0.75:
        return VolRegime.NORMAL
    if rank <= 0.95:
        return VolRegime.HIGH
    return VolRegime.EXTREME
