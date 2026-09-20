# Indian Market Platform — Detailed Implementation & Migration Plan

> **Purpose:** Turn the current `options-analytics-suite` into a serious India-first equities + portfolio + systematic research platform while preserving the best existing quant code.  
> **Current repository:** `Bhargavvxx/options-analytics-suite`  
> **Baseline reviewed:** `main` @ `92fc3312258536f5394d6394245dd1b9dfc20c39`  
> **Revision:** Final integrated implementation plan including production prediction, forecast evaluation, opportunity ranking, and explainable decision support.  
> **Companion document:** `INDIAN_MARKET_PLATFORM_ARCHITECTURE.md`  
> **Implementation philosophy:** correctness first, incremental migration, no big-bang rewrite, no feature-binge, explicit acceptance gates, and no production prediction without point-in-time validation plus a permanent evaluation trail.

---

# 1. Implementation objective

The migration is successful when the application is useful as a **daily personal Indian-market research and portfolio system**, not merely when its directory structure matches the target architecture.

The desired transition is:

```text
CURRENT
Options analytics app
  + simulated/model backtest
  + portfolio/risk prototype
  + ML/sentiment tabs

            ↓ staged migration

TARGET
India-first market data foundation
  + equity research workstation
  + personal research/watchlists
  + portfolio ledger/risk
  + point-in-time backtesting
  + integrated futures/options
  + auditable prediction/forecasting
  + explainable opportunity & decision support
  + evidence-grounded assistant
  + optional broker execution boundary
```

---

# 2. Non-negotiable migration rules

## R1 — Do not rewrite working quant modules just to reorganize folders
Move only after tests protect behavior.

## R2 — New stock features must not depend on the old Yahoo-centric provider abstraction
The provider-contract redesign happens before major stock UI work.

## R3 — Do not claim a phase complete because tests “exist”
Each phase has economic/data acceptance criteria.

## R4 — No historical backtest uses present-day membership or unpublished future data
Point-in-time controls are architectural gates.

## R5 — Never discard source data after parsing
Raw artifacts + hashes + manifests are required for official datasets.

## R6 — Live execution stays disabled and outside the critical path
Research must be fully useful without broker order permissions.

## R7 — Current repo bugs are fixed before using the affected subsystem as a foundation
Known backtest, ML, multiplier, config, and derivative issues are not carried forward.

## R8 — One phase should leave the repo runnable
Avoid long-lived “half-migrated” architecture.

## R9 — Prefer small reviewable commits
A suggested commit usually changes one concept plus its tests/migration.

## R10 — Every phase ends with a written completion report
Include code commit, migrations, test results, data evidence, unresolved items, and next gate.

## R11 — No production forecast without a permanent audit trail
A user-facing prediction requires an approved model deployment, immutable prediction record, point-in-time input cutoff, baseline/calibration evidence, abstention policy, and later outcome evaluation. Suggestions must reference stored evidence rather than invent a reason after the fact.

---

# 3. Current baseline — what we are starting from

## 3.1 Strengths to preserve

- pricing separated from Greeks and IV;
- typed dataclass outputs;
- cascading IV solver;
- volatility modules;
- strategy definitions separated from UI;
- portfolio/stress concepts already exist;
- Streamlit entry point is relatively thin;
- provider ABC exists, proving data access is already abstracted conceptually;
- test suite covers major options math;
- structured logging/config groundwork exists.

## 3.2 Known correctness/integration debt that must not be ignored

The repo review found, among other items:

### Backtest
- actual bid/ask `fill_px` is calculated and then discarded;
- cash is treated as equity while open option liability is not marked to market;
- expiry is clamped to one day rather than settled/terminated;
- current UI is a model-based option simulation over historical underlying data, not a historical-options backtest;
- total-return baseline and some metric logic need correction;
- UI “Avg PnL” is computed incorrectly.

### ML
- forward-volatility targets can cross the chronological train/test boundary;
- test set is used to select a “best” model;
- LSTM inference length/index handling is inconsistent;
- LSTM can silently fall back to linear behavior while retaining an LSTM label;
- persistence does not robustly package wrapper/scaler/architecture state.

### Risk/domain
- stock multiplier can accidentally remain `100` in UI construction;
- portfolio valuation is effectively single-underlying despite instrument labels.

### Data/config
- current provider is Yahoo-centric and embeds US Treasury symbols;
- `Settings.from_env()` is not the real runtime source of truth;
- duplicated defaults drift across modules;
- duplicate day-count enum exists;
- cache/provider capabilities are not integrated consistently.

### Derivatives math/integration
- real IV surface pipeline exists but is not wired to UI;
- SVI and arbitrage diagnostics need mathematical hardening;
- same volatility can be used across multi-strike strategies;
- American-option dividend/boundary handling has limitations.

These are inputs to Phase 0/1, not reasons to throw away the repo.

---

# 4. Migration strategy at a glance

```text
Phase 0   Baseline freeze + CI + safety net
Phase 1   Correctness debt in current system
Phase 2   New core/domain/storage skeleton
Phase 3   Canonical instruments + India calendar + provider contracts
Phase 4   Official NSE EOD ingestion + raw/quality/versioning
Phase 5   Corporate actions + adjusted histories + universes
Phase 6   Equity analytics + Market/Stock UI v1
Phase 7   Corporate filings + fundamentals + ownership
Phase 8   Screener + watchlists + research notes + alerts
Phase 9   Portfolio ledger + broker read-only reconciliation
Phase 10  Backtest Engine 2.0 for equities
Phase 11  Futures + migrate/integrate options stack
Phase 12  Option snapshot collector + derivative market intelligence
Phase 13  ML research framework (only after PIT data/backtest)
Phase 14  Production prediction & forecast layer
Phase 15  Opportunity & decision-support engine
Phase 16  Evidence-grounded AI research assistant
Phase 17  Optional paper/live execution boundary
```

Not every phase must be completed before the platform becomes useful. By Phases 6–9 it should already be a strong daily system.

---

# 5. Phase 0 — Baseline freeze, reproducibility, CI visibility

## Goal
Make the current repo a trustworthy migration starting point.

## Why first
The current GitHub Actions history reviewed earlier had lint failures causing tests to be skipped. A migration without a clean baseline makes regressions hard to attribute.

## Work

### 0.1 Record baseline
Create:

```text
docs/migration/BASELINE_2026.md
```

Include:
- reviewed commit SHA;
- repo tree summary;
- current feature inventory;
- known defects list;
- test count discovered from code;
- current CI state;
- migration objective.

### 0.2 CI jobs
Change CI so test observability is not completely hidden by a lint failure.

Recommended jobs:

```text
lint
unit-tests
```

Run both independently; branch protection can require both later.

### 0.3 Reproducible environment
Replace floating-only dependency practice with one reproducible mechanism.

Recommended low-friction choice:
- keep `pyproject.toml` as source of dependency intent;
- generate a lock/constraints file with `uv` or `pip-tools`.

Do not introduce Poetry unless the team actually wants its workflow.

### 0.4 Python version policy
Either:
- test supported versions, e.g. 3.11/3.12; or
- explicitly state one supported version initially.

Do not claim `3.10+` while CI proves only one version.

### 0.5 Root license
Add actual `LICENSE` file if project remains MIT.

## Tests / gate
- lint job passes;
- current unit tests pass in CI;
- installation from clean environment succeeds;
- `streamlit run run.py` smoke-start succeeds;
- baseline document committed.

## Do not do in Phase 0
- directory mega-refactor;
- database introduction;
- new stock analytics.

---

# 6. Phase 1 — Fix correctness debt before expansion

## Goal
Stop known incorrect behavior from becoming a dependency of the new platform.

This phase is intentionally split into isolated units.

---

## Phase 1A — Backtest correctness repair

### 1A.1 Use actual execution fill
Current code obtains:

```python
fill_px, bid, ask, exec_mode = self._get_fill(...)
```

but then replaces it with a model-price slippage result.

**Fix:** executable price must be the price used in cash/P&L accounting.

### 1A.2 Separate cash from NAV
Introduce explicit state:

```text
cash
open_positions
position_market_value
nav
```

For a short option:

```text
NAV = cash - market_value(short liability)
```

Opening a fairly priced position should not create profit except for immediate costs/slippage.

### 1A.3 Expiry lifecycle
Remove the “minimum one day forever” model.

At/after expiry:
- settle/exercise/expire according to contract model;
- generate a settlement event;
- position disappears.

### 1A.4 Rename current historical option workflow
Until real historical chain/snapshots exist, label it accurately:

> Model-based option strategy simulation over historical underlying prices

Do not call it a historical options backtest.

### 1A.5 Fix metrics/UI
- total return vs initial NAV;
- average P&L uses actual trade average;
- review Sortino annualization consistently;
- drawdown from NAV series;
- report execution mode and model assumptions.

### Required regression tests
1. sell-at-bid test;
2. buy-to-close-at-ask test;
3. opening a fair-value short option does not increase NAV except costs;
4. expiry terminates position;
5. cash + position value reconciles to NAV each bar;
6. final NAV reconciles to trade ledger;
7. UI avg-P&L source value test.

### Gate
No migration uses `BacktestEngine` until these invariants pass.

---

## Phase 1B — Risk/domain repairs

### Work
- stock positions default to multiplier `1`, options use contract multiplier from instrument metadata;
- remove implicit single `S, r, q` portfolio valuation contract;
- represent valuation inputs as `instrument_id -> market state`;
- validate option sigma/T/strike at portfolio boundary.

### Tests
- 1 stock share at ₹X values to ₹X, not ₹100X;
- two equities can value independently;
- option and stock positions coexist;
- aggregate P&L reconciles per-position contributions.

---

## Phase 1C — Config consolidation

### Work
- one canonical `DayCountConvention`;
- replace module `_CFG = Settings()` globals;
- app constructs one `AppSettings`/`Settings` and injects it;
- reconcile commission defaults, artifact directory, XGBoost defaults, risk-free config;
- deprecate US treasury mapping.

### Gate
A test changes an environment/config value and proves affected runtime service sees it.

---

## Phase 1D — ML quarantine and correctness

Do not expand ML. Make it truthful and safe.

### Work
- implement purge/embargo >= target horizon or split before overlapping target construction;
- create train/validation/test or walk-forward selection;
- never choose model on final test set;
- fix LSTM inference index alignment;
- remove silent LSTM→Ridge identity mismatch;
- package model + scaler + feature schema + architecture + training metadata;
- add dedicated ML tests.

### Gate
- leakage regression test passes;
- model selection uses validation only;
- final test touched once;
- LSTM prediction index length matches output;
- artifact load reproduces predictions within tolerance.

### Product priority
After correctness, leave ML alone until Phase 13.

---

# 7. Phase 2 — Introduce the new core without breaking the app

## Goal
Create the foundations for the India-first platform alongside the current modules.

## New dependencies
Recommended:
- SQLAlchemy 2.x or SQLModel-style SQLAlchemy usage;
- Alembic;
- PostgreSQL driver (`psycopg`);
- Pydantic v2 for boundary schemas;
- DuckDB;
- PyArrow;
- optional Polars later if profiling justifies it.

Do not replace NumPy/Pandas quant code solely for fashion.

## New structure
Create only:

```text
src/core/
src/instruments/
src/providers/contracts/
src/storage/
src/ingestion/
```

Keep current packages running during migration.

## 2.1 Settings
Introduce nested application settings with environment loading.

## 2.2 Database
Add `docker-compose.yml` for local PostgreSQL or document native alternative.

Minimal schema:
- `source`;
- `ingestion_run`;
- `raw_artifact`;
- `instrument`;
- `instrument_alias`.

## 2.3 Migration mechanism
Alembic migration `0001_core_identity`.

## 2.4 Repository interfaces
Do not expose SQLAlchemy sessions throughout domain logic.

Example:

```python
class InstrumentRepository(Protocol):
    def get(self, instrument_id): ...
    def resolve_alias(self, provider, alias, at): ...
```

## Gate
- DB can initialize from zero;
- migration up/down tested;
- create instrument + aliases;
- alias resolution respects validity interval;
- existing Streamlit app still starts.

---

# 8. Phase 3 — Canonical instruments, NSE calendar, provider contracts

## Goal
Make the system understand Indian securities before ingesting serious history.

---

## 3.1 Instrument identity

Implement:

```text
instrument
instrument_alias
derivative_contract
company
index
index_membership
```

### Identity policy
Preferred equity anchors:
- internal UUID/ULID primary key;
- ISIN where available as a strong external identifier;
- exchange + trading symbol as dated alias;
- broker keys as dated aliases.

Do not assume symbol uniqueness across time/exchanges.

---

## 3.2 Provider protocols

Implement narrow interfaces:

```text
ReferenceDataProvider
HistoricalPriceProvider
LiveQuoteProvider
CorporateEventsProvider
FundamentalsProvider
DerivativesProvider
RatesProvider
BrokerPortfolioProvider
ExecutionProvider
```

### Result envelope
Pydantic model:

```text
provider
retrieved_at
as_of
source_dataset
warnings
quality_flags
raw_artifact_id
results
```

---

## 3.3 NSE calendar

Create `exchange_session` table.

Seed/ingest:
- normal sessions;
- official holidays;
- special/muhurat sessions when published.

NSE publishes yearly trading holidays and regular market timing information. Store yearly source artifact and parser version.

### Gate tests
- weekends excluded;
- known official holiday excluded;
- known trading day included;
- timezone-aware session open/close;
- calendar version is queryable by year.

---

## 3.4 Broker reference adapters

Implement **one** broker reference provider first, based on the account you actually intend to use later. Architecture supports multiple; implementation should not attempt all simultaneously.

Adapter responsibilities:
- fetch instrument master;
- archive payload;
- normalize instrument metadata;
- map aliases;
- retain expiry/strike/lot/tick size;
- update validity intervals rather than deleting old aliases.

Important research observations:
- Zerodha recommends a daily instrument dump and documents derivative token expiry/reuse behavior.
- Upstox recommends `instrument_key` instead of exchange token because exchange tokens can be reused.

### Gate
Take two dated instrument-master fixtures where a derivative disappears/changes and prove historical alias resolution still works.

---

# 9. Phase 4 — Official NSE EOD market-data pipeline

## Goal
Build the first trustworthy production dataset: daily NSE market history with provenance.

## Start with a narrow official dataset set

### Required
- CM UDiFF Common Bhavcopy;
- Security-wise Delivery Positions;
- market activity/reference data as needed.

### Later in the same ingestion framework
- short-selling report;
- F&O UDiFF Common Bhavcopy;
- participant-wise OI/volume;
- FII derivatives statistics.

NSE’s current reports page explicitly directs users from older bhavcopy formats to UDiFF common bhavcopy, so parser names/versions should follow the current format rather than obsolete CSV assumptions.

---

## 4.1 Raw artifact store

For every download:

```text
provider=NSE
dataset=CM_UDIFF_BHAVCOPY
trade_date=...
retrieved_at=...
sha256=...
url/source identifier
content_length
parser_version
```

Never parse directly into the final table without saving source bytes.

---

## 4.2 Normalized daily bar schema

Parquet/canonical record:

```text
instrument_id
trade_date
open
high
low
close
previous_close
volume
traded_value
trades             if available
source_id
source_run_id
quality_flags
```

Keep delivery data separate:

```text
instrument_id
trade_date
deliverable_quantity
delivery_pct
source_run_id
```

Do not join and duplicate it into every raw price row.

---

## 4.3 Quality gates

Block publish if:
- duplicate `(instrument_id, trade_date)`;
- unresolved instrument rate above configured threshold;
- invalid OHLC ordering;
- negative volume/value;
- file hash duplicate with inconsistent date metadata;
- trade date does not match expected session.

Warnings:
- broker comparison close differs beyond tolerance;
- missing delivery row for eligible security;
- newly unknown series/security type.

---

## 4.4 Dataset version

Publish only after quality checks:

```text
NSE_DAILY_EQUITY@2026-09-21.v1
```

A backtest can later pin to this version.

---

## 4.5 Historical bootstrap

Do not start by downloading every possible file forever.

Suggested bootstrap order:
1. recent 1–2 years for all target equities;
2. NIFTY 500 / research universe longer history;
3. extend backward based on actual research need.

If official historical access/licensing becomes a constraint, document the alternative provider and retain source identity.

### Gate
A CLI/job can ingest a selected date range from fixtures/live allowed sources and produce:
- raw artifacts;
- normalized Parquet;
- ingestion rows;
- quality report;
- dataset version;
- reproducible query result.

---

# 10. Phase 5 — Corporate actions, adjusted histories, and historical universes

## Goal
Prevent silent errors in returns, screens, and backtests.

---

## 5.1 Corporate actions ingestion

Create normalized event types:

```text
DIVIDEND
SPLIT
BONUS
RIGHTS
MERGER
DEMERGER
SYMBOL_CHANGE
SUSPENSION
DELISTING
OTHER
```

Store original source description as well as structured interpretation.

Fields:

```text
event_id
instrument_id
event_type
announcement_at
ex_date
record_date
effective_at
ratio / amount where applicable
raw_artifact_id
parser_version
status
```

NSE’s corporate-actions surface exposes ex-date and purpose; preserve the source, do not merely scrape a text label into adjusted prices.

---

## 5.2 Adjustment engine

Generate views, not destructive rewrites:

```text
RAW
SPLIT_ADJUSTED
TOTAL_RETURN_ADJUSTED
```

### Tests
Golden fixtures for:
- 2-for-1 split;
- 1:1 bonus;
- cash dividend;
- symbol change;
- delisting.

### Required invariant
A pure split/bonus does not create artificial wealth in portfolio/accounting.

---

## 5.3 Historical universe membership

Create ingestion for target index constituent files/membership sources.

Start with:
- NIFTY 50;
- NIFTY Next 50;
- NIFTY 100/200/500 as useful;
- sector indices used in comparisons;
- F&O-eligible universe with validity dates.

If an official source does not provide convenient full historical membership, build membership history prospectively and use explicit third-party/historical sources only with provenance.

### Do not
Backfill history using today’s constituent set.

### Gate
A test asks:

```text
universe("NIFTY50", date=T)
```

for two dates with a known membership change and gets different correct membership snapshots.

---

# 11. Phase 6 — Equity analytics and daily UI v1

## Goal
Reach the first major product milestone: useful every day even with no derivatives.

---

## 6.1 Market analytics modules

Implement in order:

### Returns/context
- 1D/1W/1M/3M/6M/1Y returns;
- rolling returns;
- drawdown;
- distance from 52-week high/low.

### Liquidity/activity
- ADV/average traded value;
- volume z-score;
- delivery z-score;
- turnover percentile.

### Relative strength
Against:
- NIFTY benchmark;
- sector index;
- custom peer basket.

Define formulas/version them; do not use vague “RS” labels.

### Technical context
Keep technicals limited and interpretable:
- SMA/EMA;
- RSI;
- ATR/range;
- realised volatility;
- trend state.

Do not add 50 indicators.

---

## 6.2 Market dashboard

Replace the old options-first landing page with:

```text
Market Overview
- benchmark indices
- sector performance
- breadth
- highs/lows
- volume/delivery anomalies
- India VIX
- major corporate events/results
- portfolio/watchlist changes
```

All widgets show `as_of` and source/freshness.

---

## 6.3 Stock workspace v1

Tabs:

```text
Overview
Price & Relative Strength
Events
Derivatives (existing features bridged later)
My Research (placeholder until Phase 8)
```

Overview fields should come from canonical IDs, not free-form Yahoo ticker text.

---

## 6.4 Search

Implement instrument search by:
- symbol;
- company name;
- ISIN where available;
- index.

Show exchange/series to disambiguate.

### Gate
Using only the new core:
- search RELIANCE/TCS/etc.;
- display official/current daily history;
- show benchmark-relative chart;
- show delivery/activity metrics;
- show data source/freshness;
- no direct yfinance call from UI page.

This is the first phase where the app begins to feel like the new product.

---

# 12. Phase 7 — Corporate filings, fundamentals, ownership, valuation

## Goal
Turn the stock page from price analytics into actual company research.

NSE currently exposes financial-results and shareholding filing surfaces, including submission/revision metadata. Use those time fields.

---

## 7.1 Filing metadata first

Before extracting every financial line item, create:

```text
corporate_filing
- filing_id
- company_id
- filing_type
- subject
- period_end
- published_at/broadcast_at
- revision_at
- source_url/reference
- raw_artifact_id
- parse_status
```

This lets you deliver event awareness even before full XBRL normalization.

---

## 7.2 Financial facts

Build a canonical metric dictionary.

Start with high-value facts only:
- revenue;
- EBITDA/operating profit where consistently derivable;
- PAT;
- EPS;
- assets;
- debt/borrowings;
- equity;
- cash;
- operating cash flow;
- capex where reliably extractable.

Preserve:
- consolidated vs standalone;
- annual vs quarterly;
- period;
- units;
- source filing;
- publication/revision date.

Do not flatten everything into “latest fundamentals.”

---

## 7.3 Ratio engine

Derived formulas live in code with versions.

Examples:

```text
metric_code
formula_version
numerator periods
units
missing-data rule
```

Start with:
- sales/PAT growth;
- operating/net margins;
- ROE;
- ROCE if inputs are reliable;
- debt/equity;
- interest coverage if inputs available;
- cash conversion.

If a metric cannot be computed consistently from sourced fields, omit it rather than fabricate approximations silently.

---

## 7.4 Shareholding

Ingest quarterly snapshots with:
- as-of date;
- submission date;
- revision date;
- promoter/public categories;
- detailed categories only where source supports them.

Expose change vs previous filed period.

---

## 7.5 Valuation

Compute with clear price date and fundamental period.

Examples:
- P/E TTM;
- P/B;
- earnings yield;
- EV-based measures once enterprise-value inputs are robust.

Add:
- own-history percentile;
- sector peer distribution.

Do not use valuation labels such as “cheap/expensive” without showing the rule/context.

---

## 7.6 Stock workspace v2

Add:

```text
Fundamentals
Valuation
Ownership
Filings
Peers
```

Every chart/table should disclose:
- period;
- consolidated/standalone scope;
- source;
- publication date;
- revisions where relevant.

### Gate
Pick a fixed fixture company and prove:
- filing history is date-ordered;
- revised result does not overwrite prior revision;
- point-in-time query before publication cannot see it;
- shareholding change is computed from correct snapshots;
- valuation can reproduce from source facts + price date.

---

# 13. Phase 8 — Screener, watchlists, research notes, and alerts

## Goal
Make the platform persistent and personal.

---

## 8.1 Screener

Implement a safe expression AST instead of arbitrary Python/SQL input.

Components:
- field registry;
- operator registry;
- universe selector;
- missing-data policy;
- sort/rank;
- as-of date.

Example serialized screen:

```json
{
  "universe": "NIFTY500",
  "as_of": "latest",
  "filters": [
    {"field": "roe_ttm", "op": ">", "value": 0.15},
    {"field": "debt_to_equity", "op": "<", "value": 0.5},
    {"field": "relative_strength_6m_vs_nifty", "op": ">", "value": 0}
  ]
}
```

Store the screen definition/version.

---

## 8.2 Watchlists

Tables:

```text
watchlist
watchlist_item
```

Allow:
- manual membership;
- optional dynamic membership from a screen;
- tags/reason.

---

## 8.3 Research notes/thesis

Add Markdown notes and structured thesis fields:
- thesis summary;
- catalysts;
- risks;
- invalidation conditions;
- review date;
- status.

Research snapshot action should freeze current metrics/source versions.

---

## 8.4 Alert evaluator

Initial alerts should run on daily jobs, not minute-by-minute infrastructure.

Useful v1 rules:
- new filing;
- result announced;
- watchlist price threshold;
- volume/delivery anomaly;
- new 52-week high/low;
- thesis review due;
- portfolio concentration threshold.

Alert record contains evidence payload.

### Gate
- create watchlist;
- save screen;
- run screen as-of historical date;
- attach thesis/note;
- ingest a new filing fixture;
- alert fires once and is deduplicated/cooldown-aware.

---

# 14. Phase 9 — Portfolio ledger and broker read-only integration

## Goal
Create a portfolio system accurate enough to use, independent of broker UI.

---

## 9.1 Ledger schema

```text
portfolio
account
ledger_event
order_reference        optional
position_lot           derived/optional
portfolio_snapshot     derived
```

### Ledger events
- buy/sell;
- brokerage/fees/taxes;
- deposits/withdrawals;
- dividends;
- split/bonus/right adjustments;
- derivative settlement/exercise later.

Use Decimal/fixed precision for money where appropriate; avoid floating-point accounting drift.

---

## 9.2 Position projection

Positions are rebuilt from ledger events.

Support configurable cost-basis policy only when needed; preserve raw lots for tax/accounting inspection.

---

## 9.3 Valuation

Daily mark-to-market from canonical price data.

Compute:
- NAV;
- unrealized/realized P&L;
- income;
- cash;
- exposures;
- benchmark comparison;
- TWR;
- XIRR/MWR where cash-flow semantics warrant it.

---

## 9.4 Broker read-only adapter

First broker integration should be:

```text
BrokerPortfolioProvider
```

not order execution.

Fetch where available:
- holdings;
- positions;
- trades/order history relevant to reconciliation.

Normalize broker IDs through instrument aliases.

### Reconciliation states

```text
MATCHED
QUANTITY_MISMATCH
MISSING_LOCAL
MISSING_BROKER
UNRESOLVED_INSTRUMENT
PRICE_ONLY_DIFFERENCE
```

Never let a broker sync silently mutate the ledger without an explicit import/reconciliation action.

---

## 9.5 Risk v1

- single-name concentration;
- sector concentration;
- benchmark beta;
- rolling volatility;
- max drawdown;
- correlation matrix;
- position contribution to P&L/risk.

Options Greeks can be added when derivatives migrate.

### Gate
- import/replay a deterministic trade ledger;
- exact cash/NAV reconciliation;
- split/dividend handled correctly;
- broker snapshot mismatch surfaced;
- benchmark comparison reproducible.

---

# 15. Phase 10 — Backtest Engine 2.0 (equities first)

## Goal
Build a generic, point-in-time, India-aware research backtester.

Do **not** extend the repaired old options engine into a universal engine. Use what was learned, then build the new abstraction.

---

## 10.1 Backtest specification

```text
BacktestSpec
- start/end
- universe_spec
- data_version
- strategy_config
- portfolio_construction
- risk_config
- execution_model
- fee_schedule_version
- benchmark
- initial_cash
- rebalance_policy
```

---

## 10.2 Event loop

Suggested event types:

```text
SESSION_START
MARKET_DATA
UNIVERSE_CHANGE
CORPORATE_ACTION
SIGNAL
TARGETS
ORDER
FILL
CASHFLOW
SESSION_END
```

Daily strategy v1 does not require high-frequency event complexity; keep interfaces ready but implementation simple.

---

## 10.3 Point-in-time accessor

Create a backtest data context that enforces:

```text
market_date <= simulation_date
published_at <= simulation_timestamp
membership valid at simulation_date
```

No strategy receives a raw repository handle that can bypass time controls.

---

## 10.4 Strategy interface

Example:

```python
class Strategy(Protocol):
    def on_rebalance(self, context) -> list[Signal]: ...
```

Signals describe intent, not fills.

---

## 10.5 Portfolio construction

Separate:
- equal weight;
- rank weight;
- fixed position sizing;
- later volatility/risk targeting.

---

## 10.6 Risk layer

Initial:
- max position weight;
- max sector weight;
- max number positions;
- cash floor;
- liquidity filter;
- drawdown stop for research scenarios.

---

## 10.7 Execution v1

Start with explicit daily modes:
- close signal -> next open;
- next close;
- configurable slippage bps.

Add liquidity participation cap if volume available.

Do not simulate a precise intraday fill from daily OHLC with false confidence.

---

## 10.8 India fee engine

`fee_schedule` table/config with effective dates and source.

Fee calculation should accept:
- segment;
- side;
- turnover;
- order/trade properties;
- effective date.

Rates change; backtest date chooses correct schedule.

---

## 10.9 Corporate events

Backtest portfolio receives split/dividend/delisting events from historical source.

---

## 10.10 Artifacts

Each run writes:

```text
manifest.json
nav.parquet
positions.parquet
orders.parquet
fills.parquet
signals.parquet
metrics.json
warnings.json
```

Manifest contains:
- code commit;
- data versions;
- config hash;
- package environment/lock hash;
- start/end;
- bias controls.

---

## 10.11 Required backtest tests

### Temporal
- future fundamental inaccessible;
- future constituent inaccessible;
- revised filing not visible before revision.

### Accounting
- buy/sell cash equations;
- NAV invariant;
- dividend cash flow;
- split quantity/value preservation;
- fees reconcile.

### Universe
- newly listed security appears only after listing;
- delisted security exits lifecycle;
- constituent changes reflected.

### Execution
- next-open signal cannot fill at prior close;
- slippage worsens execution in correct direction.

### Reproducibility
Same manifest/data/code -> same result.

### Gate
Run at least three simple benchmark strategies and verify invariants. Strategy profitability is irrelevant to acceptance.

---

# 16. Phase 11 — Futures and options migration/integration

## Goal
Put the existing strongest work back into the new platform on correct foundations.

---

## 11.1 Move options modules incrementally

Suggested move order:
1. pricing;
2. Greeks;
3. IV;
4. volatility helpers;
5. surface;
6. SVI;
7. arbitrage;
8. strategy definitions.

Use temporary compatibility imports so UI/tests do not break in one giant commit.

---

## 11.2 Contract master

Derivatives must reference canonical contract rows.

Fields from current NSE/broker instrument master:
- underlying;
- expiry;
- strike;
- CE/PE;
- lot size;
- tick size;
- segment;
- current exercise/settlement rules with validity dates.

Current NSE documentation states individual-stock options are European style and physically settled; encode contract rules from reference data rather than retaining American-option assumptions as core behavior.

---

## 11.3 Futures analytics

Add:
- spot/futures basis;
- annualized basis/carry;
- OI/volume;
- contract roll calendar;
- continuous futures research series with explicit roll method.

Never treat a stitched futures series as an actually tradable contract without roll accounting.

---

## 11.4 Real options chain workflow

Wire the previously disconnected pieces:

```text
Derivative provider
 -> chain normalization
 -> bid/ask QC
 -> canonical contracts
 -> IV solve
 -> surface
 -> SVI optional
 -> arbitrage diagnostics
 -> UI
```

Remove simulated surface as default when real market chain is available; keep simulation clearly labeled.

---

## 11.5 Quant hardening

Before declaring option analytics “serious use”:
- calendar-arbitrage checks at fixed log-forward-moneyness;
- robust non-uniform-strike convexity tests;
- q/dividend-aware forward;
- SVI invalid-calibration flagging;
- expired contract rejection;
- same-length batch-IV input validation;
- market spread/quote QC connected to surface QC;
- per-leg IV from surface for multi-strike strategies where appropriate.

---

## 11.6 Option backtesting modes

Keep distinct:

```text
MODEL_BASED_SIMULATION
SNAPSHOT_REPLAY
```

Never blend their performance reports.

### Gate
A real-chain fixture flows end-to-end through normalization -> IV -> surface -> diagnostics. Contract expiry/lot-size/accounting tests pass.

---

# 17. Phase 12 — Option snapshot collector and derivatives market intelligence

## Goal
Start building proprietary personal historical evidence that is difficult to recreate later.

---

## 12.1 Scope carefully

Do not collect every option every second.

Initial configurable universe:
- NIFTY;
- selected major index derivatives available at that time;
- user-selected F&O stocks.

Initial cadence can be modest and measured.

---

## 12.2 Collector design

```text
scheduler
 -> provider fetch
 -> raw archive
 -> canonical contract resolve
 -> quote QC
 -> append Parquet partition
 -> collection manifest
```

Partition by:

```text
underlying / trade_date / snapshot_hour (if needed)
```

---

## 12.3 Snapshot quality

Flags:
- crossed quote;
- zero/invalid bid/ask;
- stale timestamp;
- missing OI;
- illiquid spread;
- unresolved contract;
- underlying mismatch.

---

## 12.4 Derivative intelligence UI

Once data exists:
- OI by strike;
- OI change;
- IV smile/skew;
- IV term structure;
- PCR with explicit definition;
- futures basis;
- India VIX context;
- snapshot history.

Do not present max-pain/PCR-type indicators as predictive truth; label definition and limitations.

### Gate
- collector survives restart without duplicates;
- idempotent same-snapshot ingestion;
- raw/normalized counts reconcile;
- historical snapshot query reproduces chain state.

---

# 18. Phase 13 — ML research framework

## Goal
Only now make ML a serious research subsystem.

This phase produces **research-grade experiments**, not user-facing stock calls.

---

## 13.1 Dataset builder

Features must be built `as_of` time with provenance.

Example:

```text
DatasetSpec
- universe
- start/end
- feature_set
- label
- rebalance frequency
- point-in-time rules
- embargo/purge
```

---

## 13.2 Feature registry

Each feature:
- name;
- version;
- required history;
- formula;
- source datasets;
- availability delay.

---

## 13.3 Forecast research targets

Start with a small target set rather than dozens of models:

```text
5D / 20D / 60D direction probability
20D relative outperformance vs benchmark
5D / 20D / 60D realised-volatility forecast
return quantiles / distribution where method is validated
later: drawdown-risk and regime forecasts
```

Do not start with exact future-price prediction as the primary target.

---

## 13.4 Validation

Prefer:
- expanding/walk-forward;
- purge overlapping label periods;
- final holdout untouched during model selection;
- sector/regime/time-slice evaluation;
- baseline comparisons on exactly the same cohort.

Report prediction metrics and portfolio relevance separately.

For probability models, include calibration/Brier or log-loss style evaluation—not accuracy alone.

For distribution/regression outputs, include out-of-sample error/coverage appropriate to the forecast type.

---

## 13.5 Artifact envelope

```text
model type
actual implementation/fallback status
feature schema
normalizer/scaler
training windows
hyperparameters
weights/model object
data version
code commit
metrics
calibration artifact
baseline metrics
approved_for_production=false by default
```

Never label a fallback estimator as the requested model.

### Gate
A stored experiment can be reproduced and loaded to produce identical point-in-time features/predictions on a fixture, and its final holdout/baseline results are recorded.

No experiment is user-facing merely because it beat another ML model.

---

# 19. Phase 14 — Production prediction and forecast layer

## Goal
Turn only approved research models into an auditable production prediction system.

This phase is where “prediction” becomes a real product capability.

---

## 14.1 Production forecast contract

Create:

```text
forecast_definition
- target
- horizon
- universe scope
- benchmark if applicable
- model deployment/version
- feature/label version
- minimum data quality
- abstention policy
- calibration version
- active validity interval
```

Initial production families:
- direction probability;
- relative outperformance probability;
- realised-volatility forecast;
- return quantiles/range only when validated;
- later drawdown-risk/regime forecasts.

---

## 14.2 Model promotion

A model may move from experiment -> production only when:
- point-in-time dataset checks pass;
- walk-forward/final holdout results exist;
- baseline comparison is recorded;
- calibration/error is acceptable under a documented rule;
- feature availability is reliable in production;
- inference latency/operability is acceptable;
- the model has an explicit supported universe/horizon;
- an abstention rule exists.

Promotion is an explicit metadata event; it is not inferred from “best RMSE.”

---

## 14.3 Permanent prediction ledger

Create immutable `prediction_record` rows.

Required fields:

```text
prediction_id
forecast_id
instrument_id
prediction_as_of
data_cutoff_at
generated_at
expected_horizon_end
model_version
data_version
code_commit
probabilities / quantiles / interval
confidence bucket
calibration state
coverage/abstention state
quality flags
explanation feature refs
```

Never overwrite old predictions after retraining.

---

## 14.4 Scheduled inference

Jobs generate forecasts only when:
- required EOD/fundamental inputs are current;
- data quality is non-blocking;
- instrument belongs to supported universe;
- model deployment is active;
- required lookback exists.

If not, emit/surface an explicit state rather than silently using stale/fallback input.

---

## 14.5 Confidence and abstention

Support:

```text
HIGH
MEDIUM
LOW
NO_RELIABLE_SIGNAL
```

`NO_RELIABLE_SIGNAL` can be caused by:
- low calibrated confidence;
- model disagreement;
- out-of-distribution input;
- stale/missing data;
- insufficient history;
- too-wide uncertainty;
- unsupported market regime where defined by policy.

Track **coverage** alongside performance.

---

## 14.6 Outcome evaluator

When a forecast horizon matures, a deterministic job creates `prediction_evaluation`.

Evaluate:
- observed return/outcome;
- benchmark-relative outcome if applicable;
- correctness/error;
- probability scoring/calibration;
- forecast interval/quantile coverage;
- sector/regime/confidence bucket at issuance.

Never evaluate using information unavailable under the original prediction definition except the matured outcome itself.

---

## 14.7 Prediction scorecards

Build scorecards by:
- forecast family;
- horizon;
- model version;
- sector;
- market-cap bucket;
- market regime;
- confidence bucket;
- calendar period;
- liquidity bucket where relevant.

Always show:
- sample count;
- baseline;
- coverage/abstention;
- calibration/error;
- last evaluation date.

Do not present a 63% hit rate without its cohort size, baseline, time window, and coverage.

---

## 14.8 Stock UI — Predictions tab

Show only validated production forecasts, for example:

```text
20D positive-return probability
20D NIFTY-outperformance probability
20D realised-vol forecast
expected return range / quantiles
regime state
confidence / abstention
```

Also show:
- model version;
- as-of/data cutoff;
- historical scorecard link;
- what factors most influenced the model where explainability is supported;
- warning when models disagree.

### Required tests/gate
1. no prediction can use a feature newer than `prediction_as_of`;
2. prediction rows are immutable;
3. evaluation cannot occur before horizon maturity;
4. same model/data/config produces same fixture prediction;
5. stale/blocking input causes abstention/failure rather than silent output;
6. probability calibration report reconciles to evaluation rows;
7. simple baselines are computed on the same cohort;
8. UI can display `NO_RELIABLE_SIGNAL` without forcing a directional view.

---

# 20. Phase 15 — Opportunity and decision-support engine

## Goal
Turn trustworthy data, events, screens, forecasts, portfolio context, and research state into a prioritized list of **what deserves attention**.

This is the suggestion layer. It must remain explainable and non-automatic.

---

## 15.1 Inputs

The engine may consume:
- saved screens;
- market/sector analytics;
- production forecasts;
- corporate filings/events;
- watchlists;
- thesis/review state;
- portfolio exposures/risk;
- derivative intelligence where available;
- data/model freshness.

---

## 15.2 Opportunity schema

```text
opportunity_snapshot
- opportunity_id
- generated_at
- as_of
- scope/instrument/portfolio
- opportunity_type
- attention_state
- research_lens
- supporting_evidence refs
- conflicting_evidence refs
- prediction refs
- screen refs
- event refs
- portfolio-context refs
- freshness state
- confidence state
- explanation version
```

Attention states:

```text
MONITOR
RESEARCH
HIGH_INTEREST
REVIEW
RISK_WARNING
NO_RELIABLE_SIGNAL
```

These are attention states—not BUY/SELL actions.

---

## 15.3 Research lenses

Implement configurable lenses:

### Long-term
Weight/priority context from:
- growth;
- profitability/quality;
- debt/cash flow;
- valuation;
- ownership;
- filings/events.

### Swing/positional
Emphasize:
- momentum/relative strength;
- sector strength;
- volume/delivery;
- volatility/regime;
- event risk.

### Derivatives
Emphasize:
- IV/realised-vol relationship;
- surface/skew/term structure;
- OI/change in OI;
- spread/liquidity;
- expiry/event context.

The lens changes prioritization, not the underlying data.

---

## 15.4 “Why am I seeing this?”

Every opportunity must have a deterministic explanation payload containing:
- trigger(s);
- supporting evidence;
- evidence against;
- forecast references and confidence;
- relevant event/portfolio context;
- freshness/quality status;
- rule/explanation version.

The UI must be able to show both sides.

---

## 15.5 Conflict engine

Rules downgrade/suppress a suggestion when, for example:
- models materially disagree;
- only one weak signal exists;
- critical data is stale;
- corporate event risk is imminent and policy requires caution;
- liquidity is insufficient;
- portfolio concentration would worsen materially;
- forecast is `NO_RELIABLE_SIGNAL`.

Do not force an opportunity every day.

---

## 15.6 “What should I look at today?”

Generate a small prioritized daily brief combining categories such as:

```text
Portfolio attention
New material watchlist/company filing
High-interest research candidate
Unusual market/sector condition
Derivative volatility/OI anomaly
Thesis review due
```

Ranking factors may include:
- materiality;
- novelty since last review;
- portfolio exposure;
- watchlist/research relevance;
- forecast confidence;
- evidence breadth;
- freshness;
- cooldown/deduplication.

Keep the brief intentionally short enough to be usable.

---

## 15.7 Portfolio-aware decision support

Examples:
- concentration threshold crossed;
- two holdings create similar correlated exposure;
- major portfolio holding has a new filing/result event;
- candidate would materially increase sector concentration;
- portfolio beta/vol/drawdown state changed;
- derivative exposure raises Greeks/risk threshold.

The engine surfaces the issue and possible investigation. It does not place trades or silently rebalance.

---

## 15.8 Opportunity history

Persist enough history to answer:
- why an item surfaced on a date;
- which evidence changed;
- whether confidence changed;
- whether the same issue has repeated;
- which version of ranking/explanation logic produced it.

### Required tests/gate
1. every opportunity has at least one stored trigger/evidence reference;
2. conflicting evidence is retained, not dropped;
3. stale critical inputs suppress/downgrade according to policy;
4. duplicate/cooldown behavior is deterministic;
5. `NO_RELIABLE_SIGNAL` prevents false directional suggestion when required;
6. portfolio-aware suggestion reproduces from the same snapshot;
7. “Why am I seeing this?” can be generated without asking an LLM to invent reasons.

---

# 21. Phase 16 — Evidence-grounded AI research assistant

## Goal
Use AI to reduce research effort, explain evidence, and interact naturally with predictions/opportunities—not to replace deterministic calculations or manufacture investment calls.

---

## 16.1 Retrieval sources

Allow retrieval over:
- corporate filing metadata/content where rights allow;
- normalized fundamental facts;
- corporate events;
- research notes;
- watchlists;
- portfolio state;
- market analytics snapshots;
- immutable prediction records and scorecards;
- opportunity/attention snapshots and evidence payloads.

---

## 16.2 Tool-first assistant

The assistant should call deterministic tools for:
- ratios;
- returns;
- portfolio calculations;
- screen results;
- comparisons;
- prediction scorecards/calibration;
- opportunity explanation;
- model disagreement/confidence state.

LLM role:
- summarize;
- compare;
- explain;
- synthesize evidence;
- translate model/portfolio outputs into understandable language.

Not:
- perform unsourced arithmetic from memory;
- invent missing company facts;
- invent model probabilities;
- upgrade `NO_RELIABLE_SIGNAL` into a directional claim;
- output unsupported buy/sell decisions.

---

## 16.3 Evidence contract

Every generated research answer stores/returns:
- source IDs;
- timestamps;
- excerpts/metric IDs;
- calculation references;
- prediction/opportunity IDs where used;
- “data current as of” value.

### Gate
A test asks a question for which a future filing exists but is outside the as-of date; assistant cannot retrieve/cite it.

A second test asks why an opportunity was surfaced; assistant explanation must remain consistent with the deterministic stored evidence payload.

---

# 22. Phase 17 — Optional paper/live execution boundary

## Goal
Only if personal usage proves it is valuable.

This phase is optional and the platform is already successful without it.

---

## 17.1 Sequence

```text
read-only broker
 -> paper execution
 -> generated order ticket
 -> human confirmation
 -> guarded live adapter (optional)
```

Predictions/opportunities never bypass this sequence.

