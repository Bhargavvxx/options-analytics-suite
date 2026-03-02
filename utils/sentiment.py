# Sentiment analysis functions
import requests
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from textblob import TextBlob

def fetch_news_headlines(ticker, limit=10):
    """
    Fetch recent news headlines for a stock
    
    Parameters:
    -----------
    ticker : str
        Stock ticker symbol
    limit : int
        Maximum number of headlines to fetch
        
    Returns:
    --------
    headlines : list
        List of news headlines
    """
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        headlines = []
        for item in data.get("news", []):
            if "title" in item:
                headlines.append(item["title"])
            if len(headlines) >= limit:
                break
                
        return headlines
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []

def calculate_sentiment_score(headlines):
    """
    Calculate sentiment score for a list of headlines
    
    Parameters:
    -----------
    headlines : list
        List of news headlines
        
    Returns:
    --------
    sentiment_score : float
        Sentiment score between -10 (very negative) and 10 (very positive)
    """
    if not headlines:
        return 0.0
        
    scores = []
    for headline in headlines:
        analysis = TextBlob(headline)
        scores.append(analysis.sentiment.polarity)
        
    # Scale to -10 to 10 range
    avg_score = np.mean(scores) * 10
    return avg_score

def get_sentiment_label(score):
    """
    Convert sentiment score to a descriptive label
    
    Parameters:
    -----------
    score : float
        Sentiment score between -10 and 10
        
    Returns:
    --------
    label : str
        Sentiment label
    """
    if score >= 5:
        return "Very Bullish"
    elif score >= 2.5:
        return "Bullish"
    elif score > -2.5:
        return "Neutral"
    elif score > -5:
        return "Bearish"
    else:
        return "Very Bearish"

def get_sentiment_recommendation(score):
    """
    Generate a trading recommendation based on sentiment score
    
    Parameters:
    -----------
    score : float
        Sentiment score between -10 and 10
        
    Returns:
    --------
    recommendation : str
        Trading recommendation
    """
    if score >= 5:
        return "Consider bullish strategies (calls, call spreads)"
    elif score >= 2.5:
        return "Slightly bullish bias; consider calls or stock"
    elif score > -2.5:
        return "No strong sentiment edge; consider neutral strategies"
    elif score > -5:
        return "Slightly bearish bias; consider puts or put spreads"
    else:
        return "Consider bearish strategies (puts, put spreads)"