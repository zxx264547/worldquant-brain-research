---
name: failed_strategies_2026
description: Document of all failed alpha strategies to avoid repeating
type: reference
---

# Failed Alpha Strategies (2026-04-25/26)

## Neutralization - ALL INVALID
- "industry" - INVALID
- "market" - INVALID
- "sector" - INVALID
- "crowding" - INVALID

## Expression Modifications - DON'T USE
- signed_power(eps_tsum, 1.3): Sharpe=0.89 (WORSE than baseline 1.04)
- ts_rank(ts_sum(eps), 22): timeout after 600s
- rank(ts_sum(eps)): rate limit exceeded
- ts_zscore(eps): Sharpe=0.56 (MUCH WORSE)

## Universe - DON'T USE
- TOP1500 with USA region: "not available for EQUITY"
- TOP500: Sharpe=0.85-0.87 (WORSE than TOP3000's 1.04)

## Market Data Fields - MUCH WORSE
- rank(close): Sharpe=0.68 (vs EPS's 1.04)
- rank(vwap): Sharpe=0.68
- rank(open): Sharpe=0.68

## Field Comparisons (all with ts_sum/winsorize)
- actual_eps_value_quarterly: Best at 1.04
- actual_cashflow_per_share: 0.81
- actual_dividend_value_quarterly: 0.83
- actual_sales_value_quarterly: 0.74

## What Works
- ts_sum(winsorize(actual_eps_value_quarterly), 25)/25: Sharpe=1.04, Fitness=1.47

## Gap to Target
- Sharpe 1.04 -> 1.58 (52% gap)

## What Needs to Work
Need new fundamentally different approach. Current single-field ts_sum variations exhausted.