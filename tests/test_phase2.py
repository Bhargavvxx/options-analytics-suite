"""
Tests for Phase 2 features — all five tracks.

Track 1: Surface arbitrage diagnostics
Track 2: American option pricing (binomial tree)
Track 3: Interest-rate term structure (RateCurve)
Track 4: Portfolio risk aggregation + stress testing
Track 5: Strategy policies + capital constraints
"""
from __future__ import annotations

import math

import numpy as np
import pytest


# ===================================================================
# Track 1 — Surface arbitrage diagnostics
# ===================================================================

class TestSurfaceArbitrage:
    """Calendar-spread and butterfly arbitrage checks."""

    @pytest.fixture
    def clean_surface(self):
        """An arbitrage-free IV surface (flat vol)."""
        n_time, n_strike = 10, 15
        strikes = np.linspace(80, 120, n_strike)
        times = np.linspace(0.1, 2.0, n_time)
        strike_grid, time_grid = np.meshgrid(strikes, times)
        iv_grid = np.full_like(strike_grid, 0.20)  # flat → no arb
        return iv_grid, strike_grid, time_grid

    @pytest.fixture
    def calendar_arb_surface(self):
        """Surface with deliberate calendar violations."""
        n_time, n_strike = 10, 15
        strikes = np.linspace(80, 120, n_strike)
        times = np.linspace(0.1, 2.0, n_time)
        strike_grid, time_grid = np.meshgrid(strikes, times)
        iv_grid = np.full_like(strike_grid, 0.20)
        # Inject: make vol spike at short end → total var decreases in T
        iv_grid[0, :] = 0.60  # short T, high vol
        iv_grid[1, :] = 0.05  # next T, low vol → w drops
        return iv_grid, strike_grid, time_grid

    def test_clean_surface_no_violations(self, clean_surface):
        from analytics.arbitrage import surface_arbitrage_check

        iv, K, T = clean_surface
        report = surface_arbitrage_check(iv, K, T, S=100.0, r=0.05)
        assert report.calendar_violations == 0
        assert report.total_grid_points == iv.size

    def test_calendar_arb_detected(self, calendar_arb_surface):
        from analytics.arbitrage import surface_arbitrage_check

        iv, K, T = calendar_arb_surface
        report = surface_arbitrage_check(iv, K, T, S=100.0, r=0.05)
        assert report.calendar_violations > 0
        assert report.calendar_violation_pct > 0

    def test_report_has_masks(self, clean_surface):
        from analytics.arbitrage import surface_arbitrage_check

        iv, K, T = clean_surface
        report = surface_arbitrage_check(iv, K, T, S=100.0, r=0.05)
        assert report.calendar_mask is not None
        assert report.butterfly_mask is not None
        assert report.calendar_mask.shape == iv.shape


# ===================================================================
# Track 2 — American options (binomial tree)
# ===================================================================

class TestBinomialPricing:
    """CRR binomial tree for American and European exercise."""

    def test_european_call_converges_to_bs(self, atm_params):
        from analytics.american import binomial_price, ExerciseStyle
        from analytics.pricing import black_scholes_price

        bs = black_scholes_price(**atm_params, option_type="call")
        res = binomial_price(
            **atm_params, option_type="call",
            exercise=ExerciseStyle.EUROPEAN, steps=500,
        )
        assert abs(res.price - bs) < 0.05, f"Binomial {res.price:.4f} vs BS {bs:.4f}"

    def test_european_put_converges_to_bs(self, atm_params):
        from analytics.american import binomial_price, ExerciseStyle
        from analytics.pricing import black_scholes_price

        bs = black_scholes_price(**atm_params, option_type="put")
        res = binomial_price(
            **atm_params, option_type="put",
            exercise=ExerciseStyle.EUROPEAN, steps=500,
        )
        assert abs(res.price - bs) < 0.05

    def test_american_put_geq_european_put(self, atm_params):
        from analytics.american import binomial_price, ExerciseStyle

        eu = binomial_price(**atm_params, option_type="put", exercise="european", steps=300)
        am = binomial_price(**atm_params, option_type="put", exercise="american", steps=300)
        assert am.price >= eu.price - 1e-10

    def test_american_call_no_dividend_equals_european(self, atm_params):
        """American call on non-dividend stock should equal European call."""
        from analytics.american import binomial_price

        eu = binomial_price(**atm_params, option_type="call", exercise="european", steps=300)
        am = binomial_price(**atm_params, option_type="call", exercise="american", steps=300)
        assert abs(am.price - eu.price) < 0.05

    def test_american_call_with_dividend_premium(self):
        """With dividends, American call should be ≥ European call."""
        from analytics.american import binomial_price

        kw = dict(S=100, K=100, T=1.0, r=0.05, sigma=0.20, q=0.04)
        eu = binomial_price(**kw, option_type="call", exercise="european", steps=300)
        am = binomial_price(**kw, option_type="call", exercise="american", steps=300)
        assert am.price >= eu.price - 1e-10

    def test_discrete_dividends(self):
        from analytics.american import binomial_price, DividendSchedule

        div = DividendSchedule(payments=[(0.25, 2.0), (0.75, 2.0)])
        res = binomial_price(S=100, K=100, T=1.0, r=0.05, sigma=0.20,
                             option_type="put", exercise="american",
                             dividends=div, steps=200)
        assert res.price > 0

    def test_boundary_returned(self, atm_params):
        from analytics.american import binomial_price

        res = binomial_price(**atm_params, option_type="put", exercise="american",
                             steps=100, return_boundary=True)
        assert res.early_exercise_boundary is not None
        assert len(res.early_exercise_boundary) == 101

    def test_invalid_inputs_raise(self):
        from analytics.american import binomial_price

        with pytest.raises(ValueError):
            binomial_price(S=-1, K=100, T=1, r=0.05, sigma=0.2)

    def test_result_fields(self, atm_params):
        from analytics.american import binomial_price

        res = binomial_price(**atm_params, option_type="call", exercise="american")
        assert res.exercise_style == "american"
        assert res.option_type == "call"
        assert res.steps == 200


# ===================================================================
# Track 3 — Interest-rate term structure
# ===================================================================

