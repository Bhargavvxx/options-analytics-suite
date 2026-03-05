"""Tests for analytics.greeks — analytical and finite-difference Greeks."""
import pytest
from analytics.pricing import OptionType
from analytics.greeks import analytical_greeks, finite_difference_greeks


class TestAnalyticalGreeks:
    def test_call_delta_range(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        assert 0 < g.delta < 1

    def test_put_delta_range(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.PUT)
        assert -1 < g.delta < 0

    def test_gamma_positive(self, atm_params):
        for opt in (OptionType.CALL, OptionType.PUT):
            g = analytical_greeks(**atm_params, option_type=opt)
            assert g.gamma > 0

    def test_call_put_gamma_equal(self, atm_params):
        gc = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        gp = analytical_greeks(**atm_params, option_type=OptionType.PUT)
        assert gc.gamma == pytest.approx(gp.gamma, abs=1e-10)

    def test_vega_positive(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        assert g.vega > 0

    def test_call_put_vega_equal(self, atm_params):
        gc = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        gp = analytical_greeks(**atm_params, option_type=OptionType.PUT)
        assert gc.vega == pytest.approx(gp.vega, abs=1e-10)

    def test_theta_negative_for_long(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        assert g.theta < 0  # time decay hurts long positions

    def test_call_rho_positive(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        assert g.rho > 0

    def test_put_rho_negative(self, atm_params):
        g = analytical_greeks(**atm_params, option_type=OptionType.PUT)
        assert g.rho < 0


class TestFiniteDifferenceGreeks:
    """FD Greeks should closely match analytical Greeks."""

    def test_fd_matches_analytical(self, atm_params):
        a = analytical_greeks(**atm_params, option_type=OptionType.CALL)
        f = finite_difference_greeks(**atm_params, option_type=OptionType.CALL)
        assert f.delta == pytest.approx(a.delta, abs=0.005)
        assert f.gamma == pytest.approx(a.gamma, abs=0.005)
        assert f.theta == pytest.approx(a.theta, abs=0.05)
        assert f.vega == pytest.approx(a.vega, abs=0.05)
        assert f.rho == pytest.approx(a.rho, abs=0.05)

    def test_fd_put(self, atm_params):
        a = analytical_greeks(**atm_params, option_type=OptionType.PUT)
        f = finite_difference_greeks(**atm_params, option_type=OptionType.PUT)
        assert f.delta == pytest.approx(a.delta, abs=0.005)
