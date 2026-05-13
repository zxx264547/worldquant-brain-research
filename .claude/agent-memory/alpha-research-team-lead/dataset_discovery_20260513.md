---
name: dataset_discovery_20260513
description: Complete BRAIN API dataset scan discovery - 343 datasets found, 30+ untested with VECTOR fields
type: reference
---

# Complete Dataset Discovery — 2026-05-13

## Discovery Method
BRAIN API `/data-sets` endpoint without instrumentType filter returned 5196 records (343 unique named datasets). Cross-referenced with all previously tested datasets.

## Previously Tested Datasets
risk60, analyst4, analyst10, analyst14, analyst27, fundamental6, pv87, pv1, pv13, news12, sentiment21, wds, analyst11, analyst12, analyst15, analyst16, analyst35, analyst39

## VECTOR Datasets Discovered (Untested)

### shortinterest3 (Securities Lending Files Data) — **TOP PRIORITY**
- 31 VECTOR fields, ALL coverage=1.0
- 29 fields have alphaCount=0, userCount=0
- Same domain as risk60 (securities lending) but different data source
- Key fields: `max_loan_rate`, `min_loan_rate`, `mean_loan_rate`, `borrow_activity_score`, `loan_utilization_ratio`, `loan_rate_volatility`, `available_market_value_usd`, `available_share_count`
- Two fields are already heavily used: `shrt3_bar` (alphaCount=1802), `shrt3_utilizationpercent_units` (alphaCount=812)
- **The 29 unused fields are the target — zero competition = low ProdCorr**

### biasfree_analyst (Bias Adjusted Analyst Forecasts)
- VECTOR fields: `biasfree_analyst_price_target` (cov=0.885, users=0, alphaCount=0), `biasfree_analyst_fundamental_estimate` (used by 1)
- Also: `first/second_biasfree_price_target_analogue`, `forecast_horizon_months`
- **`biasfree_analyst_price_target` is completely unused — target price via vec_max**

### analyst44 (Integrated Broker Estimates)
- VECTOR fields with prefix `anl44_2_`: `eps_value` (cov=0.9577, users=1), `ebit_value` (cov=0.9402, users=2), `bps_value` (cov=0.7856, users=22), `ebitda_value`, `cfps_value`, etc.
- These are event-level estimates; vec_max aggregates across brokers

### analyst45 (Analyst Trade Ideas)
- 50 VECTOR fields: idea returns, benchmark returns, analyst performance metrics
- Coverage 0.2-0.66 (lower than ideal)
- `analyst45_daily_index_relative_return` (cov=0.54), `analyst45_weighted_average_return` (cov=0.66)

### option4 (Implied Volatility and Pricing for Equity Options)
- 10 VECTOR fields but most have coverage=0.0

### analyst55 (Earning Quality Analyst Estimates)
- VECTOR fields for EPS estimates (mean, median, high, low) but coverage=0.0

## Other Noteworthy Untested Datasets (MATRIX)
- analyst47: Composite alpha indicator (6 MATRIX fields, cov=0.66, pre-built alpha signal!)
- analyst82: ML-predicted EBITDA/EPS values (MATRIX, cov=0.5-1.0)
- analyst69: Fundamental Analyst Estimates (MATRIX EPS, cov=1.0)
- short_interest_pred: Short Interest Forecast Signals (10 MATRIX)
- order_flow_imb: Institutional Order Flow Imbalance (50 MATRIX)
- social_sent_score: Equity Social Sentiment Scores
- search_interest: Rapid Search Interest Signals
- news_transformer_scores: Transformer-Based News Sentiment Scores
