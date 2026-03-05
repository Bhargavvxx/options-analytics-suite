# Option Analytics Suite

A professional-grade options analytics platform built with Python and Streamlit. The codebase implements Black-Scholes European pricing, analytical & finite-difference Greeks, production-quality IV solvers (Newton → Bisection → Brent cascade), multiple volatility models (HV / EWMA / GARCH / regime detection), composable multi-leg strategy definitions, event-driven backtesting with transaction costs, ML volatility prediction pipelines, and news sentiment scoring — all behind a layered architecture with typed dataclass outputs, structured logging, and comprehensive tests.

---

## Features

### Pricing Engine (`analytics/pricing.py`)
- Closed-form Black-Scholes European call/put pricing
- Vectorised (NumPy array) **and** scalar interface
- Continuous dividend-yield support
- Put-call parity verification
- Optional `validate=False` fast-path for inner loops

### Greeks (`analytics/greeks.py`)
- **Analytical** closed-form Delta, Gamma, Theta, Vega, Rho (dividend-adjusted)
- **Finite-difference** Greeks via central-differencing for cross-validation
- All outputs in a frozen `Greeks` dataclass
- Theta per calendar day (/365), Vega and Rho per 1 percentage point

### Implied Volatility (`analytics/implied_vol.py`)
- Cascading solver: Newton-Raphson → Bisection → Brent (scipy)
- Arbitrage-bounds pre-check before solver entry
- Near-zero vega guard in Newton iteration
- Structured `IVResult` output: IV, converged flag, iterations, method used, residual
- `batch_solve_iv()` for full option chains

### Volatility Models (`analytics/volatility.py`)
- Rolling historical volatility (any window)
- Realised volatility cone (multi-window percentile stats)
- EWMA volatility (configurable λ)
- GARCH(1,1) via `arch` with graceful fallback
- Forward volatility estimation from term-structure
- Vol-regime detection (LOW / NORMAL / HIGH / EXTREME)

### IV Surface (`analytics/iv_surface.py`)
- Builder from real option-chain data with market-IV or re-solving
- SciPy `griddata` interpolation
- Diagnostics: skew slope, smile curvature
- **SurfaceQC** report: total/converged/failed points, % missing, solver stats, IV range
- Simulated surface (clearly marked educational) when no market data

### SVI Smile Fit (`analytics/smile.py`)
- Raw SVI parameterisation (Gatheral 2004): calibrates `a, b, rho, m, sigma` per expiry slice
- Bounded `least_squares` optimisation with RMSE reporting
- `calibrate_surface_svi()` for full surface — one fit per tenor
- Smooth IV curves that can replace scattered market quotes

### Strategies (`strategies/`)
- Declarative `StrategyLeg` + `StrategyDefinition` dataclasses
- Catalog of 10 pre-built strategies (straddle, strangle, spreads, butterfly, iron condor, protective put, covered call, etc.)
- `price_strategy()` and `strategy_payoff()` for pricing and expiry P&L
- IV-vs-HV trading-signal generator

### Backtesting (`backtesting/`)
- Event-driven `BacktestEngine` with trade lifecycle (entry → hold → exit)
- **Decaying T**: `expiry_date` parameter gives per-bar time-to-expiry via day-count conventions
- **Bid/ask execution model**: fills at bid/ask when quote columns exist, slippage fallback otherwise
- **Trade blotter** with enriched fields: bid, ask, spread, execution mode, entry/exit T
- **BacktestConfig** snapshot for full reproducibility (serialisable to JSON)
- CSV + JSON export buttons in the Streamlit UI
- Explicit transaction costs and slippage
- `PerformanceMetrics`: Sharpe, Sortino, Calmar, max drawdown, profit factor, win rate
- Monte-Carlo simulation (GBM + antithetic variates) clearly labelled educational

### ML Pipeline (`ml/`)
- Reproducible feature engineering (`features.py`): 13 price-based features, forward-vol target
- Model registry: Ridge (baseline), XGBoost, LSTM (PyTorch)
- **Training** separated from **inference** — no re-training on Streamlit reruns
- Time-series aware chronological split (no future leakage)
- Model persistence via joblib / torch.save

### Sentiment (`sentiment/`)
- Google News RSS fetcher (no API key required)
- TextBlob and VADER scoring (lazy-loaded)
- Structured `SentimentSummary` with per-article and aggregate scores

### Visualization (`visualization/`)
- All Plotly: price surfaces, Greeks dashboards, vol cones, IV surfaces, payoff diagrams, equity curves, drawdown, ML comparison, feature importance

### UI (`ui/`)
- **Thin** Streamlit orchestrator (`run.py`) — all logic in library packages
- Shared sidebar component for consistent parameter input
- 7 pages: Pricing, Volatility, Strategies, Backtesting, ML, Sentiment, Educational

---

## Architecture

```
├── run.py                          # Streamlit entry point (thin dispatcher)
├── config/
│   ├── settings.py                 # Centralised frozen Settings dataclass (~50 fields)
│   ├── errors.py                   # Custom exception hierarchy (OASError base)
│   └── logging_config.py           # Structured logging (replaces all print())
├── analytics/
│   ├── pricing.py                  # BS pricing (price only, vectorised)
│   ├── greeks.py                   # Analytical + finite-difference Greeks
│   ├── implied_vol.py              # IV solvers (Newton/Bisection/Brent)
│   ├── volatility.py               # HV, EWMA, GARCH, regime, vol cone
│   ├── iv_surface.py               # IV surface builder + QC diagnostics
│   ├── smile.py                    # SVI smile calibration (Gatheral 2004)
│   └── day_count.py                # Year-fraction with day-count conventions
├── data/
│   ├── market_data.py              # Abstract MarketDataProvider + YFinance impl
│   ├── cache.py                    # Thread-safe TTL cache
│   ├── normalization.py            # OHLCV validation, chain normalization, bid/ask QC
├── strategies/
│   ├── definitions.py              # Composable leg definitions + catalog
│   ├── pricing.py                  # Strategy pricing & expiry payoff
│   └── signals.py                  # IV/HV trading signal generation
├── backtesting/
│   ├── engine.py                   # Event-driven backtest with decaying T + bid/ask fills
│   ├── metrics.py                  # Sharpe, Sortino, drawdown, profit factor
│   └── simulation.py               # Educational Monte-Carlo (GBM paths)
├── ml/
│   ├── features.py                 # Feature engineering pipeline
│   ├── models.py                   # Model registry (Ridge, XGB, LSTM)
│   ├── training.py                 # Train pipeline (chrono split)
│   ├── inference.py                # Inference pipeline (stateless)
│   └── artifacts.py                # Model save / load
├── sentiment/
│   └── analyzer.py                 # News fetch + TextBlob / VADER scoring
├── visualization/
│   ├── pricing_charts.py           # Price surface, Greeks dashboard
│   ├── vol_charts.py               # Vol cone, term structure, IV surface 3D
│   ├── strategy_charts.py          # Payoff diagrams, strategy comparison
│   ├── backtest_charts.py          # Equity curve, drawdown
│   └── ml_charts.py                # Model comparison, feature importance
├── ui/
│   ├── components.py               # Shared sidebar + metric helpers
│   └── pages/                      # One module per tab
│       ├── pricing.py
│       ├── volatility.py
│       ├── strategies.py
│       ├── backtesting.py
│       ├── ml.py
│       ├── sentiment.py
│       └── educational.py
├── tests/
│   ├── conftest.py                 # Shared fixtures
│   ├── test_pricing.py             # BS benchmarks + put-call parity
│   ├── test_greeks.py              # Analytical / FD cross-validation
│   ├── test_implied_vol.py         # IV round-trip + edge cases
│   ├── test_volatility.py          # Vol models + regime
│   ├── test_strategies.py          # Strategy pricing + payoffs + signals
│   ├── test_backtesting.py         # MC convergence + metrics
│   ├── test_data.py                # Cache + normalization
│   └── test_new_features.py        # Decaying T, bid/ask, SVI, QC, exceptions
├── .github/workflows/ci.yml        # GitHub Actions: lint (ruff) + test
├── ruff.toml                        # Ruff linter/formatter config
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.10+

### Installation

```bash
git clone https://github.com/Bhargavvxx/options-analytics-suite.git
cd options-analytics-suite

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Optional Dependencies
| Package | Purpose | Fallback |
|---|---|---|
| `arch` | GARCH volatility | EWMA used instead |
| `xgboost` | Gradient-boosted trees | Ridge regression |
| `torch` | LSTM model | Ridge regression |
| `feedparser` | News fetching | Empty results |
| `textblob` | Sentiment scoring | Neutral scores |

---

## Usage

### Running the App

```bash
streamlit run run.py
```

Opens at `http://localhost:8501`.  Use the sidebar to set ticker, strike, expiry, volatility, and other parameters.

### Running Tests

```bash
python -m pytest tests/ -v --tb=short
```

Test coverage includes pricing benchmarks (Hull 10th ed.), put-call parity, Greeks sign/range/FD-cross-validation, IV round-trip at various moneyness levels, vol model outputs, strategy pricing/payoff, Monte-Carlo convergence, and data-layer caching.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Frozen dataclasses for outputs | Immutability prevents downstream mutation bugs |
| Pricing separated from Greeks separated from IV | Each concern testable and replaceable independently |
| Abstract `MarketDataProvider` ABC | Swap yfinance for Bloomberg/IBKR without touching analytics |
| Cascading IV solver | Newton is fast; Bisection/Brent guarantee convergence |
| ML training separated from inference | Avoids re-training on every Streamlit interaction |
| Structured logging (no `print()`) | Production diagnostics, configurable verbosity |
| Centralized `Settings` dataclass | All magic numbers in one place, env-var overridable |

---

## Limitations

- **European options only** — Black-Scholes does not price early exercise (American options)
- **No live streaming data** — yfinance provides delayed snapshots, not tick-level feeds
- **Backtesting uses decaying T by default** — set an expiry date or use the legacy fixed-T mode
- **ML predicts volatility, not price direction** — features are price-derived only; no fundamental/macro data
- **Sentiment is headline-level** — TextBlob/VADER are general-purpose, not finance-tuned
- **Monte-Carlo is educational** — uses GBM (constant vol), not stochastic vol
- **No margin/portfolio-level risk** — single-strategy focus, no cross-position netting
- **LSTM requires PyTorch** — falls back to Ridge if torch is not installed
