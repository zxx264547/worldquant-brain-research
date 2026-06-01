---
name: shrt3_bar_breakthrough_20260601
description: 2026-06-01 breakthrough with shrt3_bar - found Sharpe 1.72 but all fail PROD_CORRELATION
metadata:
  type: project
---

# 2026-06-01 shrt3_bar Exploration Session

## MAJOR FINDINGS

### Success: Found shrt3_bar (shortinterest3) as strong signal source
- `signed_power(zscore(-ts_min(vec_min(shrt3_bar), 66)), 3)` Sharpe **1.72** Fitness 2.58 (BEST)
- `signed_power(zscore(-ts_min(vec_min(shrt3_bar), 66)), 2.5)` Sharpe 1.67
- `signed_power(zscore(-ts_min(vec_min(shrt3_bar), 66)), 2)` Sharpe 1.61
- `signed_power(zscore(-ts_min(vec_min(shrt3_bar), 66)), 1.5)` Sharpe 1.49
- Many variations with different windows (22, 66, 120, 252): Sharpe 1.44-1.72

### Failure: ALL high-Sharpe shrt3_bar alphas FAIL PROD_CORRELATION
- 33 strong alphas (Sharpe >= 1.5) tested
- ALL have PROD_CORRELATION value 0.96-0.97 (limit 0.7) → FAIL
- SELF_CORRELATION passes (0.74)
- Correlated with "analyst4_usa_1step" and "fundamental6_usa_2step" production alphas

### Why: New datasets (analyst44, analyst4, biasfree_analyst) are too WEAK
- analyst44 eps_value: Sharpe 0.29-0.50
- analyst4 adxqfv110_mean: Sharpe -0.06 to 0.42
- biasfree_analyst fundamental_estimate: Sharpe -0.27 to 0.46
- These don't reach 1.58 threshold

### Effective Pattern
```
signed_power(zscore(-ts_min(vec_min(shrt3_bar), 66)), M)
where M = 1.5 to 3 (higher M = higher Sharpe)
```

### Why:** Exploit time dimension is critical
- `ts_min(vec_min, 22)`: 1.47
- `ts_min(vec_min, 66)`: 1.49-1.72 (sweet spot)
- `ts_min(vec_min, 120)`: 1.47
- `ts_min(vec_min, 252)`: 1.44

### Effective Pattern: SECTOR vs INDUSTRY neutralization
- shrt3_bar_decay SECTOR: 1.31 (better)
- shrt3_bar_decay INDUSTRY: 1.02

## NEXT STEPS

The PROD_CORRELATION is the blocker. To get submittable alphas:
1. Use truly different structures (group_*, winsorize, ts_backfill, quantile)
2. Try EUR/CHN region (different production pool)
3. Combine shrt3_bar with technical indicators (not just simple addition)
4. Try alpha_formulas from existing ACTIVE production alphas (group_zscore + ts_mean + winsorize + ts_backfill + vec_avg pattern)

## RELATED FILES
- /tmp/shrt3_v2.py: First batch with signed_power variants
- /tmp/shrt3_v3.py: Sector + windows
- /tmp/shrt3_v4.py: Other shrt3 VECTOR fields
- /tmp/shrt3_v5.py: Exponent variations
- /tmp/test_struct2.py: Pure different structures
- /tmp/test_group.py: group_*/winsorize patterns

## VECTOR Field Performance Summary (in test order)
- shrt3_bar (Borrow demand rating 1-10): Sharpe 1.47-1.72 **STRONG**
- borrow_activity_score: Sharpe 1.49 (similar to shrt3_bar)
- shrt3_utilizationpercent_units: Sharpe 1.00
- loaned_share_count: Sharpe 0.22 (WEAK)
- new_loaned_share_count: Sharpe 0.06 (WEAK)
- average_loan_duration_days: Sharpe 0.15 (WEAK)
