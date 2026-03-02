# utils/realtime_data.py
import yfinance as yf
from typing import Tuple
import pandas as pd


def get_realtime_option_chain(ticker: str, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch real-time option chain for given ticker and expiry"""
    try:
        stock = yf.Ticker(ticker)
        chain = stock.option_chain(expiry)
        return chain.calls, chain.puts
    except Exception as e:
        raise ValueError(f"Error fetching option chain: {str(e)}")

def get_option_mid_price(calls: pd.DataFrame, puts: pd.DataFrame, strike: float, option_type: str) -> float:
    """Calculate mid price for specific strike and option type"""
    try:
        df = calls if option_type.lower() == 'call' else puts
        option = df[df['strike'] == strike].iloc[0]
        return (option['bid'] + option['ask']) / 2
    except IndexError:
        raise ValueError(f"No {option_type} option found for strike {strike}")
