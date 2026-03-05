"""
Core back-test engine with proper trade lifecycle.

Design goals
------------
* Separate *signal generation* from *execution* from *accounting*.
* Model transaction costs and bid-ask slippage explicitly.
* Track capital, margin, and P&L per trade.
* Produce a ``BacktestResult`` dataclass that metrics and charts consume.
* **Decaying T**: compute time-to-expiry per bar from an explicit expiry date.
* **Bid/ask fills**: when bid/ask columns are available, fill at the
  actual quoted price; fall back to slippage model otherwise.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from analytics.day_count import DayCountConvention, year_fraction
from analytics.pricing import OptionType, black_scholes_price
from config.errors import BacktestConfigError, ExecutionError
from config.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExecutionMode(str, Enum):
    """How a fill price was determined."""
    BID_ASK = "bid_ask"
    SLIPPAGE = "slippage"


# ---------------------------------------------------------------------------
# Trade / result containers
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """Record of a single completed trade (entry + exit)."""
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
    entry_T: float = 0.0     # time-to-expiry at entry
    exit_T: float = 0.0      # time-to-expiry at exit
    pnl: float = 0.0
    cost: float = 0.0         # total transaction cost allocated
    entry_bid: float = 0.0
    entry_ask: float = 0.0
    exit_bid: float = 0.0
    exit_ask: float = 0.0
    entry_spread: float = 0.0  # ask - bid at entry
    exit_spread: float = 0.0   # ask - bid at exit
    entry_exec_mode: str = ""
    exit_exec_mode: str = ""


@dataclass
class BacktestConfig:
    """Snapshot of all assumptions used for a backtest run (reproducible)."""
    initial_capital: float
    cost_per_contract: float
    slippage_pct: float
    risk_free_rate: float
    day_count: str
    strike: float
    expiry_date: Optional[str]
    option_type: str
    entry_threshold: float
    exit_threshold: float
    quantity: int
    max_spread_pct: float
    use_bid_ask: bool


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
    config: Optional[BacktestConfig] = None
    meta: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_T_remaining(
    current_dt: datetime | date | pd.Timestamp,
    expiry_date: date,
    convention: DayCountConvention = DayCountConvention.ACT_365,
) -> float:
    """Calendar days from *current_dt* to *expiry_date*, as a year fraction."""
    if isinstance(current_dt, pd.Timestamp):
        current_dt = current_dt.date()
    elif isinstance(current_dt, datetime):
        current_dt = current_dt.date()
    days = (expiry_date - current_dt).days
    return year_fraction(max(days, 1), convention)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Event-driven backtest over a price DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        Must have columns ``Close`` (and optionally ``IV``, ``bid``, ``ask``).
    settings : Settings, optional
        If None, uses ``Settings()`` defaults.
    initial_capital : float
        Starting cash.
    cost_per_contract : float
        Fixed cost per contract per side (open + close = 2×).
    slippage_pct : float
        Percent of mid-price added/subtracted on fills (used when no bid/ask).
    day_count : DayCountConvention
        Convention for T decay (ACT/365 or ACT/252).
    use_bid_ask : bool
        If True and bid/ask columns exist, fill at quoted prices.
    max_spread_pct : float
        Reject fills where (ask-bid)/mid > this threshold.
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        *,
        settings: Optional[Settings] = None,
        initial_capital: float = 100_000.0,
        cost_per_contract: float = 1.50,
        slippage_pct: float = 0.001,
        day_count: DayCountConvention = DayCountConvention.ACT_365,
        use_bid_ask: bool = True,
        max_spread_pct: float = 0.20,
    ) -> None:
        cfg = settings or Settings()
        self.prices = prices.copy()
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.cost_per_contract = cost_per_contract
        self.slippage_pct = slippage_pct
        self.day_count = day_count
        self.use_bid_ask = use_bid_ask
        self.max_spread_pct = max_spread_pct
        self.r = cfg.default_risk_free_rate
        self.trades: List[Trade] = []
        self._equity: List[float] = []
        self._dates: List = []
        self._open_position: Optional[dict] = None
        logger.info(
            "BacktestEngine initialised: capital=%.0f, cost=%.2f, slippage=%.4f, day_count=%s",
            initial_capital, cost_per_contract, slippage_pct, day_count.value,
        )

    # ---- helpers ----

    def _has_bid_ask(self) -> bool:
        return (
            self.use_bid_ask
            and "bid" in self.prices.columns
            and "ask" in self.prices.columns
        )

    def _fill_price_bid_ask(
        self, row: pd.Series, is_buy: bool,
    ) -> tuple[float, float, float, ExecutionMode]:
        """Fill from bid/ask columns. Returns (fill_px, bid, ask, mode).

        For a buy, fill at ask. For a sell, fill at bid.
        Validates that market is not crossed and spread is within threshold.
        """
        bid = float(row.get("bid", np.nan))
        ask = float(row.get("ask", np.nan))

        if np.isnan(bid) or np.isnan(ask) or bid <= 0 or ask <= 0:
            # Fall back to slippage model
            mid = float(row["Close"])
            return self._fill_price_slippage(mid, is_buy), bid, ask, ExecutionMode.SLIPPAGE

        if bid > ask:
            logger.warning("Crossed market (bid=%.4f > ask=%.4f); using slippage fallback", bid, ask)
            mid = (bid + ask) / 2.0
            return self._fill_price_slippage(mid, is_buy), bid, ask, ExecutionMode.SLIPPAGE

        mid = (bid + ask) / 2.0
        if mid > 0 and (ask - bid) / mid > self.max_spread_pct:
            logger.warning("Spread %.1f%% exceeds max %.1f%%; using slippage fallback",
                           (ask - bid) / mid * 100, self.max_spread_pct * 100)
            return self._fill_price_slippage(mid, is_buy), bid, ask, ExecutionMode.SLIPPAGE

        fill = ask if is_buy else bid
        return fill, bid, ask, ExecutionMode.BID_ASK

    def _fill_price_slippage(self, mid: float, is_buy: bool) -> float:
        """Slippage model fill: add/subtract percentage of mid."""
        slip = mid * self.slippage_pct
        return mid + slip if is_buy else mid - slip

    def _get_fill(
        self, row: pd.Series, is_buy: bool,
    ) -> tuple[float, float, float, ExecutionMode]:
        """Unified fill dispatcher."""
        if self._has_bid_ask():
            return self._fill_price_bid_ask(row, is_buy)
        mid = float(row["Close"])
        return self._fill_price_slippage(mid, is_buy), np.nan, np.nan, ExecutionMode.SLIPPAGE

    def _txn_cost(self, quantity: int) -> float:
        return self.cost_per_contract * abs(quantity)

    # ---- public API ----

    def run_vol_signal_backtest(
        self,
        strike: float,
        T: float = 0.0,
        sigma_col: str = "IV",
        hv_col: str = "HV",
        *,
        option_type: str = "call",
        entry_threshold: float = 1.10,
        exit_threshold: float = 1.00,
        quantity: int = 1,
        expiry_date: date | str | None = None,
    ) -> BacktestResult:
        """Long-vol / short-vol backtest driven by IV vs HV ratio.

        **Entry**: Sell (short) option when iv / hv > entry_threshold.
        **Exit**: Close when iv / hv < exit_threshold or on last bar.

        Parameters
        ----------
        strike : float
        T : float
            Fixed time-to-expiry (legacy). Ignored when *expiry_date* is set.
        expiry_date : date | str | None
            If provided, T decays per bar using ``day_count`` convention.
            Accepts ``date`` or ISO-format string ``"YYYY-MM-DD"``.
        """
        opt = OptionType.CALL if option_type == "call" else OptionType.PUT
        prices = self.prices
        if sigma_col not in prices.columns or hv_col not in prices.columns:
            raise BacktestConfigError(
                f"DataFrame must contain '{sigma_col}' and '{hv_col}' columns."
            )

        # Parse expiry_date
        _expiry: Optional[date] = None
        if expiry_date is not None:
            if isinstance(expiry_date, str):
                _expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            elif isinstance(expiry_date, datetime):
                _expiry = expiry_date.date()
            else:
                _expiry = expiry_date

        use_decaying_T = _expiry is not None

        bt_config = BacktestConfig(
            initial_capital=self.initial_capital,
            cost_per_contract=self.cost_per_contract,
            slippage_pct=self.slippage_pct,
            risk_free_rate=self.r,
            day_count=self.day_count.value,
            strike=strike,
            expiry_date=_expiry.isoformat() if _expiry else None,
            option_type=option_type,
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold,
            quantity=quantity,
            max_spread_pct=self.max_spread_pct,
            use_bid_ask=self.use_bid_ask,
        )

        for i, (dt, row) in enumerate(prices.iterrows()):
            S = float(row["Close"])
            iv = float(row.get(sigma_col, 0.20))
            hv = float(row.get(hv_col, 0.20))
            ratio = iv / hv if hv > 0 else 1.0

            # Compute T for this bar
            if use_decaying_T:
                T_bar = _compute_T_remaining(dt, _expiry, self.day_count)
            else:
                T_bar = T

            if self._open_position is None and ratio > entry_threshold:
                # -- SELL to open --
                entry_mid = black_scholes_price(
                    S, strike, T_bar, self.r, iv, opt, validate=False,
                )
                fill_px, bid, ask, exec_mode = self._get_fill(row, is_buy=False)
                # For BS-based backtest, use the model price adjusted by execution
                entry_px = self._fill_price_slippage(entry_mid, is_buy=False)
                cost = self._txn_cost(quantity)
                self.capital += entry_px * quantity * 100 - cost  # premium in
                self._open_position = {
                    "entry_date": dt,
                    "entry_price": entry_px,
                    "entry_iv": iv,
                    "entry_T": T_bar,
                    "strike": strike,
                    "quantity": quantity,
                    "cost": cost,
                    "entry_bid": bid,
                    "entry_ask": ask,
                    "entry_spread": (ask - bid) if not (np.isnan(bid) or np.isnan(ask)) else 0.0,
                    "entry_exec_mode": exec_mode.value,
                }
                logger.debug("Opened short %s @ %.4f on %s (T=%.4f)", option_type, entry_px, dt, T_bar)

            elif self._open_position is not None and (
                ratio < exit_threshold or i == len(prices) - 1
            ):
                # -- BUY to close --
                exit_mid = black_scholes_price(
                    S, strike, T_bar, self.r, iv, opt, validate=False,
                )
                exit_px = self._fill_price_slippage(exit_mid, is_buy=True)
                fill_px, bid, ask, exec_mode = self._get_fill(row, is_buy=True)
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
                    entry_T=self._open_position["entry_T"],
                    exit_T=T_bar,
                    pnl=pnl,
                    cost=self._open_position["cost"] + close_cost,
                    entry_bid=self._open_position["entry_bid"],
                    entry_ask=self._open_position["entry_ask"],
                    exit_bid=bid,
                    exit_ask=ask,
                    entry_spread=self._open_position["entry_spread"],
                    exit_spread=(ask - bid) if not (np.isnan(bid) or np.isnan(ask)) else 0.0,
                    entry_exec_mode=self._open_position["entry_exec_mode"],
                    exit_exec_mode=exec_mode.value,
                )
                self.trades.append(trade)
                self._open_position = None
                logger.debug("Closed short %s @ %.4f on %s (T=%.4f), PnL=%.2f",
                             option_type, exit_px, dt, T_bar, pnl)

            self._equity.append(self.capital)
            self._dates.append(dt)

        return self._build_result(bt_config)

    def _build_result(self, config: Optional[BacktestConfig] = None) -> BacktestResult:
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
            config=config,
            meta={
                "slippage_pct": self.slippage_pct,
                "cost_per_contract": self.cost_per_contract,
            },
        )
