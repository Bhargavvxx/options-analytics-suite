"""Tests for analytics.volatility — vol models and regime detection."""
import pytest
import numpy as np
import pandas as pd

from analytics.volatility import (
    historical_volatility,
    ewma_volatility,
    garch_volatility,
    realised_vol_cone,
    detect_vol_regime,
    forward_vol_estimate,
    VolRegime,
)


@pytest.fixture
def price_series():
    """Simulated price series for testing."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.01, 500)
    prices = 100 * np.exp(np.cumsum(returns))
    idx = pd.bdate_range("2022-01-01", periods=500)
    return pd.Series(prices, index=idx, name="Close")


class TestHistoricalVolatility:
    def test_returns_series(self, price_series):
        hv = historical_volatility(price_series, window=20)
        assert isinstance(hv, pd.Series)
        assert len(hv) == len(price_series)

    def test_positive(self, price_series):
        hv = historical_volatility(price_series, window=20).dropna()
        assert (hv >= 0).all()

    def test_annualised(self, price_series):
        log_ret = np.log(price_series / price_series.shift(1)).dropna()
        hv = historical_volatility(log_ret, window=20, trading_days=252).dropna()
        # 1% daily vol → ~16% annual
        assert hv.mean() < 1.0  # sanity: should be reasonable %


class TestEWMA:
    def test_returns_vol_estimate(self, price_series):
        est = ewma_volatility(price_series)
        assert est.value > 0
        assert est.is_annualised
        assert est.method == "ewma"


class TestGARCH:
    def test_returns_vol_estimate(self, price_series):
        est = garch_volatility(price_series)
        assert est.value > 0
        assert est.is_annualised


class TestVolCone:
    def test_returns_dataframe(self, price_series):
        cone = realised_vol_cone(price_series)
        assert isinstance(cone, pd.DataFrame)
        assert "current" in cone.index
        assert "median" in cone.index


class TestRegime:
    def test_returns_enum(self, price_series):
        hv = historical_volatility(price_series, window=20).dropna()
        current = hv.iloc[-1]
        regime = detect_vol_regime(current, hv)
        assert isinstance(regime, VolRegime)


class TestForwardVol:
    def test_positive(self):
        # short_vol=0.20, long_vol=0.30, short_T=0.5, long_T=1.0
        fwd = forward_vol_estimate(0.20, 0.30, 0.5, 1.0)
        assert fwd > 0

    def test_flat_term_structure(self):
        """Same vol over both periods → forward vol == short vol."""
        fwd = forward_vol_estimate(0.20, 0.20, 0.5, 1.0)
        assert fwd == pytest.approx(0.20, abs=1e-6)
