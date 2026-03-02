# Option Analytics Suite

A Streamlit-based web application for options pricing, analysis, and backtesting. The app uses the Black-Scholes model to price European-style options, calculates Greeks, estimates volatility through multiple methods, runs ML-based stock price predictions, and provides sentiment analysis from news headlines.

## Features

### Black-Scholes Pricing & Greeks
- Prices European call and put options using the Black-Scholes formula with continuous dividend yield support
- Calculates all five Greeks: Delta, Gamma, Theta, Vega, and Rho
- Computes implied volatility from market prices using Newton-Raphson with a binary search fallback
- Input validation on all pricing parameters

### Volatility Estimation
- **Historical Volatility** — rolling standard deviation of log returns, annualized by default (configurable window)
- **EWMA Volatility** — exponentially weighted moving average with configurable decay factor (default λ = 0.94), annualized
- **GARCH(1,1)** — fits a GARCH model via the `arch` library and forecasts one-step-ahead variance; falls back to historical volatility if fitting fails

### Option Strategies
Calculates entry prices for ten common strategies:
- Long Call, Long Put
- Straddle, Strangle
- Bull Call Spread, Bear Put Spread
- Butterfly, Iron Condor
- Protective Put, Covered Call

Generates trading signals by comparing implied volatility to historical volatility and recommends strategies based on the IV/HV ratio.

### Machine Learning Price Prediction
Three models trained on technical features derived from historical close prices:
- **Linear Regression** (scikit-learn)
- **XGBoost** (gradient-boosted trees)
- **LSTM** (Keras/TensorFlow recurrent neural network with 60-step lookback)

Each model uses an 80/20 time-series train/test split (no shuffling) and reports MAE and RMSE on the held-out test set. An ensemble prediction is computed as the mean of all individual model outputs.

### Sentiment Analysis
- Fetches recent news headlines for the selected ticker from the Yahoo Finance search API
- Scores each headline using TextBlob polarity, then scales the average to a -10 to +10 range
- Maps the score to labels (Very Bearish / Bearish / Neutral / Bullish / Very Bullish) and provides a directional trading recommendation

### Implied Volatility Surface
- When live option chain data is available for multiple expiries, builds a 3D IV surface from market-quoted implied volatilities using scipy `griddata` interpolation
- Falls back to a simulated volatility smile/skew model when market data is unavailable

### Strategy Backtesting
- **Volatility Strategy** — trades based on IV vs. HV divergence using synthetic IV generated from historical volatility with a fixed random seed for reproducibility
- **Option Strategy Backtest** — reprices an option strategy (long call, long put, straddle, strangle) at each historical price point and tracks cumulative returns
- Displays performance metrics: average daily return, daily volatility, Sharpe ratio, and total return

### Interactive Visualizations
All charts are built with Plotly:
- Option price vs. spot price curve
- Option price vs. time to expiry (time decay)
- 3D implied volatility surface
- Strategy payoff diagrams at expiration
- Backtesting results with price, volatility, and return subplots
- ML model prediction comparison bar chart
- Real-time market price vs. model price overlay

### Streamlit UI
- Auto-refreshes every 60 seconds via `streamlit-autorefresh`
- Sidebar controls: ticker, expiry selection (from live Yahoo Finance expiry dates), strike price (from live option chain), option type, risk-free rate (auto-fetched from Treasury yields or manual), dividend yield, and volatility method
- Cached data fetching with configurable TTLs (5 min for prices/chains, 10 min for news, 1 hour for rates)
- Live option chain display showing calls and puts near the money
- Educational mode with Black-Scholes formula explanation, Greek definitions, and an interactive quiz

## Project Structure

```
├── app.py                    # Streamlit application entry point
├── requirements.txt          # Python dependencies with version pins
├── .gitignore                # Git ignore rules
├── core/
│   ├── __init__.py           # Package exports
│   ├── black_scholes.py      # Black-Scholes pricing, Greeks, implied volatility
│   ├── volatility.py         # Historical, EWMA, and GARCH volatility models
│   ├── strategies.py         # Option strategy pricing and trading signal generation
│   ├── backtesting.py        # Volatility and option strategy backtesting
│   └── ml_models.py          # StockPricePredictor class (LR, XGBoost, LSTM)
├── utils/
│   ├── data_loader.py        # Yahoo Finance data fetching (stocks, options, rates)
│   ├── realtime_data.py      # Real-time option chain and mid-price calculation
│   ├── sentiment.py          # News headline fetching and TextBlob sentiment scoring
│   └── visualizations.py     # Plotly chart functions (prices, IV surface, payoffs, backtesting)
├── models/
│   └── __init__.py           # Placeholder for saved model artifacts
└── tests/
    └── test_core.py          # Unit tests for pricing, Greeks, volatility, strategies, backtesting
```

## Setup

### Prerequisites
- Python 3.9 or higher

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd option_analytics_final
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies
| Package | Purpose |
|---|---|
| streamlit | Web application framework |
| streamlit-autorefresh | Auto-refresh timer for live data |
| yfinance | Stock and option data from Yahoo Finance |
| numpy | Numerical computations |
| pandas | Data manipulation |
| scipy | Statistical functions (normal distribution, Newton-Raphson, grid interpolation) |
| plotly | Interactive charts |
| arch | GARCH volatility model fitting |
| scikit-learn | Linear Regression, preprocessing, metrics |
| xgboost | Gradient-boosted tree regressor |
| tensorflow | LSTM neural network (Keras API) |
| textblob | Sentiment analysis on news headlines |
| requests | HTTP requests for Yahoo Finance news API |

## Usage

### Running the App

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

### Sidebar Controls
1. **Stock Ticker** — enter any ticker symbol supported by Yahoo Finance (e.g., AAPL, MSFT, TSLA)
2. **Option Expiration Date** — populated from live Yahoo Finance expiry dates for the selected ticker
3. **Underlying Price** — auto-filled from the latest intraday price; editable
4. **Strike Price** — auto-filled from the nearest ATM strike in the live chain; editable within the available strike range
5. **Option Type** — Call or Put
6. **Risk-Free Rate** — automatically fetched from 10-Year Treasury (^TNX) or 3-Month T-Bill (^IRX), or enter manually
7. **Dividend Yield** — enter as a percentage
8. **Volatility Method** — choose Manual, Historical, EWMA, or GARCH

### App Tabs
- **Visualizations** — option price curves and the 3D IV surface
- **Strategy Analysis** — strategy prices, payoff diagrams, and trading signals
- **Sentiment** — recent headlines, sentiment score, and recommendation
- **Backtesting** — run and view backtest results with performance metrics
- **Educational** — Black-Scholes explanation, Greeks definitions, and a quiz (toggle Educational Mode in sidebar)

### Running Tests

```bash
python -m pytest tests/ -v
```

The test suite covers:
- Black-Scholes call/put pricing and put-call parity
- Greek calculations (value ranges, signs, symmetries)
- Implied volatility round-trip accuracy
- Volatility model outputs (historical, EWMA, GARCH)
- Strategy pricing consistency (e.g., straddle = call + put)
- Backtesting result structure and reproducibility

## Data Sources

- **Stock prices and option chains**: Yahoo Finance via the `yfinance` library
- **Risk-free rates**: Yahoo Finance Treasury yield tickers (^IRX for 3-month, ^FVX for 5-year, ^TNX for 10-year, ^TYX for 30-year)
- **News headlines**: Yahoo Finance search API (`query1.finance.yahoo.com`)
- **Sentiment scoring**: TextBlob polarity analysis

## Limitations

- The Black-Scholes model assumes European-style options; most US equity options are American-style, so model prices may differ from market prices
- ML predictions are based solely on historical price-derived features and do not account for fundamental data, earnings events, or macroeconomic factors
- Sentiment analysis uses TextBlob, which provides basic polarity scoring and may not capture financial-specific nuances
- The backtesting volatility strategy uses synthetic IV (historical volatility plus noise) rather than actual historical implied volatility data
- Real-time data depends on Yahoo Finance availability and rate limits
- LSTM training can be slow on machines without GPU support
