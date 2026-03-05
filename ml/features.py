"""
Feature engineering pipeline for volatility / price prediction.

All feature construction is encapsulated here so both training and
inference use the exact same transformations.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Feature column names (single source of truth)
# --------------------------------------------------------------------------
FEATURE_COLS: List[str] = [
    "return_1d",
    "return_5d",
    "return_20d",
    "vol_5d",
    "vol_20d",
    "vol_60d",
    "vol_ratio_5_20",
    "vol_ratio_20_60",
    "rsi_14",
    "log_volume_ratio",
    "high_low_range",
    "close_to_sma20",
    "close_to_sma50",
]

TARGET_COL: str = "fwd_vol_20d"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def build_feature_matrix(
    prices: pd.DataFrame,
    *,
    target: bool = True,
    ann_factor: float = 252.0,
    dropna: bool = True,
) -> pd.DataFrame:
    """Build a model-ready feature + target DataFrame from OHLCV data.

    Parameters
    ----------
    prices : pd.DataFrame
        Must contain at least ``Close``; ``Volume``, ``High``, ``Low``
        are used if available.
    target : bool
        If True, compute the forward 20-day realised vol target column.
    dropna : bool
        Drop rows with any NaN (recommended before training, not for
        live inference on the latest row).

    Returns
    -------
    pd.DataFrame
        Columns are ``FEATURE_COLS`` (+ ``TARGET_COL`` when target=True).
    """
    df = prices.copy()
    close = df["Close"]
    log_ret = np.log(close / close.shift(1))

    # -- Returns --
    df["return_1d"] = log_ret
    df["return_5d"] = np.log(close / close.shift(5))
    df["return_20d"] = np.log(close / close.shift(20))

    # -- Realised vol at multiple windows --
    df["vol_5d"] = log_ret.rolling(5).std() * np.sqrt(ann_factor)
    df["vol_20d"] = log_ret.rolling(20).std() * np.sqrt(ann_factor)
    df["vol_60d"] = log_ret.rolling(60).std() * np.sqrt(ann_factor)

    # -- Vol ratios (term-structure proxies) --
    df["vol_ratio_5_20"] = df["vol_5d"] / df["vol_20d"].replace(0, np.nan)
    df["vol_ratio_20_60"] = df["vol_20d"] / df["vol_60d"].replace(0, np.nan)

    # -- RSI --
    df["rsi_14"] = _rsi(close, 14)

    # -- Volume --
    if "Volume" in df.columns:
        vol_sma = df["Volume"].rolling(20).mean()
        df["log_volume_ratio"] = np.log(
            (df["Volume"] / vol_sma.replace(0, np.nan)).clip(lower=1e-6)
        )
    else:
        df["log_volume_ratio"] = 0.0

    # -- Range / trend --
    if "High" in df.columns and "Low" in df.columns:
        df["high_low_range"] = (df["High"] - df["Low"]) / close
    else:
        df["high_low_range"] = 0.0

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    df["close_to_sma20"] = (close - sma20) / sma20.replace(0, np.nan)
    df["close_to_sma50"] = (close - sma50) / sma50.replace(0, np.nan)

    # -- Target: forward 20-day realised vol --
    if target:
        # Forward-looking rolling vol: reverse, compute rolling std, reverse back
        fwd_ret = log_ret.iloc[::-1].rolling(20).std().iloc[::-1] * np.sqrt(ann_factor)
        df[TARGET_COL] = fwd_ret.shift(-1)  # 1-day-ahead avoids look-ahead

    cols = FEATURE_COLS + ([TARGET_COL] if target else [])
    out = df[cols].copy()
    if dropna:
        before = len(out)
        out = out.dropna()
        logger.info("Feature matrix: %d → %d rows after dropna", before, len(out))
    return out
