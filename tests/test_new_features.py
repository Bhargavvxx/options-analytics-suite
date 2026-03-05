"""Tests for new institution-grade features.

Covers:
- Decaying T in BacktestEngine
- Bid/ask execution model
- BacktestConfig reproducibility
- Trade blotter with enriched fields
- IV surface QC diagnostics
- SVI smile calibration
- Bid/ask validation in normalization
- Custom exceptions
"""
import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta
from dataclasses import asdict

from backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    ExecutionMode,
    Trade,
    _compute_T_remaining,
)
from backtesting.metrics import compute_metrics
from analytics.iv_surface import IVSurface, IVSurfacePoint, SurfaceQC
from analytics.day_count import DayCountConvention
from data.normalization import validate_bid_ask
from config.errors import (
    OASError,
    DataFetchError,
    SolverError,
    SurfaceBuildError,
    BacktestConfigError,
    ExecutionError,
)


# ===================================================================
# Decaying T
# ===================================================================

class TestDecayingT:
    """Tests for time-to-expiry decay in the backtest engine."""

    def _make_prices(self, n_days: int = 60):
        """Create a synthetic price DataFrame with IV and HV columns."""
        dates = pd.bdate_range("2024-01-01", periods=n_days)
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n_days) * 0.5)
        df = pd.DataFrame({
            "Close": close,
            "IV": 0.25,  # constant IV
            "HV": 0.18,  # constant HV → ratio ~ 1.39 > entry_threshold
        }, index=dates)
        return df

    def test_compute_T_remaining_basic(self):
        """T remaining decays as current date approaches expiry."""
        expiry = date(2024, 6, 30)
        t1 = _compute_T_remaining(date(2024, 1, 1), expiry)
        t2 = _compute_T_remaining(date(2024, 3, 1), expiry)
        t3 = _compute_T_remaining(date(2024, 6, 29), expiry)
        assert t1 > t2 > t3
        assert t3 > 0  # at least 1 day

    def test_compute_T_remaining_with_timestamp(self):
        """Should work with pd.Timestamp too."""
        expiry = date(2024, 6, 30)
        ts = pd.Timestamp("2024-01-01")
        result = _compute_T_remaining(ts, expiry)
        assert result > 0

    def test_compute_T_remaining_past_expiry(self):
        """Past expiry should clamp to at least 1 day."""
        expiry = date(2024, 1, 1)
        result = _compute_T_remaining(date(2024, 6, 30), expiry)
        assert result > 0  # clamped to 1 day

    def test_decaying_T_backtest_produces_trades(self):
        """Engine with expiry_date should run and produce trades."""
        prices = self._make_prices(60)
        expiry = date(2024, 6, 30)
        engine = BacktestEngine(prices, initial_capital=100_000.0)
        result = engine.run_vol_signal_backtest(
            strike=100.0,
            entry_threshold=1.10,
            exit_threshold=0.95,
            expiry_date=expiry,
        )
        assert isinstance(result, BacktestResult)
        assert result.config is not None
        assert result.config.expiry_date == expiry.isoformat()

    def test_trade_has_T_fields(self):
        """Trades should record entry_T and exit_T when using decaying T."""
        prices = self._make_prices(60)
        expiry = date(2024, 6, 30)
        engine = BacktestEngine(prices, initial_capital=100_000.0)
        result = engine.run_vol_signal_backtest(
            strike=100.0,
            entry_threshold=1.10,
            exit_threshold=0.95,
            expiry_date=expiry,
        )
        if result.trades:
            t0 = result.trades[0]
            assert t0.entry_T > 0
            assert t0.exit_T > 0
            # Entry T should be >= exit T (time decayed)
            assert t0.entry_T >= t0.exit_T

    def test_expiry_date_string_parsing(self):
        """Accepts ISO date strings."""
        prices = self._make_prices(30)
        engine = BacktestEngine(prices, initial_capital=100_000.0)
        result = engine.run_vol_signal_backtest(
            strike=100.0,
            entry_threshold=1.10,
            exit_threshold=0.95,
            expiry_date="2024-06-30",
        )
        assert result.config.expiry_date == "2024-06-30"


# ===================================================================
# Bid / ask execution model
# ===================================================================

