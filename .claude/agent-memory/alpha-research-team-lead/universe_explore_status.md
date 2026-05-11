---
name: universe_explore_status
description: Status of universe exploration script testing different universes and windows
type: project
---

# Universe Exploration (2026-04-26 00:00)

## Script Created
- /home/zxx/worldQuant/worldquant_brain/scripts/alpha_mining/universe_explore.py
- 9 variants testing TOP500, TOP1500, and extreme windows (5, 120, 252, 504)

## Current Best
- ts_sum(winsorize(actual_eps_value_quarterly), 25)/25: Sharpe=1.04, Fitness=1.47

## Key Learnings
1. "industry", "market", "sector", "crowding" neutralization are ALL INVALID
2. signed_power(1.3) HURTS performance (0.89 vs 1.04)
3. ts_rank nested on eps fails (600s timeout)
4. rank wrapper hits rate limits
5. Market data fields (close, vwap, open) perform MUCH worse than EPS (0.68 vs 1.04)

## Gap to Target
- Sharpe 1.04 -> 1.58 (52% gap)

## Next Strategy
- Try different universes (TOP500, TOP1500)
- Try extreme windows (252, 504)
- ts_mean (not ts_sum) with window 5
- If none work, need to consult forum for advanced techniques