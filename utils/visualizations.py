# Plotly chart functions for visualizations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.black_scholes import black_scholes, implied_volatility

def plot_option_price_vs_spot(S, K, T, r, sigma, q=0, option_type='call'):
    """
    Plot option price vs spot price
    
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
    option_type : str
        'call' or 'put'
        
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    # Generate spot prices
    spot_range = np.linspace(max(0.5*S, 0.1), 1.5*S, 100)
    
    # Calculate option prices
    option_prices = [black_scholes(s, K, T, r, sigma, option_type, q)[0] for s in spot_range]
    
    # Create plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spot_range, 
        y=option_prices,
        mode='lines',
        name=f'{option_type.title()} Price'
    ))
    
    # Add markers for current spot and strike
    fig.add_trace(go.Scatter(
        x=[S, K],
        y=[black_scholes(S, K, T, r, sigma, option_type, q)[0], black_scholes(K, K, T, r, sigma, option_type, q)[0]],
        mode='markers',
        marker=dict(size=10),
        name='Current Spot & Strike'
    ))
    
    # Customize layout
    fig.update_layout(
        title=f'{option_type.title()} Option Price vs Spot Price',
        xaxis_title='Spot Price',
        yaxis_title=f'{option_type.title()} Option Price',
        hovermode='x unified'
    )
    
    return fig

def plot_option_price_vs_time(S, K, r, sigma, q=0, option_type='call', max_days=365):
    """
    Plot option price vs time to expiry
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    r : float
        Risk-free interest rate (decimal)
    sigma : float
        Volatility (decimal)
    q : float
        Dividend yield (decimal)
    option_type : str
        'call' or 'put'
    max_days : int
        Maximum days to expiry to plot
        
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    # Generate time range
    days_range = np.linspace(1, max_days, 100)
    time_range = days_range / 365.0  # Convert to years
    
    # Calculate option prices
    option_prices = [black_scholes(S, K, t, r, sigma, option_type, q)[0] for t in time_range]
    
    # Create plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days_range, 
        y=option_prices,
        mode='lines',
        name=f'{option_type.title()} Price'
    ))
    
    # Customize layout
    fig.update_layout(
        title=f'{option_type.title()} Option Price vs Time to Expiry',
        xaxis_title='Time to Expiry (days)',
        yaxis_title=f'{option_type.title()} Option Price',
        hovermode='x unified'
    )
    
    return fig