class TestBidAskExecution:
    """Tests for bid/ask fill logic."""

    def _make_prices_with_quotes(self, n_days: int = 40):
        dates = pd.bdate_range("2024-01-01", periods=n_days)
        np.random.seed(99)
        close = 100 + np.cumsum(np.random.randn(n_days) * 0.3)
        df = pd.DataFrame({
            "Close": close,
            "IV": 0.28,
            "HV": 0.20,
            "bid": close - 0.5,
            "ask": close + 0.5,
        }, index=dates)
        return df

    def test_bid_ask_fills_used_when_available(self):
        """Engine should detect bid/ask columns and use them."""
        prices = self._make_prices_with_quotes()
        engine = BacktestEngine(prices, use_bid_ask=True)
        assert engine._has_bid_ask()

    def test_slippage_fallback_when_no_quotes(self):
        """Without bid/ask columns, should fall back to slippage model."""
        dates = pd.bdate_range("2024-01-01", periods=20)
        df = pd.DataFrame({
            "Close": np.full(20, 100.0),
            "IV": 0.25,
            "HV": 0.18,
        }, index=dates)
        engine = BacktestEngine(df, use_bid_ask=True)
        assert not engine._has_bid_ask()

    def test_trade_records_exec_mode(self):
        """Trade objects should record how fills were determined."""
        prices = self._make_prices_with_quotes(40)
        engine = BacktestEngine(prices, use_bid_ask=True, initial_capital=100_000.0)
        result = engine.run_vol_signal_backtest(
            strike=100.0,
            entry_threshold=1.10,
            exit_threshold=0.95,
        )
        if result.trades:
            t0 = result.trades[0]
            assert t0.entry_exec_mode in ("bid_ask", "slippage")
            assert t0.exit_exec_mode in ("bid_ask", "slippage")


# ===================================================================
# BacktestConfig reproducibility
# ===================================================================

class TestBacktestConfig:
    """Tests for BacktestConfig snapshot."""

    def test_config_attached_to_result(self):
        dates = pd.bdate_range("2024-01-01", periods=30)
        df = pd.DataFrame({
            "Close": np.full(30, 100.0), "IV": 0.25, "HV": 0.18,
        }, index=dates)
        engine = BacktestEngine(df, initial_capital=50_000.0, slippage_pct=0.002)
        result = engine.run_vol_signal_backtest(strike=100.0, T=0.5)
        assert result.config is not None
        assert result.config.initial_capital == 50_000.0
        assert result.config.slippage_pct == 0.002

    def test_config_is_serialisable(self):
        cfg = BacktestConfig(
            initial_capital=100_000, cost_per_contract=1.5,
            slippage_pct=0.001, risk_free_rate=0.05,
            day_count="ACT/365", strike=100.0, expiry_date="2024-06-30",
            option_type="call", entry_threshold=1.10, exit_threshold=1.00,
            quantity=1, max_spread_pct=0.20, use_bid_ask=True,
        )
        d = asdict(cfg)
        assert isinstance(d, dict)
        assert d["strike"] == 100.0


# ===================================================================
# IV Surface QC
# ===================================================================

class TestSurfaceQC:
    """Tests for SurfaceQC diagnostics dataclass."""

    def test_qc_defaults(self):
        qc = SurfaceQC()
        assert qc.total_points == 0
        assert qc.pct_missing == 0.0

    def test_qc_pct_missing(self):
        qc = SurfaceQC(total_points=100, failed_points=15, converged_points=85)
        qc.pct_missing = qc.failed_points / qc.total_points * 100.0
        assert qc.pct_missing == pytest.approx(15.0)

    def test_surface_with_qc_attached(self):
        qc = SurfaceQC(total_points=50, converged_points=45, failed_points=5,
                        pct_missing=10.0, used_market_iv=30, used_solver=15)
        surface = IVSurface(spot=100.0, points=[], qc=qc)
        assert surface.qc is not None
        assert surface.qc.used_market_iv == 30


# ===================================================================
# SVI smile
# ===================================================================

