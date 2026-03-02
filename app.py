import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Import modules
from core.black_scholes import black_scholes, implied_volatility
from core.volatility import historical_volatility, ewma_volatility, garch_volatility
from core.ml_models import StockPricePredictor
from core.strategies import get_option_strategies, get_trading_signals
from core.backtesting import backtest_vol_strategy, backtest_option_strategy
from utils.data_loader import (
    get_stock_data, get_risk_free_rate, get_option_chain,
    get_available_expiries, get_option_mid_price
)
from utils.sentiment import fetch_news_headlines, calculate_sentiment_score, get_sentiment_label, get_sentiment_recommendation
from utils.visualizations import (
    plot_option_price_vs_spot, plot_option_price_vs_time,
    plot_iv_surface, plot_strategy_payoff, plot_backtesting_results,
    plot_realtime_vs_model, plot_ml_comparison
)

st.set_page_config(page_title="Option Analytics Suite", layout="wide")


# --- Cached data fetching functions ---
@st.cache_data(ttl=300, show_spinner=False)
def cached_stock_data(ticker, period="2y", interval="1d"):
    return get_stock_data(ticker, period=period, interval=interval)

@st.cache_data(ttl=300, show_spinner=False)
def cached_option_chain(ticker, expiry):
    return get_option_chain(ticker, expiry)

@st.cache_data(ttl=600, show_spinner=False)
def cached_news_headlines(ticker):
    return fetch_news_headlines(ticker)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_risk_free_rate(maturity):
    return get_risk_free_rate(maturity=maturity)

@st.cache_data(ttl=300, show_spinner=False)
def cached_available_expiries(ticker):
    return get_available_expiries(ticker)


