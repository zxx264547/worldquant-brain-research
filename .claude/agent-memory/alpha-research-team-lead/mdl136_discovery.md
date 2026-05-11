---
name: mdl136_discovery
description: WorldQuant forum discovered mdl136 as high-Sharpe field
type: reference
---

# mdl136 Field Discovery

## From Forum Knowledge
- mdl136 is listed as a **high-Sharpe field** (approx 1.58)
- pv87 has high Margin/Turnover ratio (~3.0) but low Sharpe (~0.64)
- winsorize + ts_backfill + ts_mean patterns are recommended

## Key Patterns from Forum
1. `winsorize(mdl136_xxx)` -降异常值影响
2. `winsorize(ts_backfill(x))` - 回填缺失
3. `ts_mean(winsorize(x), 10)` - 平滑+降噪
4. `ts_decay_linear` - 降低换手率

## Implication
The current approach uses analyst4 (actual_eps_value_quarterly) which maxes out at Sharpe=1.04. But mdl136 is reported to have Sharpe ~1.58 - we should test this field!

## Action Items
- Test mdl136 field expressions
- Use TOP500 universe for faster testing
- Apply winsorize + ts_mean patterns