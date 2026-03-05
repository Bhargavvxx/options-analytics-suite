"""
Centralised configuration for the Option Analytics Suite.

All magic numbers, environment knobs, and default parameters live here.
Override via environment variables or by subclassing ``Settings``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DayCountConvention(Enum):
    """Supported day-count conventions for year-fraction calculations."""
    ACT_365 = "ACT/365"
    ACT_252 = "ACT/252"


class VolOutput(Enum):
    """Whether a volatility figure is daily or annualised."""
    DAILY = "daily"
    ANNUALISED = "annualised"


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Immutable application-wide settings.

    Every field has a sensible default; override through ``Settings(...)``
    or by reading ``os.environ`` in the factory method ``from_env()``.
    """

    # -- Day-count / calendar --------------------------------------------------
    day_count: DayCountConvention = DayCountConvention.ACT_365
    trading_days_per_year: int = 252
    calendar_days_per_year: int = 365

    # -- Pricing defaults -------------------------------------------------------
    default_risk_free_rate: float = 0.045
    default_dividend_yield: float = 0.0
    min_time_to_expiry: float = 1e-6          # floor to avoid /0
    min_volatility: float = 1e-6
    max_volatility: float = 10.0              # 1000 %
    min_spot: float = 1e-6
    min_strike: float = 1e-6

    # -- IV solver --------------------------------------------------------------
    iv_newton_tol: float = 1e-8
    iv_newton_max_iter: int = 100
    iv_bisection_tol: float = 1e-8
    iv_bisection_max_iter: int = 200
    iv_brent_tol: float = 1e-10
    iv_brent_max_iter: int = 200
    iv_low_bound: float = 1e-4
    iv_high_bound: float = 10.0

    # -- Greeks finite-difference bump -----------------------------------------
    fd_bump_spot: float = 0.01                # 1 % relative bump
    fd_bump_vol: float = 0.01                 # 1 pp absolute bump
    fd_bump_rate: float = 0.0001              # 1 bp absolute bump
    fd_bump_time: float = 1.0 / 365.0         # 1 calendar day

    # -- Volatility models ------------------------------------------------------
    ewma_lambda: float = 0.94
    garch_p: int = 1
    garch_q: int = 1
    garch_scale_factor: float = 100.0         # scale returns for numerical stability
    default_vol_window: int = 30

    # -- Data layer -------------------------------------------------------------
    data_cache_ttl_seconds: int = 300
    data_max_retries: int = 3
    data_retry_delay_seconds: float = 1.0
    data_stale_threshold_seconds: int = 900   # 15 min
    default_history_period: str = "2y"
    default_interval: str = "1d"

    # Treasury ticker mapping (Yahoo Finance)
    treasury_tickers: Dict[str, str] = field(default_factory=lambda: {
        "3m": "^IRX",
        "5y": "^FVX",
        "10y": "^TNX",
        "30y": "^TYX",
    })

    # -- Backtesting defaults ---------------------------------------------------
    default_commission_per_contract: float = 0.65
    default_slippage_pct: float = 0.001       # 10 bps
    backtest_initial_capital: float = 100_000.0
    annualised_risk_free_for_sharpe: float = 0.045

    # -- ML defaults ------------------------------------------------------------
    ml_test_ratio: float = 0.2
    ml_random_seed: int = 42
    lstm_time_steps: int = 60
    lstm_epochs: int = 50
    lstm_batch_size: int = 32
    xgb_n_estimators: int = 100
    xgb_learning_rate: float = 0.05
    xgb_max_depth: int = 5
    model_artifacts_dir: str = "model_artifacts"

    # -- Sentiment --------------------------------------------------------------
    sentiment_max_headlines: int = 10
    sentiment_request_timeout: int = 10

    # -- UI / Streamlit ---------------------------------------------------------
    auto_refresh_interval_ms: int = 60_000
    ui_cache_ttl_prices: int = 300
    ui_cache_ttl_news: int = 600
    ui_cache_ttl_rates: int = 3600

    # -- Logging ----------------------------------------------------------------
    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s"

    # -------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------
    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings with environment-variable overrides where set."""
        overrides: dict = {}
        if v := os.environ.get("OAS_LOG_LEVEL"):
            overrides["log_level"] = v
        if v := os.environ.get("OAS_RISK_FREE_RATE"):
            overrides["default_risk_free_rate"] = float(v)
        if v := os.environ.get("OAS_TRADING_DAYS"):
            overrides["trading_days_per_year"] = int(v)
        if v := os.environ.get("OAS_MODEL_DIR"):
            overrides["model_artifacts_dir"] = v
        return cls(**overrides)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    @property
    def annualisation_factor(self) -> float:
        """Annualisation multiplier for volatility (sqrt of trading days)."""
        import math
        return math.sqrt(self.trading_days_per_year)

    def year_fraction(self, calendar_days: int) -> float:
        """Convert calendar days to year fraction using the configured convention."""
        if self.day_count == DayCountConvention.ACT_365:
            return max(calendar_days, 0) / self.calendar_days_per_year
        elif self.day_count == DayCountConvention.ACT_252:
            return max(calendar_days, 0) / self.trading_days_per_year
        raise ValueError(f"Unsupported convention: {self.day_count}")
