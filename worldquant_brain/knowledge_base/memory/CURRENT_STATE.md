# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：深度优化Alpha阶段（目标Sharpe>=1.58）
- 最佳成绩：Sharpe 1.17 (analyst4 + eps + signed_power + ts_backfill)
- 已测试：1475个Alpha，其中924个成功，203个Sharpe>=1.0
- 差距：当前1.17 vs 目标1.58，需要约35%提升
- API状态：严重限流(429)，每次调用需等待

## API状态 (2026-05-01)

- TOP3000 Universe正常工作
- TOP1500/UVIX等Universe不可用
- 大量调用会触发429 Rate Limit
- 模拟创建成功但轮询超时严重(需300-600s)
- analyst4的actual_eps_value_quarterly字段表现最佳
- signed_power表达式有效果但超时严重

## 最佳Alpha表达式

```
ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)
Sharpe=1.17, Fitness=2.06, Margin=0.126, Turnover=0.006
```

## 新发现

### 短窗口signed_power测试失败
- 22窗口: 超时
- 11窗口: 429限流
- 5窗口: 429限流

### 简单表达式测试失败
- sign/abs/if_else全部超时或429

### analyst14/analyst27字段不可用
- analyst27只有VECTOR类型字段4个
- 字段名称与描述不匹配，无法直接使用

## 核心问题

单一字段/数据集已触及瓶颈（Sharpe 1.17），需要：
1. **vec_min/vec_max模式** - API需要修复
2. **group_rank/group_op** - 印度区经验称可优化Robust Sharpe
3. **多字段rank组合** - rank(A) + rank(B)模式

## API问题总结

### vec_min/ts_min 失败原因
- API返回 "must be an vector data"
- ts_mean/rank/ts_sum 不支持 event inputs (VECTOR字段)
- 原因：BRAIN API对VECTOR类型字段的处理有严格限制
- 论坛帖子声称1.81 Sharpe可能是过时的或针对不同数据版本

### API限流问题
- 429错误在4-6次调用后触发
- 模拟创建成功但轮询超时(需300-600s)
- TOP3000可用，TOP1500/UVIX不可用

### 字段类型说明
- MATRIX类型: 支持ts_mean/rank等算子 ✓
- VECTOR类型: 不支持ts_mean/rank等算子 ✗
- analyst4的actual_eps_value_quarterly是MATRIX类型，所以可以工作

## 新测试结果 (2026-05-04)

### model136 数据集测试
- `ts_mean(mdl136_qes_etf_us_flow_gross_pctvol, 22)`: Sharpe=0.65, Fitness=0.92
- ETF流量数据单独使用效果一般，不如EPS

### API状态
- 429限流严重
- 模拟创建后轮询超时严重(>180s)
- 建议降低测试频率

## 重要发现

### VECTOR vs MATRIX 字段类型
- **MATRIX类型**: 支持ts_mean/rank等算子 ✓ (代表字段: actual_eps_value_quarterly)
- **VECTOR类型**: 不支持ts_mean/rank等算子 ✗ (会报错"Operator does not support event inputs")

### vec_min/ts_min 失败原因
- vec_min/ts_min 需要 VECTOR 类型字段
- 但VECTOR类型不支持ts_mean包裹，导致无法构建复杂表达式
- 论坛帖子声称的1.81 Sharpe可能是针对旧版API或不同数据

### 纯MATRIX数据集 (可正常使用)
- model136: ETF流量因子 (50 MATRIX)
- fundamental6: 公司基本面 (48 MATRIX)
- analyst4: EPS预测 (26 MATRIX)
- pv87, news12 等

## 当前最佳Alpha

```
Alpha ID: A1g1Z1Vw
Expression: ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)
Sharpe: 1.17, Fitness: 2.06, Margin: 0.126, Turnover: 0.006
```

## 待测试方向

1. **model136 + analyst4 组合** - 等待API恢复
2. **fundamental13/fundamental17** - 综合基本面数据
3. **pv87** - 价格/价值数据
4. **sentiment21/22/23** - 情感数据 (纯MATRIX)