# Alpha Research Team Lead - Memory Index

## Project Context
- [user_role.md](user_role.md) - User role and goals for alpha research
- [alpha_research_status_20260501.md](alpha_research_status_20260501.md) - Current status with 1.17 ceiling analysis

## Current Status (2026-05-01)
- **Best Sharpe: 1.17** (CEILING - not broken after 1566 results)
- Best expression: `ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)`
- 727 unique alphas tested, 27 with Sharpe > 1.17, 0 with Sharpe >= 1.5
- PV87 dataset discovered (6666 ESG fields) but testing problematic

## What's Been Exhausted
1. All EPS windows (5-504) - converge to 1.04-1.17
2. All analyst4 fields (eps, cashflow, dividend, revenue) - eps best
3. All operators (ts_sum, ts_mean, ts_rank, ts_delta, ts_decay_linear, ts_backfill, signed_power)
4. All neutralization options (INDUSTRY/MARKET/SECTOR/CROWDING return errors)
5. Multiple universes (TOP3000 best)
6. mdl136 field doesn't exist in API

## New Findings (2026-05-01)
- **ts_decay_exp** operator not yet tested on EPS
- PV87 dataset has 6666 ESG fields - ESG data may have different properties
- API has CONCURRENT_SIMULATION_LIMIT (5 simultaneous)
- API times out after ~5 minutes for slow simulations

## Breakthrough Strategies
1. ts_decay_exp on EPS with different windows
2. neutralization='INDUSTRY' with proper truncation setting
3. PV87 field combinations (simple rank expressions first)
4. Multi-field rank combinations (sum of ranks)