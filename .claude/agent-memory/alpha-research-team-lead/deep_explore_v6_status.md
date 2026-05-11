---
name: deep_explore_v6_status
description: Status of deep exploration v6 with 8 variants testing
type: project
---

# Deep Exploration v6 Status

## Started: 2026-04-25 22:06 UTC
- Parent alpha: ts_sum(winsorize(actual_eps_value_quarterly), 25)/25 (Sharpe=1.04, Fitness=1.47)
- 8 variants being tested:
  1. signed_power_1.3 - COMPLETED: Sharpe=0.89 (WORSE)
  2. ts_rank_nested - TIMEOUT at 600s, retried
  3. double_smooth
  4. rank_wrapper
  5. industry_neutral
  6. decay_2
  7. golden_combo
  8. trunc_001

## Key Finding
- signed_power_1.3 HURT performance (0.89 vs 1.04 baseline)
- ts_rank nested also likely to hurt based on earlier ts_rank tests (0.62)
- API extremely slow - 600s timeouts frequent

## Current Best
- ts_sum(eps,25)/25: Sharpe=1.04 (unchanged since 2026-04-25)

## Gap to Target
- Need: Sharpe >= 1.58
- Current: 1.04
- Gap: 52%

## How to Apply
- signed_power 1.3 on ts_sum doesn't help - don't use it
- Need fundamentally different approach