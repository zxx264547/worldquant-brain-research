---
name: user_role
description: WorldQuant Alpha Research Team Lead coordination role
type: user
---

# User Role

User is running WorldQuant BRAIN alpha research with the goal of finding Sharpe >= 1.58 alphas for submission.

## Key Constraints
- **PPA Submission Standards**: Sharpe >= 1.58, Fitness > 0.5, PPC < 0.5, Margin > Turnover
- **OB53521 Workflow**: 0-op (rank/zscore) -> 1-op (ts_mean/ts_decay/ts_delta) -> 2-op+ (nested operations)
- **Time Windows**: Only use 5, 22, 66, 120, 252, 504
- **API Rate Limiting**: Currently experiencing severe rate limiting (429 errors)

## User Goals
1. Find/construct alphas with Sharpe >= 1.58
2. Achieve acceptable Fitness > 0.5
3. Maintain PPC < 0.5
4. Ensure Margin > Turnover

## How to Apply
- When discussing Sharpe improvements, focus on 2-op+ nested operations
- When discussing submission, verify all 4 criteria are met
- API rate limiting requires longer delays between requests
