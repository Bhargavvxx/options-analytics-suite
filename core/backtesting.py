# Backtesting functions
import numpy as np
import pandas as pd
from core.black_scholes import black_scholes


def backtest_vol_strategy(hist_data, window=21, annualization=252):
    """
    Backtest a volatility-based trading strategy

    Parameters:
    -----------
    hist_data : pandas.Series
        Series of historical prices
    window : int
        Window size for historical volatility calculation
    annualization : int
        Annualization factor (252 for daily data)

    Returns:
    --------
    results : pandas.DataFrame
        DataFrame of backtest results
    """
    if len(hist_data) < window + 10:
        return pd.DataFrame()

    # Validate input data
    if isinstance(hist_data, pd.DataFrame):
        if len(hist_data.columns) == 1:
            hist_data = hist_data.squeeze()  # Convert single-column DF to Series
        else:
            raise ValueError("Input must be a single-column DataFrame or Series")
    elif not isinstance(hist_data, pd.Series):
        hist_data = pd.Series(hist_data)

    # Calculate returns
    returns = hist_data.pct_change().dropna()

    # Calculate historical volatility
    hv = returns.rolling(window).std() * np.sqrt(annualization)

    # Generate synthetic implied volatility with fixed seed for reproducibility
    hv_series = hv.dropna()
    rng = np.random.default_rng(seed=42)
    iv = hv_series + rng.normal(0, 0.02, len(hv_series))
    iv = pd.Series(iv, index=hv_series.index).abs()

    # Align indices
    iv_aligned, hv_aligned = iv.align(hv_series, join='inner', axis=0)

    # Generate trading signals
    signals = pd.Series(0, index=iv_aligned.index)
    signals[(iv_aligned < hv_aligned * 0.9)] = 1  # Buy when IV < 90% of HV
    signals[(iv_aligned > hv_aligned * 1.1)] = -1  # Sell when IV > 110% of HV

    # Calculate strategy returns
    vol_changes = hv_aligned.diff().fillna(0)
    option_returns = vol_changes * 5  # Assuming 5x leverage
    strategy_returns = signals * option_returns

    # Prepare results with aligned data
    results = pd.DataFrame({
        'Price': hist_data.reindex(iv_aligned.index),
        'Returns': returns.reindex(iv_aligned.index),
        'HV': hv_aligned,
        'IV': iv_aligned,
        'Signal': signals,
        'Option_Return': option_returns,
        'Strategy_Return': strategy_returns,
        'Cumulative_Return': strategy_returns.cumsum()
    }).dropna()

    return results


def backtest_option_strategy(hist_data, strategy, K, T, r, sigma, q=0):
    """
    Backtest a specific option strategy

    Parameters:
    -----------
    hist_data : pandas.Series
        Series of historical prices
    strategy : str
        Strategy name ('long_call', 'long_put', 'straddle', etc.)
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (decimal)
    sigma : float
        Volatility (decimal)
    q : float
        Dividend yield (decimal)

    Returns:
    --------
    results : pandas.DataFrame
        DataFrame of backtest results
    """
    # Validate input data
    if isinstance(hist_data, pd.DataFrame):
        if len(hist_data.columns) == 1:
            hist_data = hist_data.squeeze()  # Convert single-column DF to Series
        else:
            raise ValueError("Input must be a single-column DataFrame or Series")
    elif not isinstance(hist_data, pd.Series):
        hist_data = pd.Series(hist_data)

    # Strategy mappings with vectorized operations
    strategies = {
        'long_call': lambda S: black_scholes(S, K, T, r, sigma, 'call', q)[0],
        'long_put': lambda S: black_scholes(S, K, T, r, sigma, 'put', q)[0],
        'straddle': lambda S: (black_scholes(S, K, T, r, sigma, 'call', q)[0] + 
                              black_scholes(S, K, T, r, sigma, 'put', q)[0]),
        'strangle': lambda S: (black_scholes(S, K*1.05, T, r, sigma, 'call', q)[0] + 
                              black_scholes(S, K*0.95, T, r, sigma, 'put', q)[0])
    }

    if strategy not in strategies:
        raise ValueError(f"Strategy '{strategy}' not implemented")

    # Calculate strategy prices using vectorized operations
    option_prices = hist_data.apply(strategies[strategy])

    # Calculate strategy returns
    option_returns = option_prices.pct_change().fillna(0)

    # Prepare results
    results = pd.DataFrame({
        'Price': hist_data,
        'Option_Price': option_prices,
        'Option_Return': option_returns,
        'Strategy_Return': option_returns,
        'Cumulative_Return': (1 + option_returns).cumprod() - 1
    }).dropna()

    return results