"""
Analytics engine — pricing, Greeks, implied volatility, volatility models,
American pricing, rate curves, and surface arbitrage diagnostics.
"""
from analytics.pricing import black_scholes_price, put_call_parity_check, OptionType
from analytics.greeks import analytical_greeks, finite_difference_greeks, Greeks
from analytics.implied_vol import (
    solve_iv, batch_solve_iv, IVResult, IVMethod,
)
from analytics.volatility import (
    historical_volatility,
    ewma_volatility,
    garch_volatility,
    realised_vol_cone,
    detect_vol_regime,
)
from analytics.day_count import year_fraction, DayCountConvention
from analytics.iv_surface import SurfaceQC
from analytics.american import binomial_price, BinomialResult, ExerciseStyle, DividendSchedule
from analytics.rates import RateCurve, flat_curve, build_curve
from analytics.arbitrage import surface_arbitrage_check, SurfaceArbitrageReport

__all__ = [
    "black_scholes_price",
    "put_call_parity_check",
    "OptionType",
    "analytical_greeks",
    "finite_difference_greeks",
    "Greeks",
    "solve_iv",
    "batch_solve_iv",
    "IVResult",
    "IVMethod",
    "historical_volatility",
    "ewma_volatility",
    "garch_volatility",
    "realised_vol_cone",
    "detect_vol_regime",
    "year_fraction",
    "DayCountConvention",
    "SurfaceQC",
    "binomial_price",
    "BinomialResult",
    "ExerciseStyle",
    "DividendSchedule",
    "RateCurve",
    "flat_curve",
    "build_curve",
    "surface_arbitrage_check",
    "SurfaceArbitrageReport",
]
