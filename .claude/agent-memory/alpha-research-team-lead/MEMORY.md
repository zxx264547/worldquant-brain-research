# Alpha Research Team Lead - Memory Index

## Project Context
- [user_role.md](user_role.md) - User role and goals for alpha research
- [alpha_research_status_20260501.md](alpha_research_status_20260501.md) - Previous ceiling analysis (2026-05-01)
- [alpha_research_status_20260512.md](alpha_research_status_20260512.md) - Updated status after 2026-05-13 testing -- ALL directions exhausted
- [dataset_discovery_20260513.md](dataset_discovery_20260513.md) - Full dataset discovery via API (343 unique datasets found)

## Current Status (2026-05-13)
- **Best Sharpe: 1.17** (STRUCTURAL CEILING on analyst4 EPS - 208 tests)
- **Active Direction: VECTOR pattern on shortinterest3** -- 29 unused VECTOR fields, cov=1.0
- **Active Direction: VECTOR pattern on biasfree_analyst** -- VECTOR price target, cov=0.885, users=0
- No submittable alphas (target 1.58)

## Key Recent Discoveries
1. shortinterest3 has 31 VECTOR fields (29 with alphaCount=0). Same securities lending domain as risk60 but completely unused.
2. biasfree_analyst_price_target (VECTOR, cov=0.885, 0 users) - bias-adjusted target price estimates
3. analyst44 has anl44_2_eps_value etc. (VECTOR, cov 0.6-0.96, low users)
4. analyst45 has 50 VECTOR fields for trade ideas (coverage 0.2-0.66)

## Full Tested Data Source Ceilings
1. risk60: 2.37 (all ProdCorr rejected)
2. analyst4 EPS: 1.17
3. Price signals: 0.85
4. analyst10: 0.74
5. analyst14 VECTOR: 0.68
6. PV87 BPS: 0.70
7. news12: 0.77
8. fundamental6: 0.67-0.71
9. sentiment21: 0.56
10. analyst27 VECTOR: -0.1 (no signal)

## Active Testing
- shortinterest3 VECTOR batch (8 sims) - max_loan_rate, mean_loan_rate, etc.
- biasfree_analyst VECTOR batch (8 sims) - price_target, fundamental_estimate
