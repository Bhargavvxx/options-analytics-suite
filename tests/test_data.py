"""Tests for data layer."""
import pytest
import numpy as np
import pandas as pd

from data.cache import DataCache
from data.normalization import validate_ohlcv, normalize_option_chain, safe_mid_price


class TestDataCache:
    def test_set_get(self):
        cache = DataCache(default_ttl=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_miss_returns_none(self):
        cache = DataCache(default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = DataCache(default_ttl=60)
        cache.set("key", "value")
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_clear(self):
        cache = DataCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestValidateOHLCV:
    def test_happy_path(self):
        df = pd.DataFrame({
            "Open": [100.0], "High": [101.0], "Low": [99.0],
            "Close": [100.5], "Volume": [1000],
        }, index=pd.to_datetime(["2024-01-01"]))
        result = validate_ohlcv(df)
        assert len(result) == 1

    def test_drops_nan_close(self):
        df = pd.DataFrame({
            "Close": [100.0, np.nan, 101.0],
        }, index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
        result = validate_ohlcv(df)
        assert len(result) == 2


class TestNormalizeChain:
    def test_adds_mid(self):
        df = pd.DataFrame({
            "strike": [100], "bid": [2.0], "ask": [2.5],
            "lastPrice": [2.3], "impliedVolatility": [0.20],
        })
        result = normalize_option_chain(df)
        assert "mid" in result.columns
        assert result["mid"].iloc[0] == pytest.approx(2.25)


class TestSafeMidPrice:
    def test_mid_from_bid_ask(self):
        calls = pd.DataFrame({"strike": [100.0], "bid": [2.0], "ask": [3.0], "lastPrice": [2.4]})
        puts = pd.DataFrame({"strike": [100.0], "bid": [1.0], "ask": [1.5], "lastPrice": [1.2]})
        mid = safe_mid_price(calls, puts, 100.0, "call")
        assert mid == pytest.approx(2.5)

    def test_fallback_to_last(self):
        calls = pd.DataFrame({"strike": [100.0], "bid": [0.0], "ask": [0.0], "lastPrice": [2.4]})
        puts = pd.DataFrame({"strike": [100.0], "bid": [1.0], "ask": [1.5], "lastPrice": [1.2]})
        mid = safe_mid_price(calls, puts, 100.0, "call")
        assert mid == pytest.approx(2.4)
