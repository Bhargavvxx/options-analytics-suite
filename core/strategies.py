# Strategy logic and signal generation
import numpy as np
from core.black_scholes import black_scholes

def get_option_strategies(S, K, T, r, sigma, q=0):
    """
    Calculate prices for common option strategies
    
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
    q : float
        Dividend yield (decimal)
        
    Returns:
    --------
    strategies : dict
        Dictionary of strategy prices
    """
    # Calculate individual option prices
    call_atm_price = black_scholes(S, K, T, r, sigma, 'call', q)[0]
    put_atm_price = black_scholes(S, K, T, r, sigma, 'put', q)[0]
    
    call_itm_price = black_scholes(S, K*0.9, T, r, sigma, 'call', q)[0]
    put_itm_price = black_scholes(S, K*1.1, T, r, sigma, 'put', q)[0]
    
    call_otm_price = black_scholes(S, K*1.1, T, r, sigma, 'call', q)[0]
    put_otm_price = black_scholes(S, K*0.9, T, r, sigma, 'put', q)[0]
    
    # Strategy prices
    strategies = {
        'Long Call': call_atm_price,
        'Long Put': put_atm_price,
        'Straddle': call_atm_price + put_atm_price,
        'Strangle': call_otm_price + put_otm_price,
        'Bull Call Spread': call_atm_price - call_otm_price,
        'Bear Put Spread': put_atm_price - put_otm_price,
        'Butterfly': call_itm_price - 2*call_atm_price + call_otm_price,
        'Iron Condor': (call_otm_price - call_atm_price) + (put_otm_price - put_atm_price),
        'Protective Put': S + put_atm_price,
        'Covered Call': S - call_atm_price
    }
    
    return strategies

def get_trading_signals(S, K, T, r, hv, iv, q=0):
    """
    Generate trading signals based on historical vs. implied volatility
    
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
    hv : float
        Historical volatility (decimal)
    iv : float
        Implied volatility (decimal)
    q : float
        Dividend yield (decimal)
        
    Returns:
    --------
    signals : dict
        Dictionary of trading signals and recommendations
    """
    # Calculate fair prices using historical volatility
    hv_call_price = black_scholes(S, K, T, r, hv, 'call', q)[0]
    hv_put_price = black_scholes(S, K, T, r, hv, 'put', q)[0]
    
    # Calculate market prices using implied volatility
    iv_call_price = black_scholes(S, K, T, r, iv, 'call', q)[0]
    iv_put_price = black_scholes(S, K, T, r, iv, 'put', q)[0]
    
    # Calculate differences
    call_diff = (iv_call_price - hv_call_price) / hv_call_price if hv_call_price > 0 else 0
    put_diff = (iv_put_price - hv_put_price) / hv_put_price if hv_put_price > 0 else 0
    
    # Generate signals
    signals = {}
    
    # Overall volatility signal
    if iv > hv * 1.1:
        signals['volatility'] = 'Options overpriced (IV > HV)'
        signals['vol_action'] = 'Consider selling options/volatility'
    elif iv < hv * 0.9:
        signals['volatility'] = 'Options underpriced (IV < HV)'
        signals['vol_action'] = 'Consider buying options/volatility'
    else:
        signals['volatility'] = 'Options fairly priced (IV ≈ HV)'
        signals['vol_action'] = 'No clear volatility edge'
    
    # Specific option signals
    if call_diff > 0.1:
        signals['call'] = 'Calls potentially overpriced'
        signals['call_action'] = 'Consider selling calls or call spreads'
    elif call_diff < -0.1:
        signals['call'] = 'Calls potentially underpriced'
        signals['call_action'] = 'Consider buying calls or call spreads'
    else:
        signals['call'] = 'Calls fairly priced'
        signals['call_action'] = 'No clear edge in calls'
        
    if put_diff > 0.1:
        signals['put'] = 'Puts potentially overpriced'
        signals['put_action'] = 'Consider selling puts or put spreads'
    elif put_diff < -0.1:
        signals['put'] = 'Puts potentially underpriced'
        signals['put_action'] = 'Consider buying puts or put spreads'
    else:
        signals['put'] = 'Puts fairly priced'
        signals['put_action'] = 'No clear edge in puts'
    
    # Strategy recommendations
    if iv > hv * 1.1:
        if abs(call_diff) > abs(put_diff):
            signals['strategy'] = 'Short Call Spread or Covered Call'
        else:
            signals['strategy'] = 'Short Put Spread or Cash-Secured Put'
    elif iv < hv * 0.9:
        if abs(call_diff) > abs(put_diff):
            signals['strategy'] = 'Long Call or Bull Call Spread'
        else:
            signals['strategy'] = 'Long Put or Bear Put Spread'
    else:
        signals['strategy'] = 'No strong directional or volatility signal'
    
    return signals
