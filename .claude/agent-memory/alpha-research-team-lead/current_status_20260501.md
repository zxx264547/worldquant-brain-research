---
name: current_status_20260501
description: API issue - simulations stuck at progress 0.35, workers not processing new ideas
type: project
---

# Alpha Research Status - 2026-05-01 02:10 UTC

## Current Status

### Best Alpha
- **Sharpe: 1.17** (41 from target of 1.58)
- **Expression**: `ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)`
- **Fitness**: 2.06, **Turnover**: 0.0061, **Margin**: 0.126

### API Issue - SIMULATIONS STUCK AT 35%
The API simulations are completing (HTTP 201) but when polling for results, they show:
- `status: null`
- `progress: 0.35`
- Never progressing to COMPLETED

This has been happening for 4+ hours. The issue is NOT authentication - fresh tokens work. The issue appears to be server-side rate limiting or queue congestion.

### Worker Status
- 8 workers running but idle - "No ideas assigned"
- State.json shows ideas are assigned but workers can't find them
- Root cause: idea IDs in state.json don't match ideas in ideas.json

## What Was Working Before
- ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3) - Sharpe 1.17
- ts_sum(actual_eps_value_quarterly, 245) - Sharpe 1.16

## What Doesn't Work
- ts_decay_linear, ts_decay_exp - syntax errors
- ts_zscore, ts_corr with fundamentals - timeout
- mdl136 fields - unknown variable errors (field naming is wrong)
- All neutralization methods - invalid

## Gap to Target
- Current: 1.17, Target: 1.58
- Gap: 35% improvement needed
- This requires finding a fundamentally different approach

## Key Insight
The OB53521 single-field approach has hit a ceiling at ~1.17 Sharpe. The current simulations are stuck in a queue. Need to either:
1. Wait for API to recover
2. Find a different approach that doesn't hit rate limits
3. Discover new valid fields that provide different signal

## Recent Results
- Total results: 1562
- Completed with Sharpe > 0: 833
- Submission ready (Sharpe>=1.58 & Margin>Turnover): 0