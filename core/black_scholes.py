# Black-Scholes model with Greeks and Implied Volatility
import numpy as np
from scipy.stats import norm
from scipy.optimize import newton


def black_scholes(S, K, T, r, sigma, option_type='call', q=0):
    """
    Calculate Black-Scholes option price with dividend yield adjustment
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (decimal)
    sigma : float
        Volatility (decimal)
    option_type : str
        'call' or 'put'
    q : float
        Dividend yield (decimal)
        
    Returns:
    --------
    price : float
        Option price
    greeks : dict
        Dictionary of option Greeks
    """
    # Input validation
    if S <= 0:
        raise ValueError(f"Stock price S must be positive, got {S}")
    if K <= 0:
        raise ValueError(f"Strike price K must be positive, got {K}")
    if sigma <= 0:
        raise ValueError(f"Volatility sigma must be positive, got {sigma}")
    if option_type not in ('call', 'put'):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")

    T = max(T, 1e-6)  # Avoid division by zero errors
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    
    # Calculate Greeks with proper dividend yield adjustments
    # Delta: accounts for continuous dividend yield
    if option_type == 'call':
        delta = np.exp(-q * T) * norm.cdf(d1)
    else:
        delta = np.exp(-q * T) * (norm.cdf(d1) - 1)

    # Gamma: same for calls and puts
    gamma = np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

    # Theta: per-day time decay
    common_theta = -(S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T))
    if option_type == 'call':
        theta = (common_theta
                 - r * K * np.exp(-r * T) * norm.cdf(d2)
                 + q * S * np.exp(-q * T) * norm.cdf(d1)) / 365
    else:
        theta = (common_theta
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)
                 - q * S * np.exp(-q * T) * norm.cdf(-d1)) / 365

    # Vega: per 1% change in volatility, accounts for dividend yield
    vega = S * np.exp(-q * T) * np.sqrt(T) * norm.pdf(d1) / 100

    # Rho: per 1% change in interest rate
    if option_type == 'call':
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    greeks = {
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'rho': rho
    }
    
    return price, greeks


def implied_volatility(price, S, K, T, r, option_type='call', q=0, initial_guess=0.2):
    """
    Calculate implied volatility using Newton-Raphson method
    
    Parameters:
    -----------
    price : float
        Market option price
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (decimal)
    option_type : str
        'call' or 'put'
    q : float
        Dividend yield (decimal)
    initial_guess : float
        Starting guess for volatility
        
    Returns:
    --------
    iv : float
        Implied volatility (decimal)
    """
    if price <= 0:
        raise ValueError(f"Option price must be positive, got {price}")

    def objective(sigma):
        return black_scholes(S, K, T, r, sigma, option_type, q)[0] - price
    
    try:
        iv = newton(objective, initial_guess, tol=1e-5, maxiter=100)
        if iv <= 0:
            raise RuntimeError("Newton method returned non-positive IV")
        return iv
    except (RuntimeError, ValueError):
        # Fallback to binary search if Newton-Raphson fails
        low, high = 0.001, 5.0
        for _ in range(100):
            mid = (low + high) / 2
            price_diff = black_scholes(S, K, T, r, mid, option_type, q)[0] - price
            if abs(price_diff) < 1e-5:
                return mid
            if price_diff > 0:
                high = mid
            else:
                low = mid
        return mid


def calculate_iv_from_market(market_price: float, S: float, K: float, 
                            T: float, r: float, q: float,
                            option_type: str = 'call') -> float:
    """Calculate implied volatility from market price"""
    return implied_volatility(market_price, S, K, T, r, option_type=option_type, q=q)
