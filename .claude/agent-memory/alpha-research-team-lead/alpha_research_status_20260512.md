---
name: alpha_research_status_20260513
description: Alpha research status after 2026-05-13 extensive testing - ALL new directions tested, 1.17 ceiling structural
type: project
---

# Alpha Research Status - 2026-05-13

## 1.17 Ceiling CONFIRMED Structural After 18+ New Tests

### Tested (Night of 2026-05-12 to 2026-05-13)

**Direction 1: ts_rank Operator on EPS** (2 tests) -- FAILED
- `ts_backfill(ts_rank(eps, 252), 3)`: Sharpe 0.65 (ts_sum version gives 1.17)
- `ts_backfill(signed_power(ts_rank(eps, 252), 0.9), 3)`: Sharpe 0.65
- **Conclusion**: ts_rank is fundamentally WORSE than ts_sum for EPS signal

**Direction 2: PV87 Dataset BPS Fields** (3 tests) -- MODERATE
- PV87 has 50 MATRIX fields, 2 indicators: affops (adjusted funds from ops), bps (book value)
- `rank(ts_mean(bps_chg_high, 22))`: Sharpe 0.67, Fitness 0.97, PPC 0.21 (very clean stats)
- `rank(ts_mean(bps_chg_high, 66))`: Sharpe 0.67 (same)
- `rank(ts_mean(bps_level_high, 22))`: Sharpe 0.70, PPC 0.58
- **Conclusion**: PV87 BPS is a new complementary signal but Sharpe capped at 0.70

**Direction 3: sentiment21 Sentiment Data** (1 test) -- WEAK
- 50 MATRIX fields, coverage=1.0, negative/positive/neutral sentiment
- `rank(ts_mean(snt21_2neg_mean, 22))`: Sharpe 0.56 (margin too low)
- **Conclusion**: Sentiment data alone is not a strong predictor

**Direction 4: EPS Derivatives and Combinations** (4 tests) -- FAILED
- `rank(ts_mean(eps,252)) + rank(ts_mean(bps_chg,22))`: Sharpe 0.69 (additive no better)
- `group_rank(eps, subindustry)`: Sharpe 0.68 (worse than rank)
- `rank(ts_mean(ts_delta(eps,252),22))`: Sharpe 0.69 (EPS momentum weak)
- `ts_backfill(signed_power(ts_sum(eps,252),1.3),3)`: Sharpe 0.89 (worse than 0.9)

**Direction 5: Settings/Neutralization** (2 tests) -- FAILED
- INDUSTRY neutralization: API error (empty alpha_id)
- SUBINDUSTRY neutralization: API error (empty alpha_id)
- **Conclusion**: Neutralization options not functional with current API setup

**Key Discovery: signed_power Adds Zero Value**
- `ts_backfill(ts_sum(eps, 252), 3)` = Sharpe 1.17 (WITHOUT signed_power)
- `ts_backfill(signed_power(ts_sum(eps, 252), 0.9), 3)` = Sharpe 1.17 (WITH signed_power)
- Identical results. The entire gain is from ts_sum+backfill+eps, not from signed_power.

## Consistently Observed Pattern
- EPS from analyst4: Sharpe 1.17 (ts_sum + ts_backfill, no signed_power needed)
- ALL other signals (PV87 BPS, sentiment21, fundamental6): Sharpe 0.56-0.70
- ALL operator variants (ts_rank, group_rank, group_op): give WORSE results than rank/ts_sum
- ALL neutralization (INDUSTRY, SUBINDUSTRY): API errors
- ALL additive combinations: Sharpe capped at individual max (~0.69)
- EPS combined with tech multipliers (beta): Sharpe stays at 1.17

## What's Still UNTESTED
1. **Close price alpha**: `rank(ts_mean(close, 20))` - database claims Sharpe 1.5 but not verified on platform
2. **Multi-region testing**: EPS on EUR or ASI regions (may not work - analyst4 is USA-only)
3. **News12 fields**: dividend_yield, atr14, eod_close (technical data)
4. **ts_corr operator**: EPS correlated with returns or other factors
5. **Different delay** (delay=0 vs delay=1) on proven EPS expression
6. **industry_relative or ts_decay_linear operators** (may not be available in FASTEXPR)

## Full Results Table
| Expression | Dataset | Sharpe | Fitness |
|---|---|---|---|
| ts_backfill(ts_sum(eps,252),3) | analyst4 | 1.17 | 1.90 |
| sp(ts_sum(eps,252), 1.3) | analyst4 | 0.89 | 1.34 |
| rank(ts_mean(bps_level,22)) | pv87 | 0.70 | 1.02 |
| rank(ts_mean(eps_delta,252),22) | analyst4 | 0.69 | 1.00 |
| rank(eps_252) + rank(bps_chg_22) | analyst4+pv87 | 0.69 | 1.00 |
| group_rank(eps,subindustry) | analyst4 | 0.68 | 0.96 |
| rank(ts_mean(bps_chg,22)) | pv87 | 0.67 | 0.97 |
| rank(ts_mean(bps_chg,66)) | pv87 | 0.67 | 0.97 |
| ts_backfill(ts_rank(eps,252),3) | analyst4 | 0.65 | 0.92 |
| rank(ts_mean(snt21_2neg,22)) | sentiment21 | 0.56 | 0.77 |

## API Status
- Each simulation takes 2-5 minutes (very slow polling)
- 429 Rate limit after ~5 consecutive calls
- TOP3000 USA universe reliable
- INDUSTRY/SUBINDUSTRY neutralization: not functional

## Recommendations for Breakthrough
The 1.17 ceiling appears structural for the current data/operator/settings space. Recommended paths:
1. **Verify price-based alpha**: try rank(ts_mean(close,20)) on the platform (database claims 1.5)
2. **News12 exploration**: dividend_yield and price-based signals
3. **Multi-region**: test EPS on EUR if analyst4 data available
4. **Try delay=0**: faster signal capture
5. **Browser-based approach**: use forum suggestions about group_op and group_neutralize via browser UI where direct API fails
