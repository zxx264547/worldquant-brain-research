---
name: new_dataset_exploration_20260523
description: Failed exploration of new datasets - only 1 valid but low Sharpe (0.70), 4 unknown fields, 2 API stuck
type: reference
---

# 新数据集探索结果 2026-05-23

## 背景
min_loan_rate系列因CW>0.1和Prod_Corr>0.7被拒绝，需要找全新的数据集和字段。

## 测试的候选字段

| 字段 | 数据集 | Sharpe | 状态 |
|------|--------|--------|------|
| anl47_totalrawsignal | analyst4 | 0.70 | 有效但低 |
| anl47_indicator | analyst4 | 0 | API卡在35% |
| anl47_rawexperts | analyst4 | 0 | API卡在35% |
| anl10_eps_value_ttm | analyst10 | 0 | 未知变量 |
| anl14_eps_value_ttm | analyst14 | 0 | 未知变量 |
| mdl136_bid_ask_spread | mdl136 | 0 | 未知变量 |
| pv87_ebit | pv87 | 0 | 未知变量 |

## 关键发现

1. **候选名单中的字段名不正确**：anl10_eps_value_ttm等字段在BRAIN API中不存在
   - 需要找到正确的字段名

2. **analyst4字段存在但API卡住**：anl47_* 字段可以提交但API卡在35%进度
   - 这是已知的API问题

3. **risk60仍然是最可靠的**：Sharpe 2.36+

## 建议的下一步

- 使用BRAIN API的/data-fields端点探索可用的VECTOR字段
- 尝试解决analyst4字段的API卡住问题
- 继续优化risk60数据集的alphas