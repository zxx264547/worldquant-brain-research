# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：Alpha参数优化阶段 - 遇到API速率限制
- 核心目标：寻找Sharpe≥1.58的Alpha
- 最佳成绩：Sharpe 1.17
- 独立表达式测试: 692个

## 当前最佳Alpha (Sharpe=1.17)

| 指标 | 值 |
|------|-----|
| Sharpe | 1.17 |
| Fitness | 2.06 |
| Margin | 0.126 |
| Turnover | 0.0061 |

**表达式**:
```
ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 2-4)
```

**最优参数组合**:
- 数据集: analyst4 或 analyst9 (效果相同)
- 字段: actual_eps_value_quarterly
- ts_sum窗口: 252
- signed_power指数: 1.02-1.05
- ts_backfill窗口: 2, 3, 4 (效果相同)

## 已验证无效的方向

1. **中性化方法** - 全部无效，会降低Sharpe
   - industry, market, sector, crowding

2. **时间窗口** - 252最优
   - 5, 22, 66, 120, 280, 504 都差于252

3. **字段对比** - EPS最优
   - actual_eps_value_quarterly: 1.17
   - actual_dividend_value_quarterly: ~0.8
   - actual_cashflow_per_share: ~0.81
   - actual_sales_value: ~0.74
   - market data (close, vwap): ~0.68

4. **算子组合**
   - ts_decay_linear/exp: 语法错误
   - rank嵌套: 超时或速率限制
   - ts_rank嵌套: 超时

## 2026-04-29 新批次测试结果

| Idea ID | Sharpe | 说明 |
|---------|--------|------|
| idea_3006 | 1.17 | backfill=2, exponent=1.05 |
| idea_3007 | 1.17 | backfill=4, exponent=1.05 |
| idea_3028 | 1.17 | analyst9数据集 |
| idea_3003 | 1.15 | exponent=1.1 |
| idea_3012 | 1.15 | window=220 |
| idea_3001 | 1.14 | exponent=0.95 |
| idea_3004 | 1.11 | exponent=1.15 |

**结论**: 新批次无突破，1.17是当前模式极限

## 问题分析

### API速率限制
- 429错误严重
- 8个workers同时运行导致触发限制
- 需要减少并发数量

### 突破1.58的障碍
当前模式(single-field ts_sum + signed_power)在692个测试中最高仅1.17。要达到1.58需要:
1. 发现新有效字段(非EPS)
2. 新的算子结构
3. 多信号组合

## 建议下一步

1. **降低API负载**: 只运行2-3个workers
2. **尝试TOP500 universe**: 更快测试周期
3. **新方向探索**:
   - 论坛寻找1.58+ Alpha的表达式模式
   - 测试ts_cumsum, ts_product
   - 寻找有效的mdl136字段替代

## 最新测试Ideas

- 134个ideas在队列中
- 121个分配给workers
- 11个已完成
- 109个等待执行(受速率限制)

---
*更新时间: 2026年04月29日 23:43*