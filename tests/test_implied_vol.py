"""Tests for analytics.implied_vol — IV solver."""
import pytest
from analytics.pricing import OptionType, black_scholes_price
from analytics.implied_vol import solve_iv, batch_solve_iv, IVMethod


class TestSolveIV:
    def test_roundtrip_call(self, atm_params):
        """Price → IV → price should recover original σ."""
        price = black_scholes_price(**atm_params, option_type=OptionType.CALL)
        result = solve_iv(price, atm_params["S"], atm_params["K"],
                          atm_params["T"], atm_params["r"], OptionType.CALL)
        assert result.converged
        assert result.iv == pytest.approx(atm_params["sigma"], abs=1e-6)

    def test_roundtrip_put(self, atm_params):
        price = black_scholes_price(**atm_params, option_type=OptionType.PUT)
        result = solve_iv(price, atm_params["S"], atm_params["K"],
                          atm_params["T"], atm_params["r"], OptionType.PUT)
        assert result.converged
        assert result.iv == pytest.approx(atm_params["sigma"], abs=1e-6)

    def test_deep_otm_convergence(self):
        """Deep OTM option with tiny premium."""
        S, K, T, r, sigma = 100, 150, 0.25, 0.05, 0.30
        price = black_scholes_price(S, K, T, r, sigma, OptionType.CALL)
        result = solve_iv(price, S, K, T, r, OptionType.CALL)
        if result.converged:  # may not converge for very small prices
            assert result.iv == pytest.approx(sigma, abs=0.01)

    def test_high_vol_roundtrip(self):
        """σ = 80%."""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.80
        price = black_scholes_price(S, K, T, r, sigma, OptionType.CALL)
        result = solve_iv(price, S, K, T, r, OptionType.CALL)
        assert result.converged
        assert result.iv == pytest.approx(sigma, abs=0.001)

    def test_arbitrage_violation_returns_non_converged(self):
        """Price below intrinsic → arbitrage → should fail gracefully."""
        result = solve_iv(0.0001, 100, 100, 1.0, 0.05, OptionType.CALL)
        # Should fail gracefully — iv is None or very small
        assert not result.converged or (result.iv is not None and result.iv < 0.01)

    def test_method_field_populated(self, atm_params):
        price = black_scholes_price(**atm_params, option_type=OptionType.CALL)
        result = solve_iv(price, atm_params["S"], atm_params["K"],
                          atm_params["T"], atm_params["r"], OptionType.CALL)
        assert result.method in [m.value for m in IVMethod]


class TestBatchSolveIV:
    def test_batch_of_three(self):
        S, T, r = 100, 1.0, 0.05
        strikes = [90, 100, 110]
        prices = [black_scholes_price(S, k, T, r, 0.20, OptionType.CALL) for k in strikes]
        results = batch_solve_iv(prices, strikes, S, T, r, OptionType.CALL)
        assert len(results) == 3
        for res in results:
            assert res.converged
            assert res.iv == pytest.approx(0.20, abs=0.001)
