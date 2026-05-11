---
name: alpha_research_progress_20260426
description: Current alpha research status and best performing expressions
type: project
---

# Alpha Research Status (2026-04-26)

## Current Best Alpha
- **Expression**: `ts_mean(actual_eps_value_quarterly, 22)`
- **Sharpe**: 0.91
- **Fitness**: 1.43
- **Margin**: 0.054216
- **Turnover**: 0.0114
- **Target**: 1.58 (gap: 0.67)

## Best Performing Fields (analyst4 dataset)
| Field | Best Sharpe | Notes |
|-------|-------------|-------|
| actual_eps_value_quarterly | 0.91 | Window 22 optimal |
| actual_dividend_value_quarterly | 0.86 | Window 22 |
| actual_cashflow_per_share_value_quarterly | 0.74 | Window 22 |
| actual_sales_value_quarterly | 0.67 | Window 22 |

## Key Insights
- EPS field has a ceiling around 0.91 Sharpe
- Window 22 works best for most quarterly fields
- ts_backfill with 5-day offset often improves
- Combination fields (EPS + Sales, EPS + Dividend) can help
- Simple ts_mean expressions work better than complex nested ones

## Ideas Generated
- **Batch 6001-6024**: 24 new 2-op+ nested expressions
- Focus: ts_rank, ts_delta, ts_backfill combinations
- Windows: 5, 22, 66
- Fields: EPS, Sales, Cashflow, Dividend
- Expressions include:
  - ts_rank(ts_delta(field, 5), 22)
  - rank(ts_delta(field, 22))
  - ts_backfill(ts_delta(field, 22), 5)
  - ts_delta(ts_mean(field, 22), 5)
  - rank(field) - rank(field) combinations
  - ts_mean(ts_delta(field, 5), 22)

## Failed Directions
- mdl136 fields: API timeout or "unknown variable" errors
- Fields with _1 suffix rejected by BRAIN API
- Complex nesting doesn't always improve over simple ts_mean

## Next Steps to Reach 1.58
1. Try combination of best fields (EPS + Cashflow)
2. Explore analyst10 dataset fields
3. Try market-neutral/neutralization approaches
4. Investigate different universe constraints
5. Focus on simpler expressions that avoid overfitting
