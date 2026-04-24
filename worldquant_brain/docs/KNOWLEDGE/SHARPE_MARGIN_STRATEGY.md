# Sharpe与Margin矛盾解决策略

## 核心发现

### 问题现象
从实际测试数据发现：
- **mdl136字段**：高Sharpe(~1.58)，但Margin/Turnover ≈ 0.02
- **pv87字段**：低Sharpe(~0.64)，但M/T ≈ 3.0

两个指标呈**反向关系**：提高Sharpe会降低M/T，反之亦然。

### 根本原因
- **高Sharpe策略**：依赖频繁信号变化 → 高换手 → 低Margin
- **高Margin策略**：信号稳定 → 低换手 → 低Sharpe

## 解决思路

### 方案1：混合数据集法
用**mdl136字段**（高Sharpe来源）+ **winsorize预处理**（降turnover）

测试有效的模板：
```
winsorize(mdl136_xxx)        # 降异常值影响
winsorize(ts_backfill(x))     # 回填缺失
ts_mean(winsorize(x), 10)     # 平滑+降噪
```

### 方案2：字段组合
用**ts_decay_linear**或**ts_mean**降低mdl136字段的换手率

### 方案3：调整挖掘策略
- 首轮：min_sharpe=0.7（不是1.0）
- 次轮：min_sharpe=1.0
- 提交：sharpe≥1.0

## 关键参数参考

| 参数 | 挖掘门槛 | 提交标准 |
|------|---------|---------|
| Sharpe | ≥0.7 | ≥1.0 |
| Fitness | >0.5 | >0.5 |
| PPC | <0.7 | <0.5 |
| Margin | >Turnover | >Turnover |
| Turnover | >0.01 | >0.01 |

## 测试数据集优先级

1. **mdl136** - 高Sharpe字段，适合做预处理降turnover
2. **pv87** - M/T高但Sharpe低，可做组合素材
3. **wds** - 消息数据，适合情感Alpha
4. **analyst4** - 分析师数据
5. **pv1/pv13** - 价格相关

## 下一步行动

1. 用mdl136 + winsorize模板批量测试
2. 寻找M/T>1且Sharpe>1的Alpha
3. 如仍不足，考虑IND/EUR地区（margin门槛更低）