class TestSVISmile:
    """Tests for SVI calibration."""

    def test_svi_total_variance_positive(self):
        from analytics.smile import SVIParams, svi_total_variance
        params = SVIParams(a=0.04, b=0.1, rho=-0.3, m=0.0, sigma=0.1, T=1.0)
        k = np.linspace(-0.3, 0.3, 50)
        w = svi_total_variance(k, params)
        assert np.all(w > 0)

    def test_svi_implied_vol_shape(self):
        from analytics.smile import SVIParams, svi_implied_vol
        params = SVIParams(a=0.04, b=0.1, rho=-0.3, m=0.0, sigma=0.1, T=1.0)
        k = np.linspace(-0.3, 0.3, 50)
        iv = svi_implied_vol(k, params)
        assert iv.shape == (50,)
        assert np.all(iv > 0)

    def test_calibrate_svi_roundtrip(self):
        """Calibrate SVI to data generated from known SVI params."""
        from analytics.smile import SVIParams, svi_implied_vol, calibrate_svi
        true_params = SVIParams(a=0.04, b=0.08, rho=-0.25, m=0.01, sigma=0.15, T=1.0)
        forward = 100.0
        strikes = np.linspace(80, 120, 20)
        k = np.log(strikes / forward)
        ivs = svi_implied_vol(k, true_params)

        fitted = calibrate_svi(strikes, ivs, T=1.0, forward=forward)
        assert fitted is not None
        assert fitted.rmse < 0.001

    def test_calibrate_svi_too_few_points(self):
        from analytics.smile import calibrate_svi
        strikes = np.array([90, 100, 110])
        ivs = np.array([0.22, 0.20, 0.21])
        result = calibrate_svi(strikes, ivs, T=1.0, forward=100.0)
        assert result is None  # need >= 5 points


# ===================================================================
# Bid / ask validation in normalization
# ===================================================================

class TestValidateBidAsk:
    """Tests for the validate_bid_ask function."""

    def test_drops_crossed_markets(self):
        df = pd.DataFrame({
            "strike": [100, 101, 102],
            "bid": [3.0, 2.5, 2.0],
            "ask": [2.5, 2.8, 2.5],  # row 0 is crossed
        })
        result = validate_bid_ask(df)
        assert len(result) == 2  # row 0 dropped

    def test_flags_wide_spreads(self):
        df = pd.DataFrame({
            "strike": [100, 101],
            "bid": [1.0, 2.0],
            "ask": [2.0, 2.2],  # row 0: spread/mid = 1/1.5 = 66%
        })
        result = validate_bid_ask(df, max_spread_pct=0.30)
        assert "wide" in result.columns
        assert result["wide"].iloc[0]  # row 0 is wide
        assert not result["wide"].iloc[1]

    def test_empty_df_passthrough(self):
        df = pd.DataFrame()
        result = validate_bid_ask(df)
        assert result.empty

    def test_no_bid_ask_cols(self):
        df = pd.DataFrame({"strike": [100], "lastPrice": [2.3]})
        result = validate_bid_ask(df)
        assert len(result) == 1  # unchanged


# ===================================================================
# Custom exceptions
# ===================================================================

class TestCustomExceptions:
    """Tests for the config.errors module."""

    def test_hierarchy(self):
        assert issubclass(DataFetchError, OASError)
        assert issubclass(SolverError, OASError)
        assert issubclass(SurfaceBuildError, OASError)
        assert issubclass(BacktestConfigError, OASError)
        assert issubclass(ExecutionError, OASError)

    def test_backtest_config_error_raised(self):
        dates = pd.bdate_range("2024-01-01", periods=20)
        df = pd.DataFrame({"Close": np.full(20, 100.0)}, index=dates)
        engine = BacktestEngine(df)
        with pytest.raises(BacktestConfigError):
            engine.run_vol_signal_backtest(strike=100.0, T=0.5)


# ===================================================================
# Trade enriched fields
# ===================================================================

class TestTradeEnrichedFields:
    """Test that Trade dataclass has the new fields."""

    def test_trade_has_spread_fields(self):
        t = Trade(
            entry_date=date(2024, 1, 1), exit_date=date(2024, 1, 15),
            direction="short", option_type="call", strike=100.0,
            entry_price=5.0, exit_price=3.0,
            entry_bid=4.8, entry_ask=5.2, exit_bid=2.9, exit_ask=3.1,
            entry_spread=0.4, exit_spread=0.2,
            entry_exec_mode="bid_ask", exit_exec_mode="bid_ask",
            entry_T=0.5, exit_T=0.46,
        )
        assert t.entry_spread == 0.4
        assert t.exit_T == 0.46
        assert t.entry_exec_mode == "bid_ask"
