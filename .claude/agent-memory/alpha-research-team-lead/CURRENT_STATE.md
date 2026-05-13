# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：全面排查 — 所有已知数据源方向已触及天花板
- 核心目标：寻找Sharpe>=1.58的Alpha
- 最佳成绩：Sharpe 1.17 (EPS analyst4, 结构天花板)
- 已测试独立表达式: 240+

## 当前最佳Alpha (Sharpe=1.17)

| 指标 | 值 |
|------|-----|
| Sharpe | 1.17 |
| Fitness | 1.90 |
| Margin | 0.057 |
| Turnover | 0.0063 |
| PPC | 0.327 |

**表达式**:
```
ts_backfill(ts_sum(actual_eps_value_quarterly, 252), 3)
```

**参数**:
- delay=0或1 (效果相同)
- signed_power: 不加更好 (加后还是1.17)
- neutralization: NONE (INDUSTRY降低至0.23-0.27)
- 窗口: 252最优

## 已验证无效的方向 (完整列表)

### 数据源
- **analyst4**: EPS 1.17(天花板), dividend 0.84, sales 0.69, cashflow 0.52
- **price**: close ts_sum 0.85(天花板), ts_mean 0.78, rank+neut 0.23-0.27
- **fundamental6**: eps 0.71, bookvalue 0.67-0.70 (coverage仅0.5)
- **pv87**: bps 0.70, affops 0.67 (信号弱)
- **sentiment21**: snt21_2neg_mean 0.56 (弱)
- **news12**: dividend_yield 0.77, eod_close 0.68, atr14 0.55 (未突破)

### 参数
- delay=0 vs 1: 相同Sharpe 1.17 (无差异)
- signed_power: 不提升Sharpe
- neutralization INDUSTRY: 破坏信号 (price跌至0.23, corr变负)
- decay=0-5: 无突破性变化
- truncation: 0.01-0.25: 无差别

### 算子
- ts_rank: 0.65 (差于ts_sum)
- group_rank: 0.68 (差于rank)
- signed_power: 无增量价值
- ts_corr: -1.03 (with INDUSTRY neut)
- ts_delta momentum: 0.52-0.66

## 已识别但未测试的数据集
- analyst10 (Performance-Weighted Analyst Estimates)
- analyst11 (ESG scores)
- 其他alt data需要进一步发现

## 下一步建议
- 尝试analyst10 (weighted analyst estimates, 可能比analyst4更强)
- 多市场测试 (EUR/ASI) 如果analyst4数据可用
- 需要发现全新数据源才能突破1.17天花板
