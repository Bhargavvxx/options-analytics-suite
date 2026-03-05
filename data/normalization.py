"""
Data normalisation and validation utilities.

Every piece of data coming from the market-data layer should pass
through these functions before entering the analytics engine.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# OHLCV validation
# ---------------------------------------------------------------------------

def validate_ohlcv(df: pd.DataFrame, label: str = "OHLCV") -> pd.DataFrame:
    """Validate and clean an OHLCV DataFrame.

    * Drops rows where *Close* is NaN or ≤ 0.
    * Ensures a DatetimeIndex.
    * Logs a warning if > 5 % of rows were dropped.

    Returns the cleaned DataFrame (may be empty).
    """
    if df.empty:
        return df

    original_len = len(df)

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            logger.warning("%s: could not convert index to DatetimeIndex", label)

    # Drop bad Close values
    if "Close" in df.columns:
        mask = df["Close"].notna() & (df["Close"] > 0)
        df = df.loc[mask].copy()

    dropped = original_len - len(df)
    if dropped > 0:
        pct = dropped / original_len * 100
        logger.info("%s: dropped %d / %d rows (%.1f%%)", label, dropped, original_len, pct)
        if pct > 5:
            logger.warning("%s: > 5%% of rows dropped — data quality concern", label)

    return df


# ---------------------------------------------------------------------------
# Option-chain normalisation
# ---------------------------------------------------------------------------

_REQUIRED_CHAIN_COLS = {"strike", "lastPrice", "bid", "ask"}


def normalize_option_chain(df: pd.DataFrame, label: str = "chain") -> pd.DataFrame:
    """Normalise an option-chain DataFrame.

    * Ensures required columns exist (fills with NaN if missing).
    * Adds a ``mid`` column = (bid + ask) / 2 where both are available.
    * Drops rows where strike ≤ 0.
    * Replaces 0 bids/asks with NaN.
    """
    if df.empty:
        return df

    for col in _REQUIRED_CHAIN_COLS:
        if col not in df.columns:
            logger.warning("%s: missing column '%s'; filling with NaN", label, col)
            df[col] = np.nan

    # Clean strike
    df = df[df["strike"] > 0].copy()

    # Replace zero bid/ask with NaN (zero means no quote, not free)
    for col in ("bid", "ask"):
        df.loc[df[col] <= 0, col] = np.nan

    # Mid price
    df["mid"] = (df["bid"] + df["ask"]) / 2.0

    return df


def safe_mid_price(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    strike: float,
    option_type: str,
) -> Optional[float]:
    """Return the bid-ask midpoint for a specific strike, or ``None``.

    Never raises — returns ``None`` on any failure.
    """
    try:
        chain = calls if option_type.lower() == "call" else puts
        row = chain.loc[chain["strike"] == strike].iloc[0]
        bid = row.get("bid", np.nan)
        ask = row.get("ask", np.nan)
        if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask > 0:
            return float((bid + ask) / 2.0)
        if "lastPrice" in row.index and pd.notna(row["lastPrice"]) and row["lastPrice"] > 0:
            logger.debug("Using lastPrice as fallback for strike %.2f", strike)
            return float(row["lastPrice"])
        return None
    except (IndexError, KeyError):
        return None
