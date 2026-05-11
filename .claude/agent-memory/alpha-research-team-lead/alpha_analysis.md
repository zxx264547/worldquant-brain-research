---
name: alpha_analysis
description: Analysis of existing alphas and what patterns work
type: reference
---

# Alpha Analysis

## Existing Alpha Portfolio
- **Total Alphas**: ~100 in account
- **Submittable (Sharpe >= 1.58)**: 0
- **Near-miss (4/5 criteria)**: ~44 alphas

## Best Performing Alphas
| Alpha ID | Sharpe | Fitness | PPC | Expression |
|----------|--------|---------|-----|------------|
| 1YnKL2OM | 1.02 | 1.43 | 0.16 | ts_mean(winsorize(actual_eps_value_quarterly), 25) |
| RRkznAPe | 1.02 | 1.43 | 0.16 | ts_mean(winsorize(actual_eps_value_quarterly), 25) |
| wpJkobE1 | 0.85 | 1.18 | 0.15 | signed_power(ts_mean(winsorize(actual_eps_value_quarterly), 25), 1.3) |

## Common Patterns
1. **Most common base**: `ts_mean(winsorize(actual_eps_value_quarterly), 25)`
2. **Window sizes tested**: 5, 10, 15, 20, 22, 24, 25, 27, 31, 35, 66
3. **Power values for signed_power**: 1.3, 1.5, 2.0
4. **Combinations**: eps + dividend expressions

## What's NOT Working
- All alphas stuck at Sharpe ~0.5-1.04
- Need Sharpe >= 1.58 (52% gap from 1.04)
- Simple 1-op expressions not sufficient
- Sales/cashflow/dividend fields underperform EPS significantly

## Current Best (2026-04-25)
- ts_sum(winsorize(actual_eps_value_quarterly), 25) / 25: Sharpe=1.04
- EPS variations (windows 5-30): Sharpe 1.01-1.04
- Sales variations: Sharpe ~0.74
- Cashflow variations: Sharpe ~0.75-0.81
- Dividend variations: Sharpe ~0.80

## What Needs to Be Tried
1. More complex 2-op+ nested operations
2. Different field combinations (not just eps/dividend)
3. Different operators: ts_rank, ts_delta, zscore combinations
4. Industry neutralization
5. Different universe or region settings

## How to Apply
- The simple ts_mean(eps) pattern has been thoroughly explored - need fundamentally different approach
- Consider GroupExplore agent for deep optimization of promising alpha patterns
- Look for alpha variants that combine ts_rank with ts_delta for non-linear effects
