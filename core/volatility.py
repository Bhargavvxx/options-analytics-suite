# Volatility calculation code (Historical, EWMA, GARCH)
import numpy as np
import pandas as pd
from arch import arch_model


def historical_volatility(returns, window=30, annualize=True):
    """
    Calculate historical volatility
    
    Parameters:
    -----------
    returns : pandas.Series
        Series of returns
    window : int
        Window size for rolling calculation
    annualize : bool
        Whether to annualize the volatility
        
    Returns:
    --------
    volatility : pandas.Series
        Series of historical volatility
    """
    vol = returns.rolling(window=window).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


def ewma_volatility(returns, lambda_=0.94, annualize=True):
    """
    Calculate EWMA volatility
    
    Parameters:
    -----------
    returns : array-like
        Series of returns
    lambda_ : float
        Decay factor
    annualize : bool
        Whether to annualize the volatility
        
    Returns:
    --------
    volatility : float
        EWMA volatility (annualized by default)
    """
    returns = np.asarray(returns)
    weights = np.array([(1 - lambda_) * lambda_**i for i in range(len(returns))])
    weights = weights[::-1] / weights.sum()
    daily_vol = np.sqrt(np.sum(weights * returns**2))
    if annualize:
        return daily_vol * np.sqrt(252)
    return daily_vol


def garch_volatility(returns, p=1, q=1):
    """
    Calculate GARCH volatility
    
    Parameters:
    -----------
    returns : array-like
        Series of returns
    p : int
        GARCH lag order
    q : int
        ARCH lag order
        
    Returns:
    --------
    volatility : float
        GARCH volatility forecast (annualized)
    """
    try:
        returns_arr = np.asarray(returns)
        scaled_returns = returns_arr * 100  # Scale for numerical stability
        model = arch_model(scaled_returns, vol='GARCH', p=p, q=q)
        result = model.fit(disp='off')
        forecast = result.forecast(horizon=1)
        return forecast.variance.iloc[-1, 0]**0.5 / 100  # Back to original scale
    except Exception as e:
        # Fallback to historical volatility if GARCH fails
        print(f"GARCH fitting failed, falling back to historical vol: {e}")
        return float(np.std(np.asarray(returns)) * np.sqrt(252))
