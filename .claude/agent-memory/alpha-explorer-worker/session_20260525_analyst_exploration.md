---
name: session_20260525_analyst_exploration
description: 2026-05-25 analyst dataset VECTOR field exploration - all fail, NONE neutralization baseline Sharpe 0.67
metadata:
  type: session
---

# Session 2026-05-25: Analyst Dataset VECTOR Field Exploration

## Summary
- Tested analyst VECTOR datasets (analyst4, 10, 14, 27, biasfree_analyst) with vec_max patterns
- All complex expressions (with zscore/ts_max) failed with negative Sharpe
- Simple rank(vec_max(field)) has very high turnover (>1.5) making it unusable
- Best result: `rank(close)` with NONE neutralization Sharpe 0.67, Fitness 0.93
- SECTOR neutralization causes simulations to hang at 35% (API bug)
- NONE/INDUSTRY/MARKET neutralization works, SECTOR stuck

## Completed Alphas (2026-05-25)

| Alpha ID | Expression | Neutralization | Sharpe | Fitness | Turnover |
|----------|------------|----------------|--------|---------|----------|
| gJxRLQ3g | rank(close) | NONE | 0.67 | 0.93 | 0.01 |
| qMnGae8A | rank(close) | NONE | 0.67 | 0.93 | 0.01 |
| ZYr2VKgQ | rank(close) | MARKET | 0.20 | 0.09 | 0.02 |
| RRd2vmwd | rank(close) | INDUSTRY | 0.18 | 0.07 | 0.02 |
| pw8Vkkp6 | rank(close) | SECTOR | 0.18 | 0.08 | 0.02 |
| MPkKzgOr | rank(close) | SECTOR | 0.18 | 0.08 | 0.02 |
| kqQ1YXMd | rank(vec_max(anl4_adxqfv110_high)) | SECTOR | 0.26 | 0.03 | 1.59 |
| Xg12ejKa | close | NONE | 0.12 | 0.04 | 0.01 |
| YPQ2v6wv | zscore(-ts_max(vec_max(anl4_adxqfv110_high), 22)) | SECTOR | -0.12 | -0.03 | 0.06 |
| Jjbg8LEn | zscore(-ts_max(vec_max(anl4_ady_high), 66)) | SECTOR | -0.23 | -0.11 | 0.01 |

## VECTOR Field Patterns Tested (All Failed)

| Dataset | Field | Pattern | Sharpe | Issue |
|---------|-------|---------|--------|-------|
| analyst4 | anl4_adxqfv110_high | zscore(-ts_max(vec_max(...),22)) | -0.12 | Negative |
| analyst4 | anl4_ady_high | zscore(-ts_max(vec_max(...),66)) | -0.23 | Negative |
| analyst4 | anl4_adxqfv110_high | rank(vec_max(...)) | 0.26 | Turnover 1.59 |

## API Issues
1. **Simulation Polling Bug**: platform_functions._poll_for_completion broken
   - Uses `progress >= 1.0` which never triggers
   - Correct way: `progress is None` = COMPLETE
2. **SECTOR Neutralization Stuck**: Simulations with SECTOR neutralization stuck at 35%
   - Works for NONE, INDUSTRY, MARKET
   - Only SECTOR causes hang
3. **Key Finding**: NONE neutralization gives best Sharpe (0.67) but may fail submission checks

## Field Discovery
- analyst4: 24 VECTOR fields (adxqfv110_*, ady_*, ads1detailafv110_*)
- analyst10: No VECTOR fields with predictive signal
- analyst14: 16 VECTOR fields (estvalue related)
- analyst27: 50 VECTOR fields (analyst accuracy/consistency metrics)
- biasfree_analyst: 8 VECTOR fields (fundmental_estimate, price_target)

## CRITICAL API ISSUE - BLOCKED (2026-05-26 02:30)

ALL simulations with complex expressions stuck at 35% progress:
- `rank(close)` with ANY neutralization: stuck at 35%
- `zscore(-ts_max(vec_max(rsk60_offer), 22))`: stuck at 35%
- `rank(vec_max(...))` for analyst fields: stuck at 35%
- CLI backtest ALSO stuck at 35%

This confirms the API itself has a systemic issue. Not neutralization-specific.

### Symptoms
- POST /simulations returns 201 (success)
- GET /simulations/{id} returns progress=0.35 forever
- No alpha ID ever returned
- Works for some simple expressions but NOT for complex ones

### API Status: NOT FUNCTIONING
Cannot complete any meaningful backtests.

## Recommendations for Next Session
1. **Wait for API recovery** - This is a server-side issue
2. **Try EUR region** - May have different API behavior
3. **Check with WorldQuant support** - If issue persists
4. **Simple expressions MAY work** - rank(close) completed with NONE in early tests

## Submission Check Results (rank(close) NONE)
- Sharpe 0.67 < 1.58 required - NEED HIGHER SHARPE
- Fitness 0.93 < 1.0 required - NEED HIGHER FITNESS
- Even if completed, this alpha would fail submission

## Key Learning
- Simple expressions (rank(close)) work and complete
- Complex expressions (with VECTOR fields, zscore, ts_max) all stuck at 35%
- Need either API fix or simpler expression patterns

## Files
- /tmp/all_analyst_results.json - All collected results
- /tmp/session_test.json - Session data for API calls
- /tmp/fixed_batch_runner.py - Working batch runner with requests polling