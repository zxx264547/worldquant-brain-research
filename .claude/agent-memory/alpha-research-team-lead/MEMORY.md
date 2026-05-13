# Alpha Research Team Lead - Memory Index

## Project Context
- [user_role.md](user_role.md) - User role and goals for alpha research
- [alpha_research_status_20260501.md](alpha_research_status_20260501.md) - Previous ceiling analysis (2026-05-01)
- [alpha_research_status_20260512.md](alpha_research_status_20260512.md) - Updated status after 2026-05-13 testing -- ALL directions exhausted

## Current Status (2026-05-13)
- **Best Sharpe: 1.17** (STRUCTURAL CEILING - 240+ tests, ALL data sources confirmed max)
- Best expression: `ts_backfill(ts_sum(actual_eps_value_quarterly, 252), 3)` (without signed_power)
- No submittable alphas (target 1.58)
- confirmed: delay=0/1 same, signed_power adds nothing, INDUSTRY neut destroys price

## Full Exhausted List (2026-05-13 Final)
1. EPS analyst4: 1.17 ceiling across all windows/settings/operators
2. Price signals: 0.85 ceiling (close ts_sum), neut INDUSTRY kills to 0.23-0.27
3. INDUSTRY neutralization: destroys ALL price signals (corr goes -1.03)
4. delay=0: same as delay=1 for EPS (1.17)
5. News12: dividend_yield 0.77, eod_close 0.68, atr14 0.55 -- no breakthrough
6. analyst4 non-EPS: dividend_252 0.84, sales 0.69, cashflow 0.52
7. fundamental6: 0.67-0.71 (limited by 0.5 coverage)
8. pv87 BPS: 0.67-0.70
9. sentiment21: 0.56
10. ts_rank/group_rank: 0.65-0.68
11. ts_delta momentum: 0.52-0.66
12. Composite signals: 0.62-0.69
13. Return momentum (66d): -0.60 (mean reversion)
14. Low volatility: 0.73 (decent but not breakthrough)

## Untested Promising Avenues
1. analyst10 dataset (weighted analyst estimates - might outperform analyst4)
2. Multi-region (EUR/ASI with analyst4 data)
3. Need to discover new data sources