def main():
    # Auto-refresh every 60 seconds
    st_autorefresh(interval=60_000, key="refresh")

    st.title("Advanced Option Analytics Suite")

    # Initialize defaults for variables that may not get set in sidebar
    selected_expiry = None
    T = 30 / 365.0
    S = 150.0
    K = 150.0

    with st.sidebar:
        st.header("Parameters")
        educational_mode = st.checkbox("Educational Mode", value=False)
        ticker = st.text_input("Stock Ticker", "AAPL").upper()

        # Get available option expiry dates
        try:
            expiry_dates = cached_available_expiries(ticker)
            if expiry_dates:
                selected_expiry = st.selectbox(
                    "Option Expiration Date",
                    options=expiry_dates,
                    format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%b %d, %Y'),
                    help="Select an option expiration date",
                    key=f"expiry_{ticker}"
                )
                expiry_date = datetime.strptime(selected_expiry, '%Y-%m-%d')
                days_remaining = (expiry_date - datetime.now()).days
                T = max(days_remaining, 1) / 365.0

                # Fetch live underlying price
                try:
                    live_data = cached_stock_data(ticker, period="1d", interval="1m")
                    live_price = float(live_data['Close'].iloc[-1]) if not live_data.empty else None
                except Exception:
                    live_price = None

                # Fallback to historical close
                hist_2y = cached_stock_data(ticker, period="2y")
                hist_2y.index = pd.to_datetime(hist_2y.index)
                try:
                    price_on_expiry = float(hist_2y['Close'].loc[:expiry_date].iloc[-1])
                except (KeyError, IndexError):
                    price_on_expiry = float(hist_2y['Close'].iloc[-1]) if not hist_2y.empty else 150.0

                S_default = float(live_price if live_price is not None else price_on_expiry)
                S_key = f"live_S_{ticker}_{selected_expiry}"
                S = st.number_input(
                    "Underlying Price", value=S_default, min_value=0.01,
                    key=S_key
                )
            else:
                T = 30 / 365.0
                st.info("Using default 30-day expiration")
                S = st.number_input("Underlying Price", value=150.0, min_value=0.01)
        except Exception as e:
            T = 30 / 365.0
            st.error(f"Error loading expiries: {str(e)}")
            S = st.number_input("Underlying Price", value=150.0, min_value=0.01)

        # Get available strikes
        try:
            calls, puts = cached_option_chain(ticker, selected_expiry)
            if not calls.empty:
                available_strikes = sorted(calls['strike'].unique())
                default_idx = min(range(len(available_strikes)), key=lambda i: abs(available_strikes[i] - S))
                K_key = f"live_K_{ticker}_{selected_expiry}"
                K = st.number_input(
                    "Strike Price", value=available_strikes[default_idx],
                    min_value=min(available_strikes), max_value=max(available_strikes),
                    step=(available_strikes[1] - available_strikes[0] if len(available_strikes) > 1 else 1.0),
                    key=K_key
                )
            else:
                K = st.number_input("Strike Price", value=float(round(S)), min_value=0.01)
        except Exception:
            K = st.number_input("Strike Price", value=float(round(S)), min_value=0.01)

        option_type = st.selectbox("Option Type", ["call", "put"])

        rate_source = st.selectbox(
            "Risk-Free Rate",
            ["Auto (10Y Treasury)", "Auto (3M T-Bill)", "Manual Input"]
        )
        if rate_source == "Manual Input":
            r = st.number_input("Risk-Free Rate (%)", value=4.5) / 100
        else:
            maturity = "10y" if "10Y" in rate_source else "3m"
            try:
                rate_data = cached_risk_free_rate(maturity)
                if hasattr(rate_data, 'iloc'):
                    r = float(rate_data.iloc[-1])
                else:
                    r = float(rate_data)
            except Exception:
                r = 0.045
            st.info(f"Current {maturity} rate: {r:.2%}")

        q = st.number_input("Dividend Yield (%)", value=0.0, min_value=0.0) / 100

        vol_method = st.selectbox(
            "Volatility Method",
            ["Manual", "Historical", "EWMA", "GARCH"]
        )
        if vol_method == "Manual":
            sigma = st.number_input("Volatility (%)", value=25.0, min_value=1.0) / 100
        else:
            sigma = 0.25

    with st.spinner("Fetching data..."):
        hist_data = cached_stock_data(ticker, period="2y")
        if hist_data.empty:
            st.error(f"Could not fetch data for {ticker}. Please check the ticker symbol.")
            return

        returns = np.log(hist_data['Close']).diff().dropna()
        if vol_method == "Historical":
            sigma = historical_volatility(returns).iloc[-1]
        elif vol_method == "EWMA":
            sigma = ewma_volatility(returns)
        elif vol_method == "GARCH":
            sigma = garch_volatility(returns)

        calls, puts = cached_option_chain(ticker, selected_expiry)

        try:
            market_option_price = get_option_mid_price(calls, puts, K, option_type)
        except (ValueError, IndexError, KeyError):
            market_option_price = None

        headlines = cached_news_headlines(ticker)
        sentiment_score = calculate_sentiment_score(headlines)
        sentiment_label = get_sentiment_label(sentiment_score)

        bs_price, greeks = black_scholes(S, K, T, r, sigma, option_type, q)

        iv = None
        if option_type == 'call' and not calls.empty:
            atm = calls[abs(calls['strike'] - K) < 5]
            if not atm.empty:
                try:
                    iv = implied_volatility(atm.iloc[0]['lastPrice'], S, K, T, r, option_type, q)
                except (ValueError, RuntimeError):
                    iv = None
        elif option_type == 'put' and not puts.empty:
            atm = puts[abs(puts['strike'] - K) < 5]
            if not atm.empty:
                try:
                    iv = implied_volatility(atm.iloc[0]['lastPrice'], S, K, T, r, option_type, q)
                except (ValueError, RuntimeError):
                    iv = None

        trading_signals = get_trading_signals(S, K, T, r, sigma, iv or sigma, q) if iv else None

        ml_predictions = None
        predictor = None
        if len(hist_data) > 60:
            with st.spinner("Training ML models..."):
                try:
                    predictor = StockPricePredictor()
                    feats = predictor.prepare_features(hist_data['Close'])
                    predictor.train_linear_regression(feats)
                    predictor.train_xgboost(feats)
                    predictor.train_lstm(hist_data['Close'], epochs=20)
                    ml_predictions = predictor.predict_next_price(hist_data['Close'])
                except Exception as e:
                    st.error(f"ML prediction error: {e}")

    # Main metrics display
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Current Price", f"${S:.2f}")
    col2.metric("Option Price (Model)", f"${bs_price:.2f}")
    col3.metric("Option Price (Market)", f"${market_option_price:.2f}" if market_option_price else "N/A")
    col4.metric("Volatility", f"{sigma*100:.1f}%")
    col5.metric("Sentiment", f"{sentiment_label} ({sentiment_score:.1f})")

    if selected_expiry and not calls.empty and not puts.empty:
        with st.expander(f"Option Chain for {selected_expiry}"):
            tab_call, tab_put = st.tabs(["Calls", "Puts"])

            with tab_call:
                atm_calls = calls[abs(calls['strike'] - S) < S * 0.1]
                st.dataframe(
                    atm_calls[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'impliedVolatility']],
                    hide_index=True,
                    use_container_width=True
                )

            with tab_put:
                atm_puts = puts[abs(puts['strike'] - S) < S * 0.1]
                st.dataframe(
                    atm_puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'impliedVolatility']],
                    hide_index=True,
                    use_container_width=True
                )

    st.subheader("Option Greeks")
    greek_cols = st.columns(5)
    greek_cols[0].metric("Delta", f"{greeks['delta']:.4f}")
    greek_cols[1].metric("Gamma", f"{greeks['gamma']:.4f}")
    greek_cols[2].metric("Theta", f"{greeks['theta']:.4f}")
    greek_cols[3].metric("Vega", f"{greeks['vega']:.4f}")
    greek_cols[4].metric("Rho", f"{greeks['rho']:.4f}")

    # ML Predictions section - only render if we have valid predictions
    if ml_predictions is not None and isinstance(ml_predictions, dict) and len(ml_predictions) > 0:
        st.subheader("ML Predictions & Option Pricing")

        # Show model accuracy metrics if available
        if predictor and predictor.metrics:
            with st.expander("Model Accuracy (Test Set)"):
                metric_cols = st.columns(len(predictor.metrics))
                model_display = {'lr': 'Linear Regression', 'xgb': 'XGBoost', 'lstm': 'LSTM'}
                for i, (model_key, m) in enumerate(predictor.metrics.items()):
                    with metric_cols[i]:
                        st.write(f"**{model_display.get(model_key, model_key)}**")
                        st.write(f"MAE: ${m['mae']:.2f}")
                        st.write(f"RMSE: ${m['rmse']:.2f}")

        models = ['lr', 'xgb', 'lstm', 'ensemble']
        model_names = {
            'lr': 'Linear Regression',
            'xgb': 'XGBoost',
            'lstm': 'LSTM',
            'ensemble': 'Ensemble'
        }

        for model in models:
            if model in ml_predictions:
                with st.expander(f"{model_names[model]} Analysis", expanded=True):
                    pred_col1, pred_col2 = st.columns(2)

                    with pred_col1:
                        try:
                            pred_price = ml_predictions[model]
                            if hasattr(pred_price, 'iloc'):
                                pred_price = float(pred_price.iloc[0])
                            else:
                                pred_price = float(pred_price)
                            st.metric(
                                "Predicted Stock Price",
                                f"${pred_price:.2f}",
                                delta=f"{((pred_price/S)-1)*100:.2f}% from current"
                            )
                        except Exception as e:
                            st.error(f"Error displaying {model} prediction: {str(e)}")

                    with pred_col2:
                        try:
                            option_price, _ = black_scholes(
                                pred_price, K, T, r, sigma, option_type, q
                            )
                            st.metric(
                                "Projected Option Price",
                                f"${option_price:.2f}",
                                delta=f"{((option_price/bs_price)-1)*100:.2f}% vs model"
                            )
                        except Exception as e:
                            st.error(f"Option pricing failed: {str(e)}")

        try:
            st.plotly_chart(
                plot_ml_comparison(S, {k.upper(): v for k, v in ml_predictions.items()}),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"ML comparison chart error: {e}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Visualizations", "Strategy Analysis", "Sentiment", "Backtesting", "Educational"
    ])

    with tab1:
        viz_col1, viz_col2 = st.columns(2)
        with viz_col1:
            st.plotly_chart(plot_option_price_vs_spot(S, K, T, r, sigma, q, option_type), use_container_width=True)
        with viz_col2:
            st.plotly_chart(plot_option_price_vs_time(S, K, r, sigma, q, option_type), use_container_width=True)

        # Try to build real IV surface from multiple expiries
        option_chains = None
        try:
            expiry_dates_list = cached_available_expiries(ticker)
            if expiry_dates_list and len(expiry_dates_list) >= 2:
                option_chains = {}
                for exp in expiry_dates_list[:5]:  # Limit to 5 expiries for speed
                    c, p = cached_option_chain(ticker, exp)
                    if not c.empty:
                        option_chains[exp] = (c, p)
        except Exception:
            option_chains = None

        st.plotly_chart(plot_iv_surface(S, K, r, q, option_chains=option_chains), use_container_width=True)

    with tab2:
        st.subheader("Option Strategies")
        strategies = get_option_strategies(S, K, T, r, sigma, q)
        strat_cols = st.columns(5)
        for i, (name, price) in enumerate(strategies.items()):
            col_idx = i % 5
            strat_cols[col_idx].metric(name, f"${price:.2f}")

        st.subheader("Strategy Payoff Analysis")
        strategy_type = st.selectbox(
            "Select Strategy",
            ["long_call", "long_put", "straddle", "strangle", "bull_call_spread"]
        )
        st.plotly_chart(plot_strategy_payoff(S, K, T, r, sigma, q, strategy_type), use_container_width=True)

        if trading_signals:
            st.subheader("Trading Signals")
            st.write(f"**Volatility Assessment:** {trading_signals['volatility']}")
            st.write(f"**Recommended Action:** {trading_signals['vol_action']}")
            st.write(f"**Call Assessment:** {trading_signals['call']}")
            st.write(f"**Put Assessment:** {trading_signals['put']}")
            st.write(f"**Recommended Strategy:** {trading_signals['strategy']}")

    with tab3:
        st.subheader("Sentiment Analysis")
        st.write("**Recent Headlines:**")
        for i, headline in enumerate(headlines[:5]):
            st.write(f"{i+1}. {headline}")

        sent_col1, sent_col2 = st.columns(2)
        sent_col1.metric("Sentiment Score", f"{sentiment_score:.2f}")
        sent_col1.write(f"**Sentiment Label:** {sentiment_label}")
        sent_col2.write("**Trading Recommendation:**")
        sent_col2.write(get_sentiment_recommendation(sentiment_score))

        if len(hist_data) > 30:
            st.subheader("Historical Price Movement")
            st.line_chart(hist_data['Close'][-30:])

    with tab4:
        st.subheader("Strategy Backtesting")
        backtest_type = st.selectbox(
            "Select Backtest Strategy",
            ["Volatility Strategy (IV/HV)", "Long Call", "Long Put", "Straddle", "Strangle"]
        )

        if backtest_type == "Volatility Strategy (IV/HV)":
            results = backtest_vol_strategy(hist_data['Close'])
        else:
            strategy_map = {
                "Long Call": "long_call",
                "Long Put": "long_put",
                "Straddle": "straddle",
                "Strangle": "strangle"
            }
            results = backtest_option_strategy(
                hist_data['Close'],
                strategy_map[backtest_type],
                K, T, r, sigma, q
            )

        if not results.empty:
            st.plotly_chart(plot_backtesting_results(results), use_container_width=True)
            if 'Cumulative_Return' in results.columns:
                final_return = results['Cumulative_Return'].iloc[-1]
                st.metric("Cumulative Return", f"{final_return:.2%}")
            if len(results) > 1:
                daily_std = results['Strategy_Return'].std()
                ret_stats = pd.DataFrame({
                    'Value': [
                        results['Strategy_Return'].mean(),
                        daily_std,
                        results['Strategy_Return'].mean() / daily_std if daily_std > 0 else 0,
                        final_return
                    ]
                }, index=['Avg. Daily Return', 'Daily Volatility', 'Sharpe Ratio', 'Total Return'])
                st.write("**Strategy Performance Metrics:**")
                st.table(ret_stats)

    with tab5:
        st.subheader("Black-Scholes Model Explained")
        st.write("""
The Black-Scholes option pricing model is a mathematical model for pricing European-style options.
The formula calculates the theoretical price of options using current stock prices, expected dividends,
the option's strike price, expected interest rates, time to expiration, and expected volatility.
""")
        st.subheader("The Formula")
        st.latex(r'C = S e^{-q T} N(d_1) - K e^{-r T} N(d_2) \\ d_1 = \frac{\ln(S/K) + (r - q + \sigma^2/2)T}{\sigma \sqrt{T}} \\ d_2 = d_1 - \sigma \sqrt{T}')
        st.write("""
**Where:**
- C = Call option price
- S = Current stock price
- K = Strike price
- r = Risk-free interest rate
- T = Time to expiration (in years)
- sigma = Volatility of the underlying
- q = Dividend yield
- N() = Cumulative distribution function of the standard normal distribution
""")
        st.subheader("Option Greeks")
        greeks_explanation = {
            "Delta": "Measures how much the option price changes when the underlying stock price changes by $1. Delta ranges from 0 to 1 for calls and -1 to 0 for puts.",
            "Gamma": "Measures the rate of change of Delta with respect to changes in the underlying price. High Gamma means Delta will change rapidly with small moves in the underlying.",
            "Theta": "Measures the rate of time decay, or how much value the option loses each day as it approaches expiration. Theta is typically negative for long options.",
            "Vega": "Measures sensitivity to volatility. Specifically, how much the option price changes for a 1% change in implied volatility.",
            "Rho": "Measures sensitivity to interest rates. Specifically, how much the option price changes for a 1% change in the risk-free rate."
        }
        for greek, explanation in greeks_explanation.items():
            st.write(f"**{greek}:** {explanation}")

        if educational_mode:
            st.subheader("Option Pricing Quiz")
            q1 = st.radio(
                "Which of these factors does NOT affect option prices in the Black-Scholes model?",
                ["Stock price", "Strike price", "Trading volume", "Risk-free rate"]
            )
            if q1 == "Trading volume":
                st.success("Correct! Trading volume is not a direct input to the Black-Scholes formula.")
            else:
                st.error("Incorrect. Trading volume is not a direct input to the Black-Scholes formula.")

            q2 = st.radio(
                "What happens to call option prices when volatility increases?",
                ["Increase", "Decrease", "Stay the same", "Cannot be determined"]
            )
            if q2 == "Increase":
                st.success("Correct! Higher volatility increases the price of both calls and puts.")
            else:
                st.error("Incorrect. Higher volatility increases the price of both calls and puts because it increases the probability of the option expiring in-the-money.")

if __name__ == "__main__":
    main()
