---
name: alpha_research_status_20260501
description: Current alpha research status and ceiling analysis - Updated 2026-05-01
type: project
---

# Alpha Research Status - 2026-05-01 (Updated)

## Critical Finding: 1.17 Ceiling is REAL
- After 964 completed alphas with Sharpe data: 0 alphas >= 1.2, 0 alphas >= 1.5
- All top 20 results are exactly 1.17 Sharpe
- The single-field EPS approach has HIT ITS LIMIT
- **ts_decay_exp operator DOES NOT EXIST in BRAIN API**

## Distribution Analysis
- Total completed: 964
- Sharpe range: -1.09 to 1.17
- Mean Sharpe: 0.654
- >= 1.0: 219 alphas
- >= 1.17: only the top ~20 (all clustered at 1.17)

## What This Means
The ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3) pattern is the CEILING for this approach. Further optimization within this pattern will NOT break through.

## Forum Discovery: AIAC Template Pattern
From forum post ID 1935: ts_rank(ts_max({data},d1),d2) pattern:
- d1,d2 can be (60,250) or (20,120)
- "该模板衡量当前季度的峰值在过去一年中处于什么位置"
- This is DIFFERENT from our ts_sum approach!

**Key insight**: ts_max vs ts_sum captures different information:
- ts_sum: total cumulative value over window
- ts_max: peak value in the window

## New Breakthrough Ideas Added (2026-05-01)
1. bt_001: ts_rank(ts_max(actual_eps_value_quarterly, 60), 250) - AIAC模板
2. bt_002: ts_rank(ts_max(actual_eps_value_quarterly, 20), 120) - AIAC短窗口
3. bt_003: rank(ts_sum(eps,252)) + rank(ts_sum(cashflow,252)) - 多字段组合
4. bt_004: ts_delta(ts_rank(eps,60), 5) - ts_delta on ts_rank
5. bt_005: ts_mean(analyst49::eps, 22) - analyst49数据集
6. bt_006-008: IND/CHN/EUR regions - 不同区域测试

## API Status
- Rate limit exceeded - multiple retries failing
- SSL errors and proxy issues causing instability
- Suggest waiting before next test batch

## Current Best Alpha
- **Sharpe**: 1.17 (CEILING)
- **Expression**: `ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)`
- **Alpha ID**: A1g1Z1Vw
- **Fitness**: 2.06, **Turnover**: 0.0061, **Margin**: 0.126

## Worker Status
- 8 workers running as daemon processes
- Team Lead Service runs via cron every 30 seconds
- 309 ideas in queue (including 8 new breakthrough ideas)

## Immediate Actions When API Recovers
1. Test AIAC template: ts_rank(ts_max(eps, 60), 250) and variations
2. Test multi-field combinations
3. Test IND/CHN/EUR regions
4. Do NOT keep optimizing the 1.17 pattern