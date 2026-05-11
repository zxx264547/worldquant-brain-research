---
name: current_status_20260430_final
description: Final status - Best Sharpe=1.17, settings optimization doesn't improve
type: project
---

# Alpha Research Status - 2026-04-30 17:45 UTC

## Current Best
- **Sharpe: 1.17** (35% below target of 1.58)
- **Expression**: `ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)`
- **Fitness**: 2.06, **Turnover**: 0.0061, **Margin**: 0.126

## Key Findings from Today's Exploration

### Operators That TIMEOUT
- `ts_zscore(actual_eps_value_quarterly, 22)` - TIMEOUT
- `ts_zscore(bookvalue_ps, 22)` - TIMEOUT
- `ts_corr(rank(actual_eps_value_quarterly), rank(returns), 22)` - TIMEOUT
- `ts_corr(rank(actual_eps_value_quarterly), rank(returns), 66)` - TIMEOUT
- `ts_sum(bookvalue_ps, 252)` - TIMEOUT
- `ts_sum(cashflow, 252)` - TIMEOUT

### ts_corr Results (when they complete)
- ts_corr(eps, returns, 22): Sharpe=0.63, Fitness=0.19, Margin=0.0002, TO=0.48 (HIGH turnover!)
- ts_corr(eps, returns, 66): Sharpe=0.12 (very low)

### fundamental6 Fields
- `rank(bookvalue_ps)`: Sharpe=0.67
- `rank(cashflow)`: NOT TESTED (timeout issues)
- Best fundamental6 expression: 0.42 (lower than eps)

### Settings Variations (from simple_settings_test)
- decay 0-5: all give Sharpe=1.14 (with trunc=0.08)
- trunc=0.01: Sharpe=0.95
- trunc=0.05: Sharpe=1.09
- Combined: NOT YET COMPLETE

### Fields Tested (Sharpe)
1. actual_eps_value_quarterly: **1.17** (best)
2. actual_dividend_value_quarterly: 0.77
3. actual_cashflow_per_share_value_quarterly: 0.69
4. actual_sales_value_quarterly: 0.69
5. bookvalue_ps (fundamental6): 0.42

## Key Insight
The OB53521 approach (single field, ts_sum, signed_power, ts_backfill) has reached its ceiling at ~1.17 Sharpe. The ceiling appears to be fundamental - different settings give similar results around 1.14-1.17.

## Gap to Target
- Current: 1.17, Target: 1.58
- Gap: 35% improvement needed
- This requires a fundamentally different approach, NOT just settings tuning

## What DOES NOT Work
1. ts_zscore on fundamental fields - TIMEOUT
2. ts_corr with fundamentals - TIMEOUT or LOW Sharpe with HIGH turnover
3. Multi-field combinations - Sharpe <= 0.76
4. fundamental6 fields (bookvalue_ps, cashflow) - lower Sharpe
5. Settings variations (decay, truncation) - no significant improvement

## What MIGHT Work (Not Fully Tested)
1. Different operator combinations: ts_arg_max, ts_arg_min, ts_product
2. Different data fields (analyst4 has many more fields)
3. Different regions (EUR, CHN, JPN)
4. Neural/AI-based combinations

## Current Status
- Exploration scripts running but showing limited promise
- Settings optimization shows 1.14-1.17 range
- The 1.17 might be the practical ceiling for this expression pattern