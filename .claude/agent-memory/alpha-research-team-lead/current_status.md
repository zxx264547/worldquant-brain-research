---
name: current_status_20260430
description: Current alpha research status - best Sharpe=1.17, need 1.58 to submit
type: project
---

# Alpha Research Status - 2026-04-30 01:15

## Current Best
- Alpha ID: A1g1Z1Vw
- Expression: `ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)`
- Sharpe: 1.17
- Fitness: 2.06
- Margin: 0.126, Turnover: 0.0061 (passes margin check)
- Gap to target: 0.41 (35% more needed)

## Problem
- Need Sharpe >= 1.58 to submit
- mdl136 field gave Sharpe 1.58-1.77 but:
  1. Fails margin check (margin=0.001 << turnover=0.06)
  2. Field now returns "unknown variable" error
- Standard eps approach has ceiling at ~1.17

## Forum Patterns (Untested)
1. `rank(A) + rank(B)` - mixed signals
2. `rank(A) * rank(B)` - multiplicative signals
3. `ts_decay_linear` - effective observation density
4. `scale` operator - +0.02 mentioned in forum
5. `truncation: 0.08` - weight concentration

## API Status
- Rate limited (429 errors)
- Simulations timing out (>180s)
- mdl136 field not available in TOP3000

## Ideas Queue
- 150 total ideas
- 122 untested
- Added 8 new forum-pattern ideas

## Next Steps
1. Wait for API to recover
2. Test forum patterns:
   - rank combination of eps + other fields
   - ts_decay_linear with signed_power
   - scale operator on best expression
3. Try to find alternative high-Sharpe field like mdl136