---

## 17.2 Safety requirements before live mode

- re-check current SEBI/NSE/broker API rules;
- broker-required static IP/auth controls where applicable;
- separate live credentials;
- order-size caps;
- allowed-instrument whitelist;
- max daily turnover/loss;
- kill switch;
- duplicate-order protection/idempotency key;
- reconciliation after every order/fill;
- audit log;
- live/paper environment cannot be confused visually;
- no order may be generated solely because a model probability crossed a threshold unless an explicitly tested strategy/policy and risk layer authorizes it.

NSE’s retail algorithmic trading implementation standards currently include static-IP mapping requirements for client API access, but these rules must be re-verified at implementation time.

---

# 23. File-by-file migration mapping from the current repo

| Current path | Short-term action | Long-term target |
|---|---|---|
| `run.py` | keep | UI bootstrap/application wiring |
| `config/settings.py` | consolidate | `src/core/settings.py` |
| `config/errors.py` | keep/move | `src/core/errors.py` |
| `data/market_data.py` | freeze after compatibility wrapper | replaced by capability providers |
| `data/cache.py` | reuse concept | provider/cache service |
| `data/normalization.py` | split by schema/domain | ingestion normalization |
| `analytics/pricing.py` | preserve tests | derivatives/options/pricing |
| `analytics/greeks.py` | preserve | derivatives/options/greeks |
| `analytics/implied_vol.py` | harden | derivatives/options/implied_vol |
| `analytics/volatility.py` | generalize | market/volatility + derivative helpers |
| `analytics/iv_surface.py` | integrate/harden | derivatives/options/surface |
| `analytics/smile.py` | harden | derivatives/options/svi |
| `analytics/arbitrage.py` | mathematically correct | derivatives/options/arbitrage |
| `analytics/american.py` | keep non-core | derivatives/options/models/american |
| `analytics/rates.py` | generalize for Indian curve | rates/domain |
| `strategies/*` | split | generic strategy vs derivative strategies |
| `risk/*` | replace domain assumptions | portfolio/risk |
| `backtesting/engine.py` | repair, then legacy | new `backtest/` engine |
| `backtesting/metrics.py` | fix reusable metrics | backtest/metrics |
| `backtesting/simulation.py` | keep educational | derivatives/options/simulation |
| `ml/*` | fix, pause, then migrate | research/ml experimentation; approved deployments feed `prediction/` |
| `sentiment/*` | de-prioritize | later event/document intelligence |
| `visualization/*` | retain reusable chart funcs | workflow-oriented visualization |
| `ui/pages/*` | gradually replace navigation | market/equity/portfolio/research/prediction UI |

Use compatibility imports for migrated quant modules until all callers move.

---

# 24. Database migration sequence

Recommended migration order:

```text
0001_core_sources_and_ingestion
0002_instruments_and_aliases
0003_companies_indices_memberships
0004_exchange_calendar
0005_corporate_events
0006_filings_and_fundamental_facts
0007_shareholding
0008_watchlists_research
0009_alerts
0010_portfolio_ledger
0011_backtest_runs
0012_derivative_contract_metadata
0013_ml_experiments
0014_forecast_definitions_and_deployments
0015_prediction_ledger_and_evaluations
0016_opportunity_attention_snapshots
0017_ai_interactions_evidence_refs        optional when Phase 16 begins
```

Avoid giant initial migration with every future table.

---

# 25. Data jobs and scheduling

## Job families

```text
reference_master_sync
calendar_sync
eod_equity_ingest
delivery_ingest
corporate_actions_sync
corporate_filings_sync
fundamentals_parse
shareholding_sync
index_membership_sync
analytics_materialization
alert_evaluation
portfolio_mark
option_snapshot_collect
ml_experiment_evaluate
prediction_generate
prediction_outcome_evaluate
prediction_scorecard_refresh
opportunity_refresh
daily_attention_brief
```

## Scheduling initial implementation
For a personal Windows system, start with:
- CLI commands;
- Windows Task Scheduler or a simple Python scheduler;
- database-backed run state.

Do not deploy Airflow/Prefect merely to schedule a modest personal workload. Add an orchestrator only if operational evidence demands it. Prediction jobs must depend on successful/quality-approved upstream data rather than simply running because the clock fired.

---

# 26. CLI commands

A serious system should be operable without clicking Streamlit.

Examples:

```text
python -m app instruments sync --provider <provider>
python -m app nse ingest-eod --date 2026-09-21
python -m app nse ingest-range --from ... --to ...
python -m app corporate sync --since ...
python -m app quality check --dataset ...
python -m app analytics build --as-of ...
python -m app backtest run configs/momentum.yaml
python -m app portfolio reconcile --provider <broker>
python -m app options collect --underlying NIFTY
python -m app predict run --forecast <forecast_id> --as-of 2026-09-21
python -m app predict evaluate --matured-through 2026-09-21
python -m app predict scorecard --forecast <forecast_id>
python -m app opportunities refresh --as-of 2026-09-21
python -m app brief today --as-of 2026-09-21
```

Commands should output run IDs and failure reasons.

---

# 27. Golden fixture design

Do not make tests depend on live NSE/broker APIs.

Create a small synthetic+captured fixture universe, for example:

```text
2-3 equities
1 index
1 membership change
1 split
1 dividend
1 symbol alias change
2 financial filing revisions
1 shareholding revision
1 future
several option contracts across 2 expiries
several issued predictions with known matured outcomes
1 abstained prediction case
1 opportunity with supporting + conflicting evidence
1 portfolio-aware risk-attention case
```

Store legally permitted/synthetic fixture data under `tests/fixtures/`.

This dataset should be rich enough to test the hardest temporal/accounting rules.

---

# 28. Definition of “point-in-time safe”

A dataset/query qualifies only if:

1. securities exist/listed at the as-of date;
2. universe membership is valid on that date;
3. filing `published_at <= as_of`;
4. revision is visible only after `revision_at`;
5. corporate action is applied according to announcement/effective semantics relevant to the calculation;
6. no current-state backfill silently overwrites historical values;
7. feature calculations only use prior/available observations;
8. label windows never leak into training features/splits.

Add a `PointInTimeViolation` exception for impossible access in backtest/research modes.

---

# 29. Data Health acceptance surface

Before trusting the platform daily, build `/Data Health`.

Show:

| Dataset | Last expected date | Last good ingest | Status | Rows | Warnings |
|---|---:|---:|---|---:|---|
| NSE EOD | ... | ... | GOOD | ... | ... |
| Delivery | ... | ... | GOOD | ... | ... |
| Corporate actions | ... | ... | WARN | ... | ... |
| Fundamentals | ... | ... | GOOD | ... | ... |
| Broker master | ... | ... | STALE | ... | ... |

Click-through:
- ingestion run;
- raw hash;
- quality failures;
- unresolved symbols.

This is not admin polish. It is what tells you whether today’s conclusions can be trusted.

---

# 30. Research/product UX sequence

Do not design every page before data exists.

Recommended UI release order:

## UI Release A
- Market;
- Stock search;
- Stock price/activity page;
- Data Health.

## UI Release B
- Fundamentals;
- Ownership;
- valuation/peers;
- filings/events.

## UI Release C
- Screener;
- Watchlists;
- Research notes;
- alerts.

## UI Release D
- Portfolio;
- performance/risk.

## UI Release E
- Backtest research lab.

## UI Release F
- Futures/options integrated tabs.

## UI Release G
- Predictions tab;
- Model & Prediction Health;
- Opportunities;
- “What should I look at today?” brief.

## UI Release H
- AI assistant over evidence + predictions + opportunities.

---

# 31. Performance and storage checkpoints

Measure before scaling.

## Checkpoint after Phase 4
Record:
- total NSE daily rows;
- raw disk usage;
- Parquet disk usage;
- typical stock-history query latency;
- all-universe cross-section query latency.

## Checkpoint after option collector
Record per day:
- snapshots;
- contracts;
- compressed storage;
- query latency.

Only then decide whether partitioning/cadence needs change.

---

# 32. Failure/recovery design

## Ingestion
- idempotency key = provider + dataset + source date/version;
- retry fetch separately from publish;
- failed run leaves last-good dataset untouched;
- parser upgrades can replay raw artifacts.

## Database
- transactions for metadata publication;
- unique constraints enforce natural keys.

## Option collector
- resume from last successful scheduled slot;
- no duplicate normalized snapshot on retry.

## Broker sync
- read-only import failure cannot alter local ledger;
- reconciliation is repeatable.

---

# 33. Logging rules

Structured keys:

```text
run_id
job
provider
dataset
instrument_id
trade_date
phase
severity
```

Never log:
- API tokens;
- session secrets;
- sensitive broker credential payloads.

---

# 34. Documentation that must live with code

Create:

