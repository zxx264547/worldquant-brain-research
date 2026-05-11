---
name: api_findings
description: Critical API findings about valid settings and rate limits
type: reference
---

# API Findings

## Valid Neutralization Values (CRITICAL)
- "industry" is NOT a valid choice
- Valid choices appear to be: "NONE", "market", "sector", "crowding" (need verification)
- Error: `"industry" is not a valid choice`

## Deep Exploration v6 Results (2026-04-25 22:06-22:59)
| Variant | Result |
|---------|--------|
| signed_power_1.3 | Sharpe=0.89 (WORSE than baseline 1.04) |
| ts_rank_nested | FAILED (600s timeout) |
| double_smooth | Sharpe=1.04 (same as baseline) |
| rank_wrapper | FAILED (rate limit) |
| industry_neutral | FAILED (invalid neutralization choice) |
| decay_2 | FAILED (rate limit) |
| golden_combo | FAILED (invalid neutralization + rate limit) |
| trunc_001 | FAILED (rate limit) |

## API Rate Limit Status
- Rate limit is severe - many requests failing
- Need to space out requests more
- TOP500 universe might be faster

## What Works
- ts_sum(winsorize(actual_eps_value_quarterly), 25)/25: Sharpe=1.04
- ts_mean(ts_sum(winsorize(actual_eps_value_quarterly), 25)/25, 5): Sharpe=1.04 (same)

## What Doesn't Work
- signed_power on top of ts_sum (0.89 vs 1.04)
- ts_rank nested (timed out)
- rank wrapper (rate limit hit)
- industry neutralization (invalid)

## How to Apply
- Don't use "industry" neutralization
- Need to reduce API calls to avoid rate limiting
- Consider using TOP500 for faster exploration