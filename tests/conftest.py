"""Shared pytest fixtures."""
import pytest


@pytest.fixture
def atm_params():
    """Standard ATM test parameters."""
    return dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)


@pytest.fixture
def otm_call_params():
    return dict(S=100.0, K=110.0, T=0.5, r=0.05, sigma=0.25)


@pytest.fixture
def itm_put_params():
    return dict(S=100.0, K=110.0, T=0.5, r=0.05, sigma=0.25)
