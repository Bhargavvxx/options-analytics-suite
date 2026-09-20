# Indian Market Platform — Codex Instructions

## Project mission

This repository is being transformed from `options-analytics-suite`
into a serious personal India-first market research, portfolio intelligence,
systematic research, prediction, decision-support, and derivatives analytics platform.

This is not a demo project.

Correctness, provenance, reproducibility, point-in-time safety,
accounting integrity, explainability, and maintainability take priority
over feature count or impressive-looking output.

---

## Authoritative specifications

Before substantial planning or implementation, read:

1. `docs/planning/INDIAN_MARKET_PLATFORM_ARCHITECTURE.md`
2. `docs/planning/INDIAN_MARKET_PLATFORM_IMPLEMENTATION_PLAN.md`

These documents define the target architecture and migration sequence.

Do not silently redesign the platform away from them.

If implementation evidence reveals a genuine architectural problem,
document:

- the conflict;
- evidence;
- affected acceptance criteria;
- proposed correction.

Do not begin another broad redesign merely because another architecture
appears cleaner.

---

## Migration philosophy

This is an incremental migration of the existing repository.

It is NOT a big-bang rewrite.

Preserve tested quantitative functionality where appropriate.

Do not create every target directory immediately.

Only implement packages required by the active phase.

Keep the repository runnable.

Prefer small, reviewable changes.

---

## Phase discipline

Follow the implementation plan in order.

Do not jump ahead to:

- sophisticated ML;
- stock prediction;
- opportunity ranking;
- AI assistant;
- automated execution;
- new option models;
- large dashboards;

before their prerequisites and acceptance gates are verified.

A later feature does not justify bypassing an earlier correctness gate.

---

## Git safety

Before modifying files:

1. inspect `git status`;
2. inspect current branch;
3. inspect current HEAD;
4. preserve unrelated user changes.

Never overwrite unrelated work.

Do not rewrite Git history.

Prefer one logical concept per commit.

Before declaring work complete:

- inspect the diff;
- run relevant tests;
- inspect git status;
- report remaining issues.

---

## Correctness requirements

Never knowingly introduce:

- look-ahead bias;
- survivorship bias;
- future/unpublished fundamental data in historical research;
- present-day index constituents in historical backtests;
- silent use of revised data before its revision date;
- cash being treated as portfolio NAV;
- incorrect derivative expiry lifecycle;
- silent data-provider substitution;
- silent model fallback;
- synthetic option history represented as real observed history;
- future labels leaking into model training;
- historical fees calculated using current rates without effective dating;
- destructive replacement of raw source evidence.

---

## Data architecture

Use:

RAW
-> NORMALIZED
-> CURATED
-> ANALYTICS

Raw source artifacts must remain immutable.

Important records should preserve provenance such as:

- provider;
- dataset;
- ingestion run;
- retrieved timestamp;
- event/effective timestamp;
- published timestamp;
- revision timestamp;
- parser/schema version;
- quality status;
- source artifact/hash.

Derived analytics must not overwrite source facts.

---

## Instrument identity

Provider/exchange/broker IDs are aliases.

The platform owns a stable canonical `instrument_id`.

Symbols and tokens may change.

Derivative contracts must reference canonical underlyings.

Historical aliases require validity intervals.

---

## India-first defaults

Default context is India and NSE.

Use:

- INR;
- Asia/Kolkata for presentation;
- NSE calendars;
- Indian corporate actions;
- India-specific derivative contracts;
- historically versioned Indian fee schedules;
- Indian rate sources where applicable.

Remove inappropriate US-centric assumptions during their designated migration phase.

---

## Point-in-time safety

Historical research must only see information available at that point in time.

Important rules include:

- listing date <= as_of;
- universe membership valid at as_of;
- published_at <= as_of;
- revision visible only after revision_at;
- future market data unavailable;
- feature windows use past information only;
- label horizons must not leak across training boundaries.

Backtest and research APIs should prevent callers from bypassing
point-in-time rules.

---

## Portfolio accounting

Portfolio accounting is ledger-based.

The required invariant is:

NAV = cash + market value of positions + receivables - liabilities

Signals must not directly mutate cash.

Corporate actions must produce explicit economic effects.

Portfolio accounting must reconcile.

---

## Backtesting

Separate:

- universe selection;
- signal/strategy;
- portfolio construction;
- risk;
- execution;
- fees/slippage;
- ledger/accounting;
- metrics.

Backtests must record:

- data versions;
- code commit;
- configuration;
- execution mode;
- fee schedule;
- warnings;
- bias controls.

Do not describe synthetic option simulations as historical option backtests.

---

## Prediction and forecasting

Prediction is not equivalent to recommendation.

Future production prediction capabilities may include:

- direction probabilities;
- return distributions;
- volatility forecasts;
- downside/drawdown probabilities;
- benchmark-relative outperformance probability;
- sector-relative outperformance probability;
- market/regime forecasts.

Every production prediction must be:

- timestamped;
- immutable after issuance;
- associated with model version;
- associated with feature/data versions;
- associated with forecast horizon;
- evaluated after maturity;
- benchmarked;
- calibrated where probabilistic.

The prediction system must support abstention:

`NO_RELIABLE_SIGNAL`

Never force a forecast when confidence or data quality is inadequate.

---

## Opportunity and decision support

Opportunity detection is an attention-management layer.

It is not an automatic stock picker.

Possible states include:

- MONITOR
- RESEARCH
- HIGH_INTEREST_RESEARCH
- RISK_WARNING
- THESIS_CHECK_REQUIRED
- NO_RELIABLE_SIGNAL

Whenever something is surfaced, the user must be able to inspect:

- why it appeared;
- supporting evidence;
- opposing evidence;
- important risks;
- model confidence;
- relevant forecast;
- data freshness;
- source/provenance.

Do not convert an opaque score into unsupported BUY/SELL instructions.

---

## ML

ML work must be:

- point-in-time;
- leakage safe;
- reproducible;
- benchmarked;
- evaluated using proper time-series methodology.

Do not select the best model using the final test set.

Use validation or walk-forward evaluation.

Keep final holdout untouched until final evaluation.

Requested model and actual implementation must match.

Never silently replace one model with another while keeping the original label.

---

## AI assistant

The AI assistant is evidence-grounded.

Deterministic tools/services should calculate:

- financial ratios;
- market returns;
- portfolio metrics;
- screens;
- backtest metrics;
- prediction statistics.

LLM responsibilities include:

- summarize;
- compare;
- explain;
- synthesize.

Material claims should be traceable to evidence.

If evidence is insufficient, say so.

Do not fabricate company facts.

---

## Testing

Test count alone is not sufficient.

Prioritize:

- economic invariants;
- temporal invariants;
- point-in-time leakage tests;
- accounting reconciliation;
- corporate actions;
- provider data-contract tests;
- prediction calibration/evaluation;
- reproducibility.

Do not weaken a correct test merely to make implementation pass.

Run relevant tests after modifications.

Before completing a phase/unit, run the complete required gate.

---

## Phase completion

Code existing does not mean a phase is complete.

Every phase/unit should finish with the completion-report structure
defined in the implementation plan.

Final status must be exactly one of:

`VERIFIED`

or

`NOT YET VERIFIED`

Never mark `VERIFIED` if an acceptance gate has not passed.

---

## Security

Never commit:

- API keys;
- broker credentials;
- access tokens;
- session tokens;
- `.env`;
- private secrets.

Never expose secrets in logs.

Broker execution remains disabled by default.

Live execution belongs only to the explicit execution phase.