```text
docs/
├── architecture/
│   ├── overview.md
│   ├── identity.md
│   ├── point_in_time.md
│   ├── storage.md
│   └── backtesting.md
├── data_sources/
│   ├── nse.md
│   ├── broker_provider.md
│   └── licensing.md
├── operations/
│   ├── local_setup_windows.md
│   ├── ingestion.md
│   ├── backup_restore.md
│   └── data_health.md
├── methodology/
│   ├── adjustments.md
│   ├── fundamentals.md
│   ├── metrics.md
│   ├── fees.md
│   ├── prediction_validation.md
│   ├── calibration_and_abstention.md
│   └── decision_support.md
└── migration/
    ├── BASELINE_2026.md
    └── phase_reports/
```

Each methodology doc should state formulas/assumptions and version history.

---

# 35. Phase completion report template

Every phase report:

```markdown
# Phase X Completion Report

## Status
VERIFIED / NOT YET VERIFIED

## Starting commit
...

## Ending commit
...

## Scope completed
...

## Files changed
...

## Database migrations
...

## Data evidence
- raw source artifacts
- hashes
- row counts
- quality results

## Tests
- command
- result

## Acceptance gates
- [x] ...
- [ ] ...

## Known limitations
...

## Deferred items
...

## Next phase entry conditions
...
```

Never mark `VERIFIED` if an acceptance gate is waived without an explicit exception record.

---

# 36. Priority matrix

## P0 — must be correct before expansion
- CI visibility;
- current backtest fill/NAV/expiry bugs;
- stock multiplier;
- configuration source of truth;
- ML leakage if ML remains enabled;
- canonical instrument identity;
- point-in-time model;
- raw/provenance model.

## P1 — highest product value
- NSE EOD/delivery ingestion;
- corporate actions;
- historical universes;
- stock workspace;
- fundamentals/filings/shareholding;
- screener/watchlists;
- portfolio ledger;
- equity backtesting.

## P2 — high value after core trust
- futures analytics;
- real options integration;
- option snapshot collector;
- derivatives OI/flow reports;
- leakage-safe ML research;
- calibrated production forecasting;
- opportunity/decision-support layer;
- AI evidence layer.

## P3 — optional / only if evidence justifies
- highly complex deep learning beyond validated baselines;
- intraday large-universe collection;
- public deployment;
- automated execution.

---

# 37. What not to build yet

Explicit backlog freeze until the appropriate gate:

- opaque exact-price/guaranteed-return predictor or deep-learning stock picker before Phase 13–14 gates;
- reinforcement-learning trader;
- social-media sentiment crawler;
- 100-indicator technical dashboard;
- tick-by-tick all-NSE collector;
- microservices;
- Kubernetes;
- multi-user auth/billing;
- public market-data redistribution;
- automated broker trading;
- a universal “AI BUY/SELL” score that bypasses the evidence/conflict/abstention design.

If one of these becomes attractive mid-build, require a written reason showing it solves a current validated user problem.

---

# 38. Suggested first 20 implementation commits

These are deliberately small and ordered.

1. `docs: record current migration baseline and known defects`
2. `ci: decouple lint and unit-test jobs`
3. `build: introduce reproducible dependency lock/constraints`
4. `fix(backtest): use executable fill price in accounting`
5. `fix(backtest): separate cash and marked-to-market NAV`
6. `fix(backtest): settle and close positions at expiry`
7. `test(backtest): add economic accounting invariants`
8. `fix(ui): correct average pnl and backtest labeling`
9. `fix(risk): correct equity multiplier and multi-instrument valuation contract`
10. `refactor(config): create one runtime settings source`
11. `fix(ml): purge overlapping forward labels at split boundaries`
12. `fix(ml): validation-only model selection and artifact identity`
13. `feat(core): add source and ingestion-run models`
14. `feat(instruments): add canonical instrument and alias schema`
15. `feat(storage): add postgres migrations and repositories`
16. `feat(providers): add capability contracts and result envelope`
17. `feat(calendar): add NSE exchange-session model and loader`
18. `feat(reference): ingest first broker/NSE instrument-master fixture`
19. `test(identity): verify alias validity across derivative expiry`
20. `feat(data-health): show reference-data freshness and unresolved aliases`

Only after this sequence start the EOD pipeline.

---

# 39. Suggested branch strategy

For a solo project, keep this simple.

```text
main                       always runnable
feature/<phase-unit>       short-lived
```

Do not maintain a six-month `v2-rewrite` branch.

For major database phases:
- branch;
- migration + code + tests together;
- merge only with clean gate.

Tag important stable milestones:

```text
v0-option-baseline
v1-data-foundation
v2-equity-research
v3-portfolio-backtest
v4-derivatives-integrated
```

Names can change; the principle is stable restore points.

---

# 40. Local Windows developer setup target

A future `README`/setup should get from clone to working system with roughly:

```powershell
git clone <repo>
cd <repo>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
docker compose up -d postgres
alembic upgrade head
python -m app doctor
streamlit run run.py
```

`app doctor` should check:
- Python version;
- DB connectivity;
- writable data directories;
- migration status;
- optional provider credentials;
- latest data status.

---

# 41. Backups before the platform becomes personally important

Implement by Phase 9 at latest:

## PostgreSQL
- automated daily dump;
- retention policy;
- restore test.

## Files
Backup:
- raw archive;
- Parquet;
- research notes/attachments;
- option snapshots;
- configs/manifests.

## Verification
Monthly restore into a temporary database and compare row counts/checksums.

---

# 42. India-specific implementation notes derived from current research

## 40.1 Official NSE report formats evolve
Old bhavcopy formats have been discontinued in favor of UDiFF common bhavcopy on current report pages. Use parser/version adapters and archive source artifacts.

## 40.2 Corporate-data timestamps matter
NSE corporate/shareholding pages expose submission/revision/broadcast dates. Use them for point-in-time queries.

## 40.3 Broker history differs
Current public docs show meaningful differences:
- Upstox V3 daily history can extend back to 2000 and minute history from 2022 under documented limits;
- Dhan documents daily data back to scrip inception and recent multi-year intraday capabilities;
- Zerodha historical access has derivative token lifecycle constraints and continuous-futures support.

Therefore provider capability metadata must include historical coverage and retrieval constraints; do not assume one interchangeable `get_stock_data(period="2y")` call.

## 40.4 Market reference data changes
Lot size, expiry series, and other derivative specifications can change. Reference data needs validity dates.

## 40.5 Data rights matter
NSE has explicit data-sharing/usage policies and paid historical/realtime/corporate products. Personal research architecture should keep source/license metadata and avoid assuming redistribution rights.

## 40.6 Retail algo rules matter only when execution is added
Current NSE implementation standards for retail API/algo access include static-IP mapping requirements. Recheck then; do not contaminate research architecture with trading constraints now.

---

# 43. External architecture patterns intentionally adopted

## From OpenBB
Adopt:
- provider-independent standardized query/result models;
- capability/provider separation;
- core logic consumable from more than one UI.

Do not copy:
- plugin ecosystem complexity not needed for a solo local system.

## From QuantConnect LEAN
Adopt:
- universe selection;
- signal/alpha separation;
- portfolio construction;
- risk management;
- execution separation;
- explicit corporate-action lifecycle ideas.

Do not copy:
- institutional-scale engine complexity before required.

## From Qlib
Adopt:
- reproducible data -> feature/model -> backtest workflow;
- experiment artifacts;
- separation of prediction metrics from portfolio evaluation.

Do not copy:
- ML-first product priorities.

## From vectorbt-style research systems
Adopt conceptually:
- separate simulation outputs from post-analysis;
- efficient vectorized research where semantics permit.

Do not force vectorization where event/corporate-action/accounting semantics become opaque.

---

# 44. Success metrics for the platform itself

Do not measure only code size/features.

## Data trust
- % scheduled EOD ingests successful;
- unresolved instrument rate;
- data-quality blocking incidents;
- days since last successful backup restore.

## Research usefulness
- time from search to full stock workspace;
- watchlist/filing changes surfaced automatically;
- percentage of displayed facts with traceable source;
- historical screen reproducibility.

## Portfolio correctness
- reconciliation difference vs broker;
- NAV accounting invariant failures = zero;
- corporate-action reconciliation errors = zero.

## Backtest integrity
- point-in-time violations = zero;
- reproducible run rate;
- all run manifests complete;
- corporate-action/fee tests passing.

## Derivatives
- option snapshot completeness;
- quote-QC rejection rate;
- IV solve convergence by liquidity bucket;
- no expired contract carried past lifecycle.

## Prediction integrity
- prediction rows rewritten after issuance = zero;
- point-in-time violations = zero;
- baseline comparison coverage = 100% for production forecasts;
- calibration/error tracked by model/horizon;
- abstention/coverage rate visible;
- matured predictions evaluated on schedule;
- drift or performance deterioration surfaced.

## Decision-support usefulness
- % surfaced opportunities with complete evidence payload;
- conflicting evidence retained when present;
- duplicate/cooldown suppression rate;
- daily brief stays within configured attention budget;
- user can trace every item to screen/event/prediction/portfolio evidence;
- no suggestion triggers an order without the separate execution policy boundary.

