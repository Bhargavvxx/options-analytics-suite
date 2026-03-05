"""
Core back-test engine with proper trade lifecycle.

Design goals
------------
* Separate *signal generation* from *execution* from *accounting*.
* Model transaction costs and bid-ask slippage explicitly.
* Track capital, margin, and P&L per trade.
* Produce a ``BacktestResult`` dataclass that metrics and charts consume.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from analytics.pricing import OptionType, black_scholes_price
from config.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trade / result containers
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """Immutable record of a single trade (after close)."""
    entry_date: date
    exit_date: date
    direction: str            # "long" | "short"
    option_type: str          # "call" | "put" | "stock"
    strike: float
    entry_price: float
    exit_price: float
    quantity: int = 1
    entry_iv: float = 0.0
    exit_iv: float = 0.0
    pnl: float = 0.0
    cost: float = 0.0         # total transaction cost allocated


@dataclass
class BacktestResult:
    """Everything downstream consumers need."""
    trades: List[Trade]
    equity_curve: pd.Series          # date-indexed running equity
    daily_returns: pd.Series         # simple returns of equity curve
    total_pnl: float = 0.0
    total_costs: float = 0.0
    initial_capital: float = 0.0
    final_capital: float = 0.0
    num_trades: int = 0
    win_rate: float = 0.0
    avg_pnl: float = 0.0
    meta: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Event-driven backtest over a price DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        Must have columns ``Close`` (and optionally ``IV``).
    settings : Settings, optional
        If None, uses ``Settings()`` defaults.
    initial_capital : float
        Starting cash.
    cost_per_contract : float
        Fixed cost per contract per side (open + close = 2×).
    slippage_pct : float
        Percent of mid-price added/subtracted on fills.
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        *,
        settings: Optional[Settings] = None,
        initial_capital: float = 100_000.0,
        cost_per_contract: float = 1.50,
        slippage_pct: float = 0.001,
    ) -> None:
        cfg = settings or Settings()
        self.prices = prices.copy()
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.cost_per_contract = cost_per_contract
        self.slippage_pct = slippage_pct
        self.r = cfg.default_risk_free_rate
        self.trades: List[Trade] = []
        self._equity: List[float] = []
        self._dates: List = []
        self._open_position: Optional[dict] = None
        logger.info(
            "BacktestEngine initialised: capital=%.0f, cost=%.2f, slippage=%.4f",
            initial_capital,
            cost_per_contract,
            slippage_pct,
        )

    # ---- helpers ----

    def _fill_price(self, mid: float, is_buy: bool) -> float:
        slip = mid * self.slippage_pct
        return mid + slip if is_buy else mid - slip

    def _txn_cost(self, quantity: int) -> float:
        return self.cost_per_contract * abs(quantity)

    # ---- public API ----

    def run_vol_signal_backtest(
        self,
        strike: float,
        T: float,
        sigma_col: str = "IV",
        hv_col: str = "HV",
        *,
        option_type: str = "call",
        entry_threshold: float = 1.10,
        exit_threshold: float = 1.00,
        quantity: int = 1,
    ) -> BacktestResult:
        """Long-vol / short-vol backtest driven by IV vs HV ratio.

        **Entry**: Sell (short) option when iv / hv > entry_threshold.
        **Exit**: Close when iv / hv < exit_threshold or on last bar.
        """
        opt = OptionType.CALL if option_type == "call" else OptionType.PUT
        prices = self.prices
        if sigma_col not in prices.columns or hv_col not in prices.columns:
            raise ValueError(
                f"DataFrame must contain '{sigma_col}' and '{hv_col}' columns."
            )

        for i, (dt, row) in enumerate(prices.iterrows()):
            S = float(row["Close"])
            iv = float(row.get(sigma_col, 0.20))
            hv = float(row.get(hv_col, 0.20))
            ratio = iv / hv if hv > 0 else 1.0

            if self._open_position is None and ratio > entry_threshold:
                # -- SELL to open --
                entry_mid = black_scholes_price(
                    S, strike, T, self.r, iv, opt, validate=False,
                )
                entry_px = self._fill_price(entry_mid, is_buy=False)
                cost = self._txn_cost(quantity)
                self.capital += entry_px * quantity * 100 - cost  # premium in
                self._open_position = {
                    "entry_date": dt,
                    "entry_price": entry_px,
                    "entry_iv": iv,
                    "strike": strike,
                    "quantity": quantity,
                    "cost": cost,
                }
                logger.debug("Opened short %s @ %.4f on %s", option_type, entry_px, dt)

            elif self._open_position is not None and (
                ratio < exit_threshold or i == len(prices) - 1
            ):
                # -- BUY to close --
                exit_mid = black_scholes_price(
                    S, strike, T, self.r, iv, opt, validate=False,
                )
                exit_px = self._fill_price(exit_mid, is_buy=True)
                close_cost = self._txn_cost(quantity)
                self.capital -= exit_px * quantity * 100 + close_cost
                pnl = (
                    (self._open_position["entry_price"] - exit_px) * quantity * 100
                    - self._open_position["cost"]
                    - close_cost
                )
                trade = Trade(
                    entry_date=self._open_position["entry_date"],
                    exit_date=dt,
                    direction="short",
                    option_type=option_type,
                    strike=strike,
                    entry_price=self._open_position["entry_price"],
                    exit_price=exit_px,
                    quantity=quantity,
                    entry_iv=self._open_position["entry_iv"],
                    exit_iv=iv,
                    pnl=pnl,
                    cost=self._open_position["cost"] + close_cost,
                )
                self.trades.append(trade)
                self._open_position = None
                logger.debug("Closed short %s @ %.4f on %s, PnL=%.2f", option_type, exit_px, dt, pnl)

            self._equity.append(self.capital)
            self._dates.append(dt)

        return self._build_result()

    def _build_result(self) -> BacktestResult:
        eq = pd.Series(self._equity, index=self._dates, name="equity")
        daily_ret = eq.pct_change().dropna()
        total_pnl = sum(t.pnl for t in self.trades)
        total_costs = sum(t.cost for t in self.trades)
        wins = [t for t in self.trades if t.pnl > 0]
        wr = len(wins) / len(self.trades) if self.trades else 0.0
        avg = total_pnl / len(self.trades) if self.trades else 0.0

        return BacktestResult(
            trades=self.trades,
            equity_curve=eq,
            daily_returns=daily_ret,
            total_pnl=total_pnl,
            total_costs=total_costs,
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            num_trades=len(self.trades),
            win_rate=wr,
            avg_pnl=avg,
            meta={
                "slippage_pct": self.slippage_pct,
                "cost_per_contract": self.cost_per_contract,
            },
        )
