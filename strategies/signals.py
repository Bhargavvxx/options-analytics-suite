"""
Trading-signal generation based on IV / HV comparison and strategy screens.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from analytics.pricing import OptionType, black_scholes_price


@dataclass(frozen=True, slots=True)
class TradingSignal:
    """Structured trading recommendation."""
    volatility_assessment: str
    vol_action: str
    call_assessment: str
    call_action: str
    put_assessment: str
    put_action: str
    recommended_strategy: str
    iv: float
    hv: float
    iv_hv_ratio: float


def generate_trading_signals(
    S: float,
    K: float,
    T: float,
    r: float,
    hv: float,
    iv: float,
    q: float = 0.0,
    *,
    overpriced_threshold: float = 1.10,
    underpriced_threshold: float = 0.90,
    edge_threshold: float = 0.10,
) -> TradingSignal:
    """Generate signals by comparing implied and historical volatility.

    Parameters
    ----------
    hv : float
        Historical (realised) volatility.
    iv : float
        Implied volatility.
    overpriced_threshold, underpriced_threshold : float
        IV / HV ratios used to classify over-/under-priced.
    edge_threshold : float
        Minimum relative price difference to flag a specific option.
    """
    iv_hv = iv / hv if hv > 0 else float("inf")

    # ----- Overall vol signal -----
    if iv_hv > overpriced_threshold:
        vol_assess = "Options overpriced (IV > HV)"
        vol_action = "Consider selling options / volatility"
    elif iv_hv < underpriced_threshold:
        vol_assess = "Options underpriced (IV < HV)"
        vol_action = "Consider buying options / volatility"
    else:
        vol_assess = "Options fairly priced (IV ≈ HV)"
        vol_action = "No clear volatility edge"

    # ----- Per-leg assessment -----
    def _assess(opt_type: str) -> tuple[str, str]:
        hv_px = black_scholes_price(S, K, T, r, hv, opt_type, q, validate=False)
        iv_px = black_scholes_price(S, K, T, r, iv, opt_type, q, validate=False)
        diff = (iv_px - hv_px) / hv_px if hv_px > 0 else 0
        label = opt_type.title() + "s"
        if diff > edge_threshold:
            return f"{label} potentially overpriced", f"Consider selling {opt_type}s or {opt_type} spreads"
        elif diff < -edge_threshold:
            return f"{label} potentially underpriced", f"Consider buying {opt_type}s or {opt_type} spreads"
        return f"{label} fairly priced", f"No clear edge in {opt_type}s"

    call_assess, call_action = _assess("call")
    put_assess, put_action = _assess("put")

    # ----- Strategy recommendation -----
    if iv_hv > overpriced_threshold:
        strategy = "Short Call Spread or Iron Condor"
    elif iv_hv < underpriced_threshold:
        strategy = "Long Straddle or Long Strangle"
    else:
        strategy = "No strong vol signal — consider directional or neutral strategies"

    return TradingSignal(
        volatility_assessment=vol_assess,
        vol_action=vol_action,
        call_assessment=call_assess,
        call_action=call_action,
        put_assessment=put_assess,
        put_action=put_action,
        recommended_strategy=strategy,
        iv=iv,
        hv=hv,
        iv_hv_ratio=iv_hv,
    )
