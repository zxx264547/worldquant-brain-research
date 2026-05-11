---
name: Research Progress 20260508
description: Alpha挖掘进度 - Best Sharpe=1.17遇到天花板
type: project
---

## Alpha挖掘进度 2026-05-08

### 当前状态
- Best Sharpe: 1.17 (目标: 1.58) - EPS天花板确认
- 总测试结果: 1596个
- Sharpe >= 1.5: 0个

### 已验证有效的Region/Universe组合
- USA/TOP3000: 有效 (EPS信号)
- USA/TOP500: 有效
- ASI/TOP500: 有效 (Sharpe=0.28, 低Fitness)

### 已验证无效的组合
- USA/TOP1500: 无效
- USA/TOP1000: 超时
- EUR/TOP3000, TOP1500, TOP1000: 无效
- GLB/TOP1500, TOP1000: 无效
- ASI/TOP3000, TOP1500, TOP1000: 无效

### 成功模式 (Sharpe ~1.17)
- ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)

### 数学变换测试 (Sharpe范围: 0.5-0.73)
- log(ts_sum(eps,252)): Sharpe 0.73
- ts_zscore(eps,22): Sharpe 0.58
- ts_zscore(eps,66): Sharpe 0.50

### 当前进行中的测试
1. completely_new.py - ts_corr, decay_linear, 多字段组合等15个新表达式
2. math_transform_test2.py - 仍在运行

### 下一步
1. 等待当前测试完成
2. 分析新表达式的Sharpe
3. 如果仍无法突破1.17，尝试:
   - 中性化(Industry)组合
   - Decay参数优化
   - 或者考虑完全不同的数据集(field探索)