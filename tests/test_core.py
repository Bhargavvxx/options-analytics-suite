"""
Unit tests for the Option Analytics Suite core modules.
Run with: python -m pytest tests/ -v
"""
import numpy as np
import pandas as pd
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.black_scholes import black_scholes, implied_volatility, calculate_iv_from_market
from core.volatility import historical_volatility, ewma_volatility, garch_volatility
from core.strategies import get_option_strategies, get_trading_signals
from core.backtesting import backtest_vol_strategy, backtest_option_strategy


# ============================================================
# Black-Scholes Tests
# ============================================================

class TestBlackScholes:
    """Tests for the Black-Scholes pricing model."""

    def test_call_price_positive(self):
        """Call option price should always be positive."""
        price, _ = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        assert price > 0

    def test_put_price_positive(self):
        """Put option price should always be positive."""
        price, _ = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert price > 0

    def test_put_call_parity(self):
        """Test put-call parity: C - P = S*exp(-qT) - K*exp(-rT)."""
        S, K, T, r, sigma, q = 100, 100, 1, 0.05, 0.2, 0.02
        call_price, _ = black_scholes(S, K, T, r, sigma, 'call', q)
        put_price, _ = black_scholes(S, K, T, r, sigma, 'put', q)
        parity = S * np.exp(-q * T) - K * np.exp(-r * T)
        assert abs((call_price - put_price) - parity) < 1e-10

    def test_deep_itm_call_near_intrinsic(self):
        """Deep ITM call with short expiry should be near intrinsic value."""
        S, K, T = 200, 100, 0.001
        price, _ = black_scholes(S, K, T, 0.05, 0.2, 'call')
        intrinsic = S - K * np.exp(-0.05 * T)
        assert abs(price - intrinsic) < 1.0

    def test_deep_otm_call_near_zero(self):
        """Deep OTM call should be near zero."""
        price, _ = black_scholes(50, 200, 0.01, 0.05, 0.2, 'call')
        assert price < 0.01

    def test_higher_vol_higher_price(self):
        """Higher volatility should produce higher option price."""
        price_low, _ = black_scholes(100, 100, 1, 0.05, 0.1, 'call')
        price_high, _ = black_scholes(100, 100, 1, 0.05, 0.5, 'call')
        assert price_high > price_low

    def test_longer_expiry_higher_call(self):
        """Longer time to expiry should produce higher call price (no dividends)."""
        price_short, _ = black_scholes(100, 100, 0.1, 0.05, 0.2, 'call')
        price_long, _ = black_scholes(100, 100, 1.0, 0.05, 0.2, 'call')
        assert price_long > price_short

    def test_input_validation_negative_S(self):
        """Should raise ValueError for negative stock price."""
        with pytest.raises(ValueError):
            black_scholes(-100, 100, 1, 0.05, 0.2)

    def test_input_validation_negative_K(self):
        """Should raise ValueError for negative strike."""
        with pytest.raises(ValueError):
            black_scholes(100, -100, 1, 0.05, 0.2)

    def test_input_validation_zero_sigma(self):
        """Should raise ValueError for zero volatility."""
        with pytest.raises(ValueError):
            black_scholes(100, 100, 1, 0.05, 0)

    def test_input_validation_bad_option_type(self):
        """Should raise ValueError for invalid option type."""
        with pytest.raises(ValueError):
            black_scholes(100, 100, 1, 0.05, 0.2, 'foo')


class TestGreeks:
    """Tests for option Greeks calculations."""

    def test_call_delta_range(self):
        """Call delta should be between 0 and 1."""
        _, greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        assert 0 <= greeks['delta'] <= 1

    def test_put_delta_range(self):
        """Put delta should be between -1 and 0."""
        _, greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert -1 <= greeks['delta'] <= 0

    def test_gamma_positive(self):
        """Gamma should always be positive."""
        _, greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        assert greeks['gamma'] > 0

    def test_call_put_gamma_equal(self):
        """Call and put gamma should be equal."""
        _, call_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        _, put_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert abs(call_greeks['gamma'] - put_greeks['gamma']) < 1e-10

    def test_vega_positive(self):
        """Vega should be positive for both calls and puts."""
        _, call_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        _, put_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert call_greeks['vega'] > 0
        assert put_greeks['vega'] > 0

    def test_call_put_vega_equal(self):
        """Call and put vega should be equal."""
        _, call_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        _, put_greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert abs(call_greeks['vega'] - put_greeks['vega']) < 1e-10

    def test_call_rho_positive(self):
        """Call rho should be positive."""
        _, greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        assert greeks['rho'] > 0

    def test_put_rho_negative(self):
        """Put rho should be negative."""
        _, greeks = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert greeks['rho'] < 0

    def test_delta_with_dividends(self):
        """Delta with dividends should be lower than without for calls."""
        _, greeks_no_div = black_scholes(100, 100, 1, 0.05, 0.2, 'call', q=0)
        _, greeks_div = black_scholes(100, 100, 1, 0.05, 0.2, 'call', q=0.05)
        assert greeks_div['delta'] < greeks_no_div['delta']


class TestImpliedVolatility:
    """Tests for implied volatility calculation."""

    def test_iv_roundtrip(self):
        """IV should recover the original sigma when given the BS price."""
        sigma_original = 0.25
        price, _ = black_scholes(100, 100, 1, 0.05, sigma_original, 'call')
        iv = implied_volatility(price, 100, 100, 1, 0.05, 'call')
        assert abs(iv - sigma_original) < 1e-4

    def test_iv_roundtrip_put(self):
        """IV should recover the original sigma for puts."""
        sigma_original = 0.30
        price, _ = black_scholes(100, 105, 0.5, 0.03, sigma_original, 'put')
        iv = implied_volatility(price, 100, 105, 0.5, 0.03, 'put')
        assert abs(iv - sigma_original) < 1e-4

    def test_iv_positive(self):
        """IV should always be positive."""
        price, _ = black_scholes(100, 100, 1, 0.05, 0.3, 'call')
        iv = implied_volatility(price, 100, 100, 1, 0.05, 'call')
        assert iv > 0

    def test_iv_rejects_zero_price(self):
        """IV should raise for zero option price."""
        with pytest.raises(ValueError):
            implied_volatility(0, 100, 100, 1, 0.05, 'call')

    def test_calculate_iv_from_market(self):
        """Wrapper function should produce same result as direct call."""
        price, _ = black_scholes(100, 100, 1, 0.05, 0.25, 'call')
        iv_direct = implied_volatility(price, 100, 100, 1, 0.05, 'call')
        iv_wrapper = calculate_iv_from_market(price, 100, 100, 1, 0.05, 0, option_type='call')
        assert abs(iv_direct - iv_wrapper) < 1e-4


# ============================================================
# Volatility Tests
# ============================================================

class TestVolatility:
    """Tests for volatility calculations."""

    @pytest.fixture
    def sample_returns(self):
        np.random.seed(42)
        return pd.Series(np.random.normal(0, 0.01, 500))

    def test_historical_vol_annualized(self, sample_returns):
        """Annualized HV should be roughly sqrt(252) * daily std."""
        hv = historical_volatility(sample_returns, window=30, annualize=True)
        last_hv = hv.iloc[-1]
        daily_std = sample_returns.iloc[-30:].std()
        expected = daily_std * np.sqrt(252)
        assert abs(last_hv - expected) < 0.01

    def test_ewma_vol_annualized(self, sample_returns):
        """EWMA vol should be positive and in a reasonable range when annualized."""
        vol = ewma_volatility(sample_returns, annualize=True)
        assert vol > 0
        assert vol < 2.0  # Sanity: less than 200% annualized

    def test_ewma_vol_daily(self, sample_returns):
        """Daily EWMA vol should be much smaller than annualized."""
        daily = ewma_volatility(sample_returns, annualize=False)
        annual = ewma_volatility(sample_returns, annualize=True)
        assert annual > daily * 10  # sqrt(252) ~ 15.87


# ============================================================
# Strategy Tests
# ============================================================

class TestStrategies:
    """Tests for option strategy calculations."""

    def test_straddle_price(self):
        """Straddle = call + put at same strike."""
        strategies = get_option_strategies(100, 100, 1, 0.05, 0.2)
        call_price, _ = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        put_price, _ = black_scholes(100, 100, 1, 0.05, 0.2, 'put')
        assert abs(strategies['Straddle'] - (call_price + put_price)) < 1e-10

    def test_covered_call_price(self):
        """Covered call = stock - call premium."""
        strategies = get_option_strategies(100, 100, 1, 0.05, 0.2)
        call_price, _ = black_scholes(100, 100, 1, 0.05, 0.2, 'call')
        assert abs(strategies['Covered Call'] - (100 - call_price)) < 1e-10

    def test_bull_call_spread_positive(self):
        """Bull call spread should have positive cost."""
        strategies = get_option_strategies(100, 100, 1, 0.05, 0.2)
        assert strategies['Bull Call Spread'] > 0

    def test_trading_signals_keys(self):
        """Trading signals should contain all expected keys."""
        signals = get_trading_signals(100, 100, 1, 0.05, 0.2, 0.3)
        expected_keys = ['volatility', 'vol_action', 'call', 'call_action', 'put', 'put_action', 'strategy']
        for key in expected_keys:
            assert key in signals

    def test_overpriced_signal(self):
        """When IV >> HV, signals should show overpriced."""
        signals = get_trading_signals(100, 100, 1, 0.05, 0.2, 0.4)
        assert 'overpriced' in signals['volatility'].lower()


# ============================================================
# Backtesting Tests
# ============================================================

class TestBacktesting:
    """Tests for backtesting functions."""

    @pytest.fixture
    def sample_prices(self):
        np.random.seed(42)
        prices = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.01, 300))
        return pd.Series(prices, index=pd.date_range('2023-01-01', periods=300))

    def test_vol_backtest_returns_dataframe(self, sample_prices):
        results = backtest_vol_strategy(sample_prices)
        assert isinstance(results, pd.DataFrame)
        assert not results.empty

    def test_vol_backtest_required_columns(self, sample_prices):
        results = backtest_vol_strategy(sample_prices)
        expected = ['Price', 'HV', 'IV', 'Signal', 'Strategy_Return', 'Cumulative_Return']
        for col in expected:
            assert col in results.columns

    def test_vol_backtest_short_data(self):
        """Should return empty DataFrame for insufficient data."""
        short = pd.Series([100, 101, 102])
        results = backtest_vol_strategy(short)
        assert results.empty

    def test_option_backtest_returns_dataframe(self, sample_prices):
        results = backtest_option_strategy(sample_prices, 'long_call', 100, 0.5, 0.05, 0.2)
        assert isinstance(results, pd.DataFrame)
        assert not results.empty

    def test_option_backtest_invalid_strategy(self, sample_prices):
        with pytest.raises(ValueError):
            backtest_option_strategy(sample_prices, 'invalid_strategy', 100, 0.5, 0.05, 0.2)

    def test_vol_backtest_reproducible(self, sample_prices):
        """Two runs should give identical results (fixed seed)."""
        r1 = backtest_vol_strategy(sample_prices)
        r2 = backtest_vol_strategy(sample_prices)
        pd.testing.assert_frame_equal(r1, r2)
