"""Tests for analytics.pricing — Black-Scholes pricing engine."""
import math
import pytest
import numpy as np

from analytics.pricing import OptionType, black_scholes_price, put_call_parity_check


class TestBlackScholesPrice:
    """Benchmark: Hull, Options Futures and Other Derivatives, 10th ed."""

    def test_call_hull_benchmark(self):
        """Hull Example 15.6: S=42, K=40, T=0.5, r=10%, σ=20%."""
        price = black_scholes_price(42, 40, 0.5, 0.10, 0.20, OptionType.CALL)
        assert price == pytest.approx(4.76, abs=0.02)

    def test_put_hull_benchmark(self):
        """Corresponding put from put-call parity."""
        call = black_scholes_price(42, 40, 0.5, 0.10, 0.20, OptionType.CALL)
        put = black_scholes_price(42, 40, 0.5, 0.10, 0.20, OptionType.PUT)
        # C - P = S - K*exp(-rT)
        parity = call - put - (42 - 40 * math.exp(-0.10 * 0.5))
        assert parity == pytest.approx(0, abs=1e-10)

    def test_deep_itm_call(self):
        """Deep ITM call should be approximately S - K*exp(-rT)."""
        S, K, T, r, sigma = 200, 100, 1.0, 0.05, 0.20
        price = black_scholes_price(S, K, T, r, sigma, OptionType.CALL)
        intrinsic = S - K * math.exp(-r * T)
        assert price >= intrinsic - 0.01

    def test_deep_otm_put_near_zero(self):
        price = black_scholes_price(200, 100, 0.1, 0.05, 0.20, OptionType.PUT)
        assert price < 0.01

    def test_atm_symmetry(self, atm_params):
        """ATM forward straddle: call ≈ put when S ≈ K*exp(-rT)."""
        # Adjust for forward: S = K*exp(-rT)
        K, T, r, sigma = 100, 1.0, 0.05, 0.20
        S_fwd = K * math.exp(-r * T)
        c = black_scholes_price(S_fwd, K, T, r, sigma, OptionType.CALL)
        p = black_scholes_price(S_fwd, K, T, r, sigma, OptionType.PUT)
        assert c == pytest.approx(p, abs=1e-10)

    def test_vectorized(self):
        """Numpy array inputs should produce array output."""
        S = np.array([100, 110, 120])
        K = np.array([100, 100, 100])
        prices = black_scholes_price(S, K, 1.0, 0.05, 0.20, OptionType.CALL)
        assert isinstance(prices, np.ndarray)
        assert len(prices) == 3
        assert all(p > 0 for p in prices)

    def test_negative_price_impossible(self):
        price = black_scholes_price(50, 150, 0.01, 0.05, 0.10, OptionType.CALL)
        assert price >= 0

    def test_invalid_inputs_raise(self):
        with pytest.raises(ValueError):
            black_scholes_price(-10, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        with pytest.raises(ValueError):
            black_scholes_price(100, 100, -1.0, 0.05, 0.20, OptionType.CALL)
        with pytest.raises(ValueError):
            black_scholes_price(100, 100, 1.0, 0.05, -0.1, OptionType.CALL)


class TestPutCallParity:
    def test_parity_holds(self, atm_params):
        S, K, T, r, sigma = atm_params["S"], atm_params["K"], atm_params["T"], atm_params["r"], atm_params["sigma"]
        call = black_scholes_price(S, K, T, r, sigma, OptionType.CALL)
        put = black_scholes_price(S, K, T, r, sigma, OptionType.PUT)
        result = put_call_parity_check(call, put, S, K, T, r)
        assert result["satisfied"]
        assert abs(result["difference"]) < 0.01

    def test_parity_with_dividend(self):
        S, K, T, r, sigma, q = 100, 100, 1.0, 0.05, 0.20, 0.02
        call = black_scholes_price(S, K, T, r, sigma, OptionType.CALL, q)
        put = black_scholes_price(S, K, T, r, sigma, OptionType.PUT, q)
        result = put_call_parity_check(call, put, S, K, T, r, q)
        assert result["satisfied"]
