# 待提交Alpha

## Alpha #1 (当前最佳)

| 项目 | 值 |
|------|-----|
| 表达式 | `ts_mean(winsorize(actual_eps_value_quarterly), 25)` |
| 数据集 | analyst4/10/49 |
| 地区 | USA |
| Universe | TOP3000 |
| Delay | 1 |
| Decay | 1 |
| Truncation | 0.25 |

## 测试结果汇总

### 数据集对比
| 数据集 | Sharpe | Fitness |
|--------|--------|---------|
| analyst4 | 1.02 | 1.43 |
| analyst10 | 1.02 | 1.43 |
| analyst49 | 1.02 | 1.43 |

### 字段对比
| 字段 | Sharpe | 备注 |
|------|--------|------|
| actual_eps_value_quarterly | 1.02 | 最佳 |
| actual_dividend_value_quarterly | 0.82 | - |
| actual_cashflow_per_share_value_quarterly | 0.74 | - |
| actual_sales_value_annual | 0.74 | - |

### 参数优化
| 参数 | Sharpe | 提升 |
|------|--------|------|
| t=0, d=0 | 1.00 | 基准 |
| t=0.25, d=1 | 1.02 | +2% |

## 问题

- Sharpe 1.02 < 1.58（差距54%）
- 需要更大突破

---
*最后更新：2026年4月23日*