---

# 45. Milestone definitions

## Milestone A — “I trust the data”
Phases 0–5 complete.

You can inspect provenance, data health, corporate actions, and historical universe state.

## Milestone B — “I use this for stock research”
Phases 6–8 complete.

Market dashboard, stock workspace, fundamentals, screens, notes, alerts are useful daily.

## Milestone C — “I use this for my own portfolio”
Phase 9 complete.

Ledger, performance, exposures, reconciliation are trusted.

## Milestone D — “I trust its backtests”
Phase 10 complete.

Point-in-time, cost-aware equity backtesting is reproducible.

## Milestone E — “Derivatives add information, not complexity”
Phases 11–12 complete.

Existing options expertise is integrated with real Indian contracts and collected snapshots.

## Milestone F — “I can measure whether its predictions deserve trust”
Phases 13–14 complete.

Forecasts are point-in-time, versioned, calibrated/evaluated against baselines, permanently logged, and capable of abstaining.

## Milestone G — “The system tells me what deserves attention and why”
Phase 15 complete.

Daily opportunities and portfolio/research attention items are prioritized, explainable, conflict-aware, freshness-aware, and never forced into a buy/sell verdict.

## Milestone H — “AI saves me research time”
Phase 16 complete.

Assistant is evidence-grounded, can explain forecasts/opportunities, and delegates calculations to deterministic services.

Live execution in Phase 17 is deliberately **not** a required milestone.

---

# 46. Mandatory review checkpoints

Before proceeding past the following phases, stop and audit.

## After Phase 1
Question: Are we carrying any known correctness bug into new architecture?

## After Phase 4
Question: Can we trace and reproduce every displayed EOD market value?

## After Phase 5
Question: Are returns/universes point-in-time safe enough to build research on?

## After Phase 7
Question: Do fundamental/ownership data preserve publication/revision timing?

## After Phase 9
Question: Does portfolio accounting reconcile exactly?

## After Phase 10
Question: Can deliberately adversarial leakage tests fool the backtester?

## After Phase 12
Question: Is option history real snapshot data vs synthetic data clearly distinguishable everywhere?

## After Phase 14
Question: Do production forecasts beat/document appropriate baselines, remain calibrated enough for their stated use, preserve prediction history, and abstain when they should?

## After Phase 15
Question: Can every suggestion be explained from deterministic evidence, including evidence against, without an LLM inventing the reason?

## After Phase 16
Question: Does the AI preserve point-in-time/evidence boundaries and accurately explain deterministic model/portfolio outputs?

Only redesign at these checkpoints if evidence reveals a structural problem. Do not continuously reopen architecture for aesthetic reasons.

---

# 47. Initial implementation scope I recommend starting immediately

Do **not** start by implementing this entire document.

The first execution unit should be:

```text
UNIT 1 — TRUSTWORTHY MIGRATION BASELINE

1. Record baseline/known defects.
2. Make CI show both lint and tests.
3. Fix current backtest executable-fill bug.
4. Fix NAV/accounting.
5. Fix expiry lifecycle.
6. Add economic regression tests.
7. Fix stock multiplier.
8. Consolidate runtime Settings/DayCount.
9. Add root LICENSE/dependency lock.
10. Produce Phase 1 report.
```

Then:

```text
UNIT 2 — INDIA DATA FOUNDATION

1. PostgreSQL + Alembic.
2. Source/ingestion/raw artifact tables.
3. Canonical instrument + alias tables.
4. Provider capability contracts.
5. NSE calendar.
6. First instrument-master provider.
7. Data Health v0.
8. Identity/time regression fixtures.
```

Then:

```text
UNIT 3 — NSE DAILY MARKET PIPELINE
```

This sequencing deliberately delays exciting UI work until the foundation can support it correctly.

---

# 48. Definition of done for the entire transformation

The repository can be considered transformed only when:

- [ ] equities are first-class and the primary UX;
- [ ] canonical instruments are independent of providers;
- [ ] NSE daily history is stored with raw provenance and quality status;
- [ ] corporate actions and historical universe membership are modeled;
- [ ] fundamentals/shareholding are point-in-time aware;
- [ ] stock research workspace is source-transparent;
- [ ] screener can run historically without current-state leakage;
- [ ] research notes/watchlists/alerts persist;
- [ ] portfolio is ledger-based and reconciles;
- [ ] equity backtests are point-in-time and fee/corporate-action aware;
- [ ] derivatives are linked to canonical underlyings/contracts;
- [ ] real vs simulated option data is unmistakably separated;
- [ ] option snapshots can be collected/replayed;
- [ ] ML experiments are leakage-safe, baseline-compared, and reproducible;
- [ ] approved production forecasts are immutable, point-in-time, calibrated/evaluated, and versioned;
- [ ] prediction history can be scored after horizon maturity by model/horizon/sector/regime/confidence;
- [ ] `NO_RELIABLE_SIGNAL` is a supported first-class output;
- [ ] opportunities/suggestions retain triggers, evidence for, evidence against, prediction refs, freshness, and portfolio context;
- [ ] “Why am I seeing this?” is deterministic and auditable;
- [ ] daily decision support can prioritize attention without generating automatic buy/sell verdicts;
- [ ] AI answers are evidence-grounded and consistent with stored prediction/opportunity records;
- [ ] execution remains optional, disabled by default, and isolated;
- [ ] Data Health makes stale/broken inputs visible;
- [ ] backups are restore-tested;
- [ ] docs explain methodologies and source limitations.

---

# 49. Source/research notes used for this implementation plan

Current public documentation checked during planning included:

- NSE All Reports — UDiFF EOD, delivery, short-selling and market reports:  
  https://www.nseindia.com/all-reports
- NSE F&O reports — UDiFF F&O, OI, participant data and derivatives statistics:  
  https://www.nseindia.com/all-reports-derivatives
- NSE corporate filing dashboard, financial results, corporate actions and shareholding pattern:  
  https://www.nseindia.com/companies-listing/corporate-filings-application  
  https://www.nseindia.com/companies-listing/corporate-filings-financial-results  
  https://www.nseindia.com/companies-listing/corporate-filings-actions  
  https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern
- NSE market timings and holidays:  
  https://www.nseindia.com/resources/exchange-communication-holidays
- NSE individual-security derivatives contract information:  
  https://www.nseindia.com/static/products-services/equity-derivatives-individual-securities
- NSE data policy / historical and realtime products:  
  https://www.nseindia.com/static/market-data/nse-data-policy  
  https://www.nseindia.com/static/market-data/eod-historical-data-subscription  
  https://www.nseindia.com/static/market-data/real-time-data-subscription
- Zerodha Kite Connect instruments/history:  
  https://kite.trade/docs/connect/v3/market-quotes/  
  https://kite.trade/docs/connect/v3/historical/
- Upstox instrument and historical-data documentation:  
  https://upstox.com/developer/api-documentation/instruments/  
  https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/
- DhanHQ historical/market-quote documentation:  
  https://dhanhq.co/docs/v2/historical-data/  
  https://dhanhq.co/docs/v2/market-quote/
- OpenBB provider standardization patterns:  
  https://docs.openbb.co/odp/python/developer/standardization
- QuantConnect Algorithm Framework separation:  
  https://www.quantconnect.com/docs/v1/algorithm-framework/overview
- Microsoft Qlib workflow concepts:  
  https://github.com/microsoft/qlib
- NSE implementation standards for retail algorithmic trading API access:  
  https://nsearchives.nseindia.com/content/circulars/INVG67858.pdf

These links document capabilities and design constraints; they are not permission to redistribute data. Provider terms/licensing must be reviewed before any public deployment or resale.

---

# 50. Final implementation recommendation

The most important decision is **what not to do next**.

Do not immediately add:
- fundamentals dashboard;
- 20 screeners;
- broker trading;
- AI;
- more option models.

The highest-return path is:

```text
FIX CURRENT ECONOMIC CORRECTNESS
        ↓
BUILD CANONICAL INDIA DATA FOUNDATION
        ↓
BUILD TRUSTWORTHY EQUITY RESEARCH
        ↓
ADD PERSONAL RESEARCH + PORTFOLIO
        ↓
BUILD POINT-IN-TIME BACKTESTING
        ↓
INTEGRATE DERIVATIVES
        ↓
BUILD LEAKAGE-SAFE ML RESEARCH
        ↓
PROMOTE ONLY VALIDATED MODELS TO AUDITABLE FORECASTS
        ↓
ADD EXPLAINABLE OPPORTUNITY / DECISION SUPPORT
        ↓
ADD EVIDENCE-GROUNDED AI
        ↓
KEEP EXECUTION OPTIONAL AND ISOLATED
```

That order is what changes the codebase from a portfolio project into a system you can seriously rely on. The prediction/suggestion layer is deliberately late because its credibility depends on everything before it: trustworthy point-in-time data, correct accounting, realistic backtests, and permanent evaluation of what the models actually said.
