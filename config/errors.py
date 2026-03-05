"""
Central custom exceptions for the Option Analytics Suite.

Import from ``config.errors`` in any module that needs structured
error reporting instead of bare ``Exception`` / ``RuntimeError``.
"""
from __future__ import annotations


class OASError(Exception):
    """Base class for all Option Analytics Suite errors."""


class DataFetchError(OASError):
    """Raised when market-data retrieval fails after all retries."""


class SolverError(OASError):
    """Raised when an IV or numerical solver cannot converge."""


class SurfaceBuildError(OASError):
    """Raised when building an IV surface fails structurally."""


class BacktestConfigError(OASError):
    """Raised for invalid backtesting configuration."""


class ExecutionError(OASError):
    """Raised for invalid fill / execution conditions (e.g. crossed market)."""
