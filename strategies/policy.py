"""
Strategy execution policies for automated backtest signal generation.

A *policy* encapsulates entry/exit/roll logic so that the backtest engine
can be driven by declarative rules rather than ad-hoc if/else chains.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from analytics.pricing import OptionType


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class StrategyPolicy(abc.ABC):
    """Interface that the backtest engine calls on every bar."""

    @abc.abstractmethod
    def should_enter(self, row: pd.Series, state: dict) -> Optional[dict]:
        """Return entry params dict or None to skip.

        The returned dict should contain at least:
        ``{'direction': 'long'|'short', 'option_type': 'call'|'put',
           'strike': float, 'quantity': int}``
        """

    @abc.abstractmethod
    def should_exit(self, row: pd.Series, state: dict) -> bool:
        """Return True to close the current position."""

    @abc.abstractmethod
    def should_roll(self, row: pd.Series, state: dict) -> Optional[dict]:
        """Return new-position params dict if a roll is warranted, else None.

        A roll = close current + open new in the same bar.
        """


# ---------------------------------------------------------------------------
# IV > HV mean-reversion policy
# ---------------------------------------------------------------------------

class IVMeanReversionPolicy(StrategyPolicy):
    """Short vol when IV/HV is rich, close when it normalises.

    Parameters
    ----------
    entry_threshold : float
        IV/HV ratio above which we sell (default 1.10 = 10 % rich).
    exit_threshold : float
        IV/HV ratio below which we buy back (default 1.00).
    strike_col : str
        Column in the price DataFrame for strike (used as-is).
    iv_col, hv_col : str
        Column names for IV and HV.
    dte_roll : int
        Days-to-expiry at which to roll to next contract.
    """

    def __init__(
        self,
        entry_threshold: float = 1.10,
        exit_threshold: float = 1.00,
        strike: float = 100.0,
        iv_col: str = "IV",
        hv_col: str = "HV",
        option_type: str = "call",
        quantity: int = 1,
        dte_roll: int = 5,
    ) -> None:
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.strike = strike
        self.iv_col = iv_col
        self.hv_col = hv_col
        self.option_type = option_type
        self.quantity = quantity
        self.dte_roll = dte_roll

    def _ratio(self, row: pd.Series) -> Optional[float]:
        iv = row.get(self.iv_col)
        hv = row.get(self.hv_col)
        if iv is None or hv is None or hv == 0:
            return None
        return iv / hv

    def should_enter(self, row: pd.Series, state: dict) -> Optional[dict]:
        ratio = self._ratio(row)
        if ratio is None:
            return None
        if ratio > self.entry_threshold:
            return {
                "direction": "short",
                "option_type": self.option_type,
                "strike": self.strike,
                "quantity": self.quantity,
            }
        return None

    def should_exit(self, row: pd.Series, state: dict) -> bool:
        ratio = self._ratio(row)
        if ratio is None:
            return False
        return ratio < self.exit_threshold

    def should_roll(self, row: pd.Series, state: dict) -> Optional[dict]:
        dte = state.get("dte")
        if dte is not None and dte <= self.dte_roll:
            return {
                "direction": "short",
                "option_type": self.option_type,
                "strike": self.strike,
                "quantity": self.quantity,
            }
        return None


# ---------------------------------------------------------------------------
# Capital constraints
# ---------------------------------------------------------------------------

@dataclass
class CapitalConstraints:
    """Risk limits applied by the backtest engine.

    Parameters
    ----------
    max_notional : float
        Maximum total notional exposure (sum of |qty × price × multiplier|).
    max_positions : int
        Maximum number of concurrent open positions.
    per_trade_budget : float
        Maximum capital allocated per new trade (premium + margin).
    max_loss_pct : float
        Drawdown trigger: stop opening new trades once cumulative loss
        exceeds this fraction of initial capital.
    """
    max_notional: float = 1_000_000.0
    max_positions: int = 10
    per_trade_budget: float = 50_000.0
    max_loss_pct: float = 0.20
