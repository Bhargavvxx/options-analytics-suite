"""
Educational simulation backtest.

⚠️  This module uses **simulated** data (GBM paths) to illustrate
strategy mechanics.  It does NOT use real market data and should be
treated as a teaching tool only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from analytics.pricing import OptionType, black_scholes_price
from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Payload returned by educational simulation."""
    price_paths: np.ndarray       # shape (n_paths, n_steps)
    payoffs: np.ndarray           # shape (n_paths,)
    mean_payoff: float
    std_payoff: float
    pv_mean_payoff: float
    parameters: dict


def run_educational_simulation(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    *,
    n_paths: int = 5_000,
    n_steps: int = 252,
    seed: Optional[int] = 42,
) -> SimulationResult:
    """Monte-Carlo simulation for educational purposes.

    Generates GBM price paths, computes terminal payoffs, and discounts
    back to present value.  Results can be compared with the closed-form
    Black-Scholes price.

    .. warning::
        This uses simulated random paths, **not** real market data.
    """
    rng = np.random.default_rng(seed)
    dt = T / n_steps

    # Antithetic variates for variance reduction
    z = rng.standard_normal((n_paths // 2, n_steps))
    z = np.concatenate([z, -z], axis=0)  # shape (n_paths, n_steps)

    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * z

    log_returns = drift + diffusion
    log_paths = np.cumsum(log_returns, axis=1)
    # Prepend S0
    paths = S0 * np.exp(np.column_stack([np.zeros(n_paths), log_paths]))

    S_T = paths[:, -1]

    opt = OptionType.CALL if option_type == "call" else OptionType.PUT
    if opt is OptionType.CALL:
        payoffs = np.maximum(S_T - K, 0.0)
    else:
        payoffs = np.maximum(K - S_T, 0.0)

    mean_payoff = float(payoffs.mean())
    std_payoff = float(payoffs.std())
    pv = mean_payoff * np.exp(-r * T)

    bs_price = black_scholes_price(S0, K, T, r, sigma, opt)
    logger.info(
        "Simulation complete: MC price=%.4f vs BS=%.4f (diff=%.4f)",
        pv,
        bs_price,
        pv - bs_price,
    )

    return SimulationResult(
        price_paths=paths,
        payoffs=payoffs,
        mean_payoff=mean_payoff,
        std_payoff=std_payoff,
        pv_mean_payoff=pv,
        parameters={
            "S0": S0, "K": K, "T": T, "r": r, "sigma": sigma,
            "option_type": option_type, "n_paths": n_paths,
            "n_steps": n_steps, "bs_price": bs_price,
        },
    )
