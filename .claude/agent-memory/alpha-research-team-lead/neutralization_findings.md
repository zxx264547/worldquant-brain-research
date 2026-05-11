---
name: neutralization_findings
description: Valid neutralization options and market data field performance
type: reference
---

# Neutralization & Field Findings

## Valid Neutralization Options
NONE of these work - all return "not a valid choice":
- "market" - INVALID
- "sector" - INVALID
- "crowding" - INVALID
- "industry" - INVALID

The only valid neutralization appears to be "NONE" or possibly "auto" (need verification).

## Market Data Field Performance
- rank_close_25: Sharpe=0.68 (MUCH WORSE than EPS-based 1.04)
- rank_vwap_25: timed out after 600s

## Implication
Without valid neutralization options, we cannot apply the optimization matrix strategies that depend on neutralization.

## Current Best Alpha
ts_sum(winsorize(actual_eps_value_quarterly), 25)/25:
- Sharpe=1.04, Fitness=1.47, PPC=0.17, Margin=0.043, Turnover=0.012

## Gap to Target
- Need: Sharpe >= 1.58
- Current: 1.04
- Gap: 52%

## What This Means
- Can't improve via neutralization strategies
- Need to find different field or expression structure
- Market data fields (close, vwap) significantly underperform fundamental data (eps)