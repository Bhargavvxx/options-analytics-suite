# Functions for fetching stock and option data
import yfinance as yf
import pandas as pd
import numpy as np
from utils.realtime_data import get_realtime_option_chain, get_option_mid_price


def get_stock_data(ticker, period="2y", interval="1d"):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def get_risk_free_rate(method="treasury", maturity="10y"):
    # Mapping of maturity to Yahoo Finance ticker
    # Note: Yahoo Finance does not have a 2Y Treasury ticker
    treasury_tickers = {
        "3m": "^IRX",   # 13-Week Treasury Bill
        "5y": "^FVX",   # 5-Year Treasury Yield
        "10y": "^TNX",  # 10-Year Treasury Yield
        "30y": "^TYX"   # 30-Year Treasury Yield
    }
    
    try:
        if method == "treasury" and maturity in treasury_tickers:
            data = yf.download(treasury_tickers[maturity], period="5d", progress=False)
            if data.empty:
                return pd.Series([0.045])
            rate = data['Close'].dropna().iloc[-1] / 100  # Convert from percentage to decimal
            return rate
        else:
            return pd.Series([0.045])  # 4.5% default rate
    except Exception as e:
        print(f"Error fetching risk-free rate: {e}")
        return pd.Series([0.045])


def get_available_expiries(ticker):
    """Get all available option expiration dates for a given ticker"""
    try:
        stock = yf.Ticker(ticker)
        return list(stock.options)  # List of all available expiry dates
    except Exception as e:
        print(f"Error fetching expiry dates for {ticker}: {e}")
        return []


def get_option_chain(ticker, expiry=None):
    try:
        stock = yf.Ticker(ticker)
        
        # If no expiry provided, use the first available one
        if expiry is None:
            if len(stock.options) > 0:
                expiry = stock.options[0]
            else:
                return pd.DataFrame(), pd.DataFrame()
        
        option_chain = stock.option_chain(expiry)
        return option_chain.calls, option_chain.puts
    except Exception as e:
        print(f"Error fetching option chain for {ticker}: {e}")
        return pd.DataFrame(), pd.DataFrame()


def get_realtime_iv(ticker: str, strike: float, expiry: str, option_type: str) -> float:
    """Get market-implied volatility for specific contract"""
    calls, puts = get_realtime_option_chain(ticker, expiry)
    df = calls if option_type.lower() == 'call' else puts
    match = df[df['strike'] == strike]
    if match.empty:
        raise ValueError(f"No {option_type} option found for strike {strike}")
    return float(match['impliedVolatility'].values[0])