def plot_iv_surface(S, K, r, q=0, option_chains=None):
    """
    Create an implied volatility surface plot.
    Uses real market data when option_chains is provided, otherwise uses
    a simulated skew/smile model.
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    r : float
        Risk-free interest rate (decimal)
    q : float
        Dividend yield (decimal)
    option_chains : dict, optional
        Dict mapping expiry strings to (calls_df, puts_df) tuples.
        Each calls_df must have 'strike' and 'impliedVolatility' columns.
        
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    if option_chains:
        # Build IV surface from real market data
        all_strikes = set()
        expiry_list = sorted(option_chains.keys())
        for expiry, (calls, _puts) in option_chains.items():
            if not calls.empty and 'strike' in calls.columns:
                all_strikes.update(calls['strike'].values)
        
        if all_strikes and len(expiry_list) >= 2:
            strikes = np.array(sorted(all_strikes))
            # Filter to reasonable range around ATM
            mask = (strikes >= 0.7 * S) & (strikes <= 1.3 * S)
            strikes = strikes[mask]
            
            from datetime import datetime
            times = []
            for exp in expiry_list:
                try:
                    days = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
                    times.append(max(days, 1) / 365.0)
                except ValueError:
                    continue
            
            if len(times) >= 2 and len(strikes) >= 2:
                strike_grid, time_grid = np.meshgrid(strikes, times)
                iv_surface = np.full_like(strike_grid, np.nan)
                
                for i, (expiry, T_val) in enumerate(zip(expiry_list, times)):
                    calls, _puts = option_chains[expiry]
                    if calls.empty:
                        continue
                    for j, strike in enumerate(strikes):
                        match = calls[calls['strike'] == strike]
                        if not match.empty and 'impliedVolatility' in match.columns:
                            iv_val = match['impliedVolatility'].values[0]
                            if iv_val > 0:
                                iv_surface[i, j] = iv_val
                
                # Interpolate NaN values
                from scipy.interpolate import griddata
                valid = ~np.isnan(iv_surface)
                if valid.sum() > 3:
                    points = np.array([strike_grid[valid], time_grid[valid]]).T
                    values = iv_surface[valid]
                    iv_surface = griddata(points, values,
                                         (strike_grid, time_grid), method='linear')
                    # Fill remaining NaN with nearest
                    still_nan = np.isnan(iv_surface)
                    if still_nan.any():
                        iv_surface[still_nan] = griddata(
                            points, values,
                            (strike_grid[still_nan], time_grid[still_nan]),
                            method='nearest'
                        )
                
                fig = go.Figure(data=[go.Surface(
                    x=strike_grid, y=time_grid, z=iv_surface,
                    colorscale='Viridis'
                )])
                fig.update_layout(
                    title='Implied Volatility Surface (Market Data)',
                    scene=dict(
                        xaxis_title='Strike Price',
                        yaxis_title='Time to Expiry (years)',
                        zaxis_title='Implied Volatility',
                        camera=dict(eye=dict(x=1.5, y=-1.5, z=1)),
                    ),
                    width=800, height=600,
                    margin=dict(l=65, r=50, b=65, t=90)
                )
                return fig

    # Fallback: simulated IV surface with smile/skew
    strikes = np.linspace(0.7*S, 1.3*S, 20)
    times = np.linspace(0.1, 2, 20)  # years
    strike_grid, time_grid = np.meshgrid(strikes, times)
    
    iv_surface = np.zeros_like(strike_grid)
    for i in range(strike_grid.shape[0]):
        for j in range(strike_grid.shape[1]):
            strike_effect = 0.05 * abs((strike_grid[i, j] / S) - 1) 
            time_effect = 0.03 * (1 - np.exp(-time_grid[i, j]))
            iv_surface[i, j] = 0.2 + strike_effect + time_effect
    
    fig = go.Figure(data=[go.Surface(
        x=strike_grid, y=time_grid, z=iv_surface,
        colorscale='Viridis'
    )])
    fig.update_layout(
        title='Implied Volatility Surface (Simulated)',
        scene=dict(
            xaxis_title='Strike Price',
            yaxis_title='Time to Expiry (years)',
            zaxis_title='Implied Volatility',
            camera=dict(eye=dict(x=1.5, y=-1.5, z=1)),
        ),
        width=800, height=600,
        margin=dict(l=65, r=50, b=65, t=90)
    )
    return fig

def plot_strategy_payoff(S, K, T, r, sigma, q=0, strategy='long_call'):
    """
    Plot payoff diagram for an option strategy
    
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
    strategy : str
        Strategy type ('long_call', 'long_put', 'straddle', etc.)
        
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    # Generate spot range
    spot_range = np.linspace(max(0.5*K, 0.1), 1.5*K, 100)
    
    # Strategy-specific payoff calculations
    strategies = {
        'long_call': {
            'entry': black_scholes(S, K, T, r, sigma, 'call', q)[0],
            'payoff': lambda s, entry: np.maximum(s - K, 0) - entry
        },
        'long_put': {
            'entry': black_scholes(S, K, T, r, sigma, 'put', q)[0],
            'payoff': lambda s, entry: np.maximum(K - s, 0) - entry
        },
        'straddle': {
            'entry': black_scholes(S, K, T, r, sigma, 'call', q)[0] + black_scholes(S, K, T, r, sigma, 'put', q)[0],
            'payoff': lambda s, entry: np.maximum(s - K, 0) + np.maximum(K - s, 0) - entry
        },
        'strangle': {
            'entry': black_scholes(S, K*1.1, T, r, sigma, 'call', q)[0] + black_scholes(S, K*0.9, T, r, sigma, 'put', q)[0],
            'payoff': lambda s, entry: np.maximum(s - K*1.1, 0) + np.maximum(K*0.9 - s, 0) - entry
        },
        'bull_call_spread': {
            'entry': black_scholes(S, K, T, r, sigma, 'call', q)[0] - black_scholes(S, K*1.1, T, r, sigma, 'call', q)[0],
            'payoff': lambda s, entry: np.minimum(np.maximum(s - K, 0), 0.1*K) - entry
        }
    }
    
    if strategy not in strategies:
        raise ValueError(f"Strategy '{strategy}' not implemented")
    
    strategy_entry = strategies[strategy]['entry']
    payoff = strategies[strategy]['payoff'](spot_range, strategy_entry)
    
    # Create plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spot_range, 
        y=payoff,
        mode='lines',
        name=f'{strategy.replace("_", " ").title()} Payoff'
    ))
    
    # Add breakeven points and max profit/loss
    fig.add_hline(y=0, line=dict(color='black', width=1, dash='dash'))
    fig.add_vline(x=K, line=dict(color='gray', width=1, dash='dash'))
    
    # Add current spot price marker
    fig.add_trace(go.Scatter(
        x=[S],
        y=[strategies[strategy]['payoff'](np.array([S]), strategy_entry)[0]],
        mode='markers',
        marker=dict(size=10, color='red'),
        name='Current Spot'
    ))
    
    # Customize layout
    fig.update_layout(
        title=f'{strategy.replace("_", " ").title()} Strategy Payoff Diagram',
        xaxis_title='Underlying Price at Expiration',
        yaxis_title='Profit/Loss',
        hovermode='x unified'
    )
    
    return fig

def plot_backtesting_results(results):
    """
    Plot backtesting results
    
    Parameters:
    -----------
    results : pandas.DataFrame
        DataFrame of backtesting results
        
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    if results.empty:
        return go.Figure()
    
    # Create subplot figure
    fig = make_subplots(rows=3, cols=1, 
                       shared_xaxes=True,
                       subplot_titles=('Underlying Price', 'Volatility Comparison', 'Strategy Returns'),
                       vertical_spacing=0.1,
                       row_heights=[0.3, 0.3, 0.4])
    
    # Add price chart
    fig.add_trace(go.Scatter(
        x=results.index, 
        y=results['Price'],
        mode='lines',
        name='Price'
    ), row=1, col=1)
    
    # Add volatility comparison
    if 'HV' in results.columns and 'IV' in results.columns:
        fig.add_trace(go.Scatter(
            x=results.index, 
            y=results['HV'],
            mode='lines',
            name='Historical Volatility'
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=results.index, 
            y=results['IV'],
            mode='lines',
            name='Implied Volatility'
        ), row=2, col=1)
    
    # Add strategy returns
    if 'Cumulative_Return' in results.columns:
        fig.add_trace(go.Scatter(
            x=results.index, 
            y=results['Cumulative_Return'],
            mode='lines',
            name='Strategy Returns'
        ), row=3, col=1)
    
    # Customize layout
    fig.update_layout(
        title='Backtesting Results',
        height=800,
        hovermode='x unified'
    )
    
    return fig

def plot_realtime_vs_model(calls: pd.DataFrame, puts: pd.DataFrame, 
                         strike: float, model_price: float) -> go.Figure:
    """Plot real-time market prices vs model prediction"""
    fig = go.Figure()
    
    # Add market prices
    for option_type, df in [('Call', calls), ('Put', puts)]:
        fig.add_trace(go.Scatter(
            x=df['strike'],
            y=(df['bid'] + df['ask'])/2,
            mode='lines',
            name=f'Market {option_type}'
        ))
    
    # Add model prediction
    fig.add_trace(go.Scatter(
        x=[strike],
        y=[model_price],
        mode='markers',
        marker=dict(size=15, color='red'),
        name='Model Price'
    ))
    
    fig.update_layout(
        title='Real-Time Market Prices vs Model Prediction',
        xaxis_title='Strike Price',
        yaxis_title='Option Price',
        hovermode='x unified'
    )
    return fig
def plot_ml_comparison(current_price, predictions):
    """Plot comparison of ML predictions with current price"""
    import plotly.graph_objects as go
    
    # Convert predictions to scalars if they're pandas objects
    pred_values = []
    for model, value in predictions.items():
        if hasattr(value, 'iloc'):
            pred_values.append(float(value.iloc[0]))  # Get first element if Series/DataFrame
        else:
            pred_values.append(float(value))
    
    models = list(predictions.keys())
    
    fig = go.Figure()
    
    # Add current price line
    fig.add_shape(
        type="line",
        x0=-0.5,
        y0=current_price,
        x1=len(models)-0.5,
        y1=current_price,
        line=dict(color="red", width=2, dash="dash"),
    )
    
    # Add model predictions as bars
    fig.add_trace(go.Bar(
        x=models,
        y=pred_values,
        text=[f"${p:.2f}" for p in pred_values],
        textposition='auto',
        marker_color=['lightgreen' if p > current_price else 'salmon' for p in pred_values]
    ))
    
    # Add annotations
    fig.update_layout(
        title='ML Model Predictions vs Current Price',
        xaxis_title='Model',
        yaxis_title='Price',
        showlegend=False,
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )
    
    return fig

