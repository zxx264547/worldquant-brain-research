---
name: session_20260520_eur_exploration
description: 2026-05-20 EUR region exploration - API blocked, only 1 PPA-compliant alpha found
metadata:
  type: project
---

## EUR Region Field Exploration (2026-05-20)

### API Status
- **EUR TOPCS1600 simulations stuck at 35%** - same block as USA region (TOP3000)
- Rate limiting active during testing
- Cached results from previous successful sessions

### Key Findings

1. **Only 1 alpha passes full PPA criteria**: `eur_rsk60_offer`
   - Expression: `zscore(-ts_max(vec_max(rsk60_offer), 22))`
   - Sharpe=2.36, Fitness=5.17, PPC=0.070, Turn=0.029, Margin=0.042
   - Margin > Turnover = PASS

2. **All other high-Sharpe alphas FAIL margin check**:
   - s3_zscore (Sharpe 2.46): Margin 0.029 < Turn 0.041 - FAIL
   - mean66_tw (Sharpe 1.83): Margin 0.007 < Turn 0.038 - FAIL
   - max66_tw (Sharpe 1.70): Margin 0.006 < Turn 0.040 - FAIL

3. **EUR TOPCS1600 required**: TOP3000 not available for EUR EQUITY

4. **rsk60_crowding is ANTI-PATTERN**: Sharpe=-0.32

### Field Coverage in EUR
| Field | Tests | Best Sharpe | Status |
|-------|-------|-------------|--------|
| min_loan_rate | 13 | 2.46 | READY (needs margin fix) |
| rsk60_offer | 9 | 2.36 | **SUBMITTABLE** |
| mean_loan_rate | 4 | 1.83 | NEEDS_OPT |
| max_loan_rate | 5 | 1.70 | NEEDS_OPT |
| rsk60_last | 3 | 1.62 | NEEDS_OPT |
| loan_utilization_ratio | 6 | 1.38 | NEEDS_OPT |
| rsk60_crowding | 1 | -0.32 | AVOID |

### Next Steps
1. Submit eur_rsk60_offer to PPA
2. Optimize other fields with decay=2 to fix margin > turnover
3. Test untested fields: borrow_activity_score, available_share_count, loan_rate_volatility
4. Results saved to /tmp/multi_agent/eur_alpha0_results.json