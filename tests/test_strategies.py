"""Tests for strategies."""
import pytest
import numpy as np

from strategies.definitions import STRATEGY_CATALOG, LegSide, LegType
from strategies.pricing import price_strategy, strategy_payoff
from strategies.signals import generate_trading_signals


class TestDefinitions:
    def test_catalog_not_empty(self):
        assert len(STRATEGY_CATALOG) > 0

    def test_straddle_has_two_legs(self):
        straddle = STRATEGY_CATALOG["straddle"]
        assert len(straddle.legs) == 2
        types = {l.leg_type for l in straddle.legs}
        assert LegType.CALL in types
        assert LegType.PUT in types

    def test_iron_condor_has_four_legs(self):
        ic = STRATEGY_CATALOG["iron_condor"]
        assert len(ic.legs) == 4


class TestPricing:
    def test_long_call_positive(self):
        defn = STRATEGY_CATALOG["long_call"]
        entry = price_strategy(defn, 100, 100, 1.0, 0.05, 0.20)
        assert entry > 0  # debit

    def test_iron_condor_credit(self):
        defn = STRATEGY_CATALOG["iron_condor"]
        entry = price_strategy(defn, 100, 100, 1.0, 0.05, 0.20)
        assert entry < 0  # credit


class TestPayoff:
    def test_long_call_payoff_shape(self):
        defn = STRATEGY_CATALOG["long_call"]
        S_range = np.linspace(80, 120, 50)
        entry = price_strategy(defn, 100, 100, 1.0, 0.05, 0.20)
        pnl = strategy_payoff(defn, S_range, 100, entry)
        assert pnl.shape == (50,)
        # At very low spot, loss should be capped at entry cost
        assert pnl[0] == pytest.approx(-entry, abs=0.01)

    def test_straddle_v_shape(self):
        defn = STRATEGY_CATALOG["straddle"]
        K = 100
        entry = price_strategy(defn, 100, K, 1.0, 0.05, 0.20)
        S_range = np.array([60.0, 100.0, 140.0])
        pnl = strategy_payoff(defn, S_range, K, entry)
        # Wings should have positive payoff (large move)
        assert pnl[0] > 0  # far below K
        assert pnl[2] > 0  # far above K
        # ATM should be worst (pay full premium)
        assert pnl[1] < pnl[0]
        assert pnl[1] < pnl[2]


class TestSignals:
    def test_overpriced_signal(self):
        sig = generate_trading_signals(100, 100, 1.0, 0.05, 0.15, 0.25)
        assert "overpriced" in sig.volatility_assessment.lower()

    def test_underpriced_signal(self):
        sig = generate_trading_signals(100, 100, 1.0, 0.05, 0.25, 0.15)
        assert "underpriced" in sig.volatility_assessment.lower()

    def test_fair_signal(self):
        sig = generate_trading_signals(100, 100, 1.0, 0.05, 0.20, 0.20)
        assert "fair" in sig.volatility_assessment.lower()