class TestRateCurve:
    """Zero-rate curve construction and interpolation."""

    def test_flat_curve_constant_rate(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        assert abs(curve.zero_rate(1.0) - 0.05) < 1e-12
        assert abs(curve.zero_rate(10.0) - 0.05) < 1e-12

    def test_discount_factor_formula(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        df = curve.df(2.0)
        assert abs(df - math.exp(-0.05 * 2.0)) < 1e-12

    def test_forward_rate_flat_curve(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        fwd = curve.forward_rate(1.0, 2.0)
        assert abs(fwd - 0.05) < 1e-10

    def test_forward_rate_upward_sloping(self):
        from analytics.rates import build_curve

        curve = build_curve([1.0, 5.0, 10.0], [0.03, 0.04, 0.05])
        fwd = curve.forward_rate(1.0, 5.0)
        z1, z5 = 0.03, 0.04
        expected = (z5 * 5 - z1 * 1) / (5 - 1)
        assert abs(fwd - expected) < 1e-10

    def test_shift_parallel(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        shifted = curve.shift(100)  # +100 bp
        assert abs(shifted.zero_rate(1.0) - 0.06) < 1e-12

    def test_invalid_forward_rate(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        with pytest.raises(ValueError):
            curve.forward_rate(2.0, 1.0)  # T2 < T1

    def test_vectorised_df(self):
        from analytics.rates import flat_curve

        curve = flat_curve(0.05)
        Ts = np.array([1.0, 2.0, 5.0])
        dfs = curve.df(Ts)
        expected = np.exp(-0.05 * Ts)
        np.testing.assert_allclose(dfs, expected, atol=1e-12)

    def test_interpolation_between_pillars(self):
        from analytics.rates import build_curve

        curve = build_curve([1.0, 10.0], [0.03, 0.05])
        # At T=5.5, should interpolate linearly
        z = float(curve.zero_rate(5.5))
        expected = 0.03 + (0.05 - 0.03) * (5.5 - 1.0) / (10.0 - 1.0)
        assert abs(z - expected) < 1e-10

    def test_empty_curve_raises(self):
        from analytics.rates import RateCurve

        with pytest.raises(ValueError):
            RateCurve(pillars=np.array([]), rates=np.array([]))


# ===================================================================
# Track 4 — Portfolio risk + stress testing
# ===================================================================

class TestPortfolioRisk:
    """Portfolio aggregation and stress testing."""

    @pytest.fixture
    def long_call_portfolio(self):
        from risk.portfolio import Portfolio, Position

        portfolio = Portfolio()
        portfolio.add(Position(
            instrument="SPY", option_type="call",
            strike=100, T=1.0, sigma=0.20, quantity=10,
        ))
        return portfolio

    def test_single_call_valuation(self, long_call_portfolio):
        val = long_call_portfolio.valuate(S=100, r=0.05)
        assert val.total_value > 0
        assert val.total_delta > 0  # long call → positive delta
        assert len(val.positions) == 1

    def test_portfolio_aggregation(self):
        from risk.portfolio import Portfolio, Position

        portfolio = Portfolio()
        portfolio.add(Position("SPY", "call", 100, 1.0, 0.20, quantity=10))
        portfolio.add(Position("SPY", "put", 100, 1.0, 0.20, quantity=-10))
        val = portfolio.valuate(S=100, r=0.05)
        # Long call + short put ≈ synthetic long → delta ≈ multiplier * qty
        assert len(val.positions) == 2

    def test_stock_position(self):
        from risk.portfolio import Portfolio, Position

        portfolio = Portfolio()
        portfolio.add(Position("SPY", "stock", quantity=100, multiplier=1.0))
        val = portfolio.valuate(S=100, r=0.05)
        assert abs(val.total_value - 10_000) < 0.01
        assert abs(val.total_delta - 100) < 0.01
        assert val.total_gamma == 0.0

    def test_stress_test_dimensions(self, long_call_portfolio):
        from risk.stress import run_stress_test

        result = run_stress_test(long_call_portfolio, S=100, r=0.05)
        assert result.pnl_matrix.shape[0] == len(result.spot_shocks)
        assert result.pnl_matrix.shape[1] == len(result.vol_shocks)

    def test_stress_test_base_pnl_zero(self, long_call_portfolio):
        from risk.stress import run_stress_test

        result = run_stress_test(long_call_portfolio, S=100, r=0.05)
        # At zero shock the P&L should be zero
        s_idx = np.argmin(np.abs(result.spot_shocks))
        v_idx = np.argmin(np.abs(result.vol_shocks))
        assert abs(result.pnl_matrix[s_idx, v_idx]) < 0.01

    def test_stress_test_worst_best(self, long_call_portfolio):
        from risk.stress import run_stress_test

        result = run_stress_test(long_call_portfolio, S=100, r=0.05)
        assert result.worst_pnl <= 0
        assert result.best_pnl >= 0


# ===================================================================
# Track 5 — Strategy policies + capital constraints
# ===================================================================

class TestStrategyPolicy:
    """IV mean-reversion policy and capital constraints."""

    def test_iv_mean_reversion_entry(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy(entry_threshold=1.10, strike=100.0)
        row = pd.Series({"IV": 0.30, "HV": 0.20, "Close": 100.0})
        result = policy.should_enter(row, {})
        assert result is not None
        assert result["direction"] == "short"

    def test_iv_mean_reversion_no_entry(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy(entry_threshold=1.10)
        row = pd.Series({"IV": 0.20, "HV": 0.20, "Close": 100.0})
        result = policy.should_enter(row, {})
        assert result is None

    def test_iv_mean_reversion_exit(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy(exit_threshold=1.00)
        row = pd.Series({"IV": 0.18, "HV": 0.20, "Close": 100.0})
        assert policy.should_exit(row, {}) == True

    def test_roll_on_low_dte(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy(dte_roll=5, strike=100.0)
        row = pd.Series({"IV": 0.25, "HV": 0.20, "Close": 100.0})
        result = policy.should_roll(row, {"dte": 3})
        assert result is not None

    def test_no_roll_when_dte_ok(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy(dte_roll=5)
        row = pd.Series({"IV": 0.25, "HV": 0.20, "Close": 100.0})
        result = policy.should_roll(row, {"dte": 30})
        assert result is None

    def test_capital_constraints_dataclass(self):
        from strategies.policy import CapitalConstraints

        cc = CapitalConstraints(max_notional=500_000, max_positions=5)
        assert cc.max_notional == 500_000
        assert cc.max_positions == 5
        assert cc.max_loss_pct == 0.20  # default

    def test_policy_handles_missing_cols(self):
        import pandas as pd
        from strategies.policy import IVMeanReversionPolicy

        policy = IVMeanReversionPolicy()
        row = pd.Series({"Close": 100.0})  # no IV/HV
        assert policy.should_enter(row, {}) is None
        assert policy.should_exit(row, {}) is False
