"""
Market-data adapter layer.

Defines an **abstract** ``MarketDataProvider`` interface and a concrete
``YFinanceProvider`` implementation.  Other sources (IBKR, Polygon, etc.)
can plug in by subclassing the ABC.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.logging_config import get_logger
from config.settings import Settings
from config.errors import DataFetchError

logger = get_logger(__name__)
_CFG = Settings()


# ---------------------------------------------------------------------------
# Metadata envelope
# ---------------------------------------------------------------------------

@dataclass
class DataMeta:
    """Provenance metadata attached to every fetch result."""
    source: str
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    ticker: str = ""
    is_delayed: bool = True
    stale: bool = False


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class MarketDataProvider(abc.ABC):
    """Abstract interface for market-data backends."""

    @abc.abstractmethod
    def get_stock_data(
        self, ticker: str, period: str = "2y", interval: str = "1d",
    ) -> Tuple[pd.DataFrame, DataMeta]:
        ...

    @abc.abstractmethod
    def get_option_chain(
        self, ticker: str, expiry: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, DataMeta]:
        ...

    @abc.abstractmethod
    def get_available_expiries(self, ticker: str) -> List[str]:
        ...

    @abc.abstractmethod
    def get_risk_free_rate(self, maturity: str = "10y") -> Tuple[float, DataMeta]:
        ...


# ---------------------------------------------------------------------------
# yfinance implementation
# ---------------------------------------------------------------------------

class YFinanceProvider(MarketDataProvider):
    """Concrete implementation backed by the ``yfinance`` library."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    # -- helpers -----------------------------------------------------------

    def _retry(self, fn, *args, **kwargs):
        """Call *fn* with retries and exponential back-off."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt, self._max_retries, fn.__name__, exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay * attempt)
        raise DataFetchError(
            f"All {self._max_retries} retries exhausted"
        ) from last_exc

    # -- public API --------------------------------------------------------

    def get_stock_data(
        self, ticker: str, period: str = "2y", interval: str = "1d",
    ) -> Tuple[pd.DataFrame, DataMeta]:
        import yfinance as yf

        meta = DataMeta(source="yfinance", ticker=ticker)

        def _fetch():
            return yf.download(ticker, period=period, interval=interval, progress=False)

        data = self._retry(_fetch)
        if data.empty:
            logger.warning("Empty OHLCV for %s (period=%s)", ticker, period)
        return data, meta

    def get_option_chain(
        self, ticker: str, expiry: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, DataMeta]:
        import yfinance as yf

        meta = DataMeta(source="yfinance", ticker=ticker)

        def _fetch():
            stock = yf.Ticker(ticker)
            if expiry is None:
                if len(stock.options) == 0:
                    return pd.DataFrame(), pd.DataFrame()
                exp = stock.options[0]
            else:
                exp = expiry
            chain = stock.option_chain(exp)
            return chain.calls, chain.puts

        calls, puts = self._retry(_fetch)
        return calls, puts, meta

    def get_available_expiries(self, ticker: str) -> List[str]:
        import yfinance as yf

        def _fetch():
            stock = yf.Ticker(ticker)
            return list(stock.options)

        try:
            return self._retry(_fetch)
        except Exception as exc:
            logger.error("Failed to fetch expiries for %s: %s", ticker, exc)
            return []

    def get_risk_free_rate(self, maturity: str = "10y") -> Tuple[float, DataMeta]:
        import yfinance as yf

        tickers = _CFG.treasury_tickers
        meta = DataMeta(source="yfinance_treasury", ticker=tickers.get(maturity, ""))

        if maturity not in tickers:
            logger.warning("Unsupported maturity '%s'; using default %.2f%%",
                           maturity, _CFG.default_risk_free_rate * 100)
            return _CFG.default_risk_free_rate, meta

        def _fetch():
            data = yf.download(tickers[maturity], period="5d", progress=False)
            if data.empty:
                return None
            return data["Close"].dropna().iloc[-1] / 100.0

        try:
            rate = self._retry(_fetch)
            if rate is None:
                rate = _CFG.default_risk_free_rate
                meta.stale = True
            return float(rate), meta
        except Exception as exc:
            logger.error("Risk-free rate fetch failed: %s", exc)
            meta.stale = True
            return _CFG.default_risk_free_rate, meta


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_provider: Optional[MarketDataProvider] = None


def get_default_provider() -> MarketDataProvider:
    """Return (and lazily create) the default provider singleton."""
    global _default_provider
    if _default_provider is None:
        _default_provider = YFinanceProvider(
            max_retries=_CFG.data_max_retries,
            retry_delay=_CFG.data_retry_delay_seconds,
        )
    return _default_provider
