# 长期记忆

> 重要发现、经验总结、套路积累

## 重要发现

### Alpha筛选标准 (PPA)
- **PPC < 0.5** (核心门槛，必须满足)
- **Sharpe >= 1.0** (建议 >=1.05 更安全)
- **Fitness > 0.5** (必须)
- **Margin > Turnover** (必须，表示盈利交易>亏损交易)
- **Turnover > 0.01** (必须，避免僵尸Alpha)

### 数据集特征
- **analyst4**: **首次同时实现Sharpe>1和M/T>1**。关键字段：actual_eps_value_quarterly, actual_dividend_value_quarterly
- **pv87**: 金融数据，Margin/Turnover比例好(3.01)，但Sharpe相对较低(0.64)
- **mdl136**: 高频数据，Sharpe可达1.5+，但Margin/Turnover比例差(~0.02)；API调用有时失败
- **analyst10**: 分析师数据，Sharpe=0.72，M/T=9.47，比pv87平衡但仍未达标

### 表达式算子限制
- **`demean`** 在FASTEXPR中不可用，会报错"inaccessible or unknown operator"
- **`winsorize`** + **`ts_mean`** 组合可有效降低Turnover
- 使用 **`rank()`** 处理会使Margin/Turnover变为0
- **偶数窗口**(24,26,28,30)容易失败，奇数窗口(23,25,27)更容易成功

### 核心矛盾与突破
- 高Sharpe通常意味着高换手（信号变化频繁）
- 低换手策略信号稳定但Sharpe较低
- **analyst4突破**: 首次同时实现Sharpe=1.00和M/T=2.96
- 最优回溯期区间: **23-26** (奇数窗口)

## 套路积累

### 成功模板（验证有效）
| 模板 | 效果 |
|------|------|
| `winsorize({data})` | 基础降噪，略微降低Turnover |
| `ts_mean({data}, 20)` | 时间序列平滑，显著降低Turnover |
| `ts_mean(winsorize({data}), 20)` | 组合效果最佳 |
| `rank(ts_mean({data}, 20))` | 平滑+排序，提高稳定性 |
| `ts_zscore({data}, 20)` | Z-score标准化 |

### 预处理策略
1. **ts_backfill**: 回测数据填充，处理NaN
2. **winsorize**: 异常值处理，限制极端值
3. **ts_mean**: 平滑处理，降低噪声
4. **rank**: 排序处理，线性化关系

### 常用参数
- **delay**: 1 (USA市场)
- **decay**: 0.0 (无衰减)
- **universe**: TOP3000
- **neutralization**: NONE (避免PPC超标)

## 失败教训

### 避免的做法
- **单一字段裸跑**: Turnover过高，无法满足Margin>Turnover
- **长回溯期+无预处理**: Sharpe不稳定，Fitness低
- **忽视中性化**: PPC容易超标
- **使用demean算子**: FASTEXPR不支持

### 常见陷阱
- **pv87高Margin假象**: 需同时验证Sharpe，单独Margin高不够
- **mdl136高Sharpe假象**: 需同时验证Margin/Turnover，单独Sharpe高不够
- **长回溯ts_mean**: 虽然降低Turnover但可能损害Sharpe

## 优质资源

### 论坛帖子分类
- **PPA标准**: USA>5, EUR>10, CHN>3 等margin标准
- **Alpha挖掘**: 多数据集组合、预处理策略
- **因子组合**: 如何Combine多个Alpha

### API注意事项
- `pasteurization` 字段必须设置为 'ON'
- `language` 设置为 'FASTEXPR'
- 创建模拟后需要轮询等待完成
- 使用 `Retry-After` header调整轮询间隔

---

*更新时间：2026年4月19日*
## 论坛新技巧（2026-04-23）

### 印度区帖子1737 - 常见问题解决
- **Robust Universe Sharpe<1**：group_rank, signed_power
- **turnover>40%**：ts_decay_linear, decay调整
- **Weight过于集中**：ts_backfill, ts_arg_max, ts_arg_min, ts_av_diff
- **2 year Sharpe<1.58**：group_op

### EUR帖子1915 - TOPCS1600经验
- **Date Coverage不足**：ts_backfill
- **股票数量Coverage不足**：group_backfill
- **最佳实践**：group_backfill(alpha, group_cartesian_product(country, subindustry), 126)

---
*更新时间：2026年4月23日*

## Alpha优化技巧（帖子1778）

### Robust Universe Sharp
- **ts_backfill窗口调整**：从60调整到90-120
- **group_backfill**：找到能改善数据集的group进行插值
- **group_neutralize/group_zscore**：中性化和归一化

### Sub Universe Sharp
- 使用Subindustry中性化
- 更换风险中性化
- 更换股票池

### Turnover控制
- 调整window size（更小窗口→更高换手）
- 调整decay参数
- 使用ts_target_tvr_decay或ts_decay_linear

---
*更新时间：2026年4月23日*

## Alpha优化技巧（2026-04-23更新）

### 帖子1737 - 印度区因子挖掘技巧
- **Robust Universe Sharpe<1**：group_rank, signed_power
- **turnover>40%**：ts_decay_linear, decay调整
- **Weight过于集中**：ts_backfill, ts_arg_max, ts_arg_min, ts_av_diff
- **2 year Sharpe<1.58**：group_op

### 帖子1778 - Alpha优化
- **Robust Universe Sharp**：ts_backfill窗口60→90-120，group_backfill，group_neutralize/group_zscore
- **Sub Universe Sharp**：Subindustry中性化
- **Turnover控制**：ts_decay_linear, ts_target_tvr_decay

### 帖子1915 - EUR TOPCS1600经验
- **Date Coverage不足**：ts_backfill
- **股票数量Coverage不足**：group_backfill
- **最佳实践**：group_backfill(alpha, group_cartesian_product(country, subindustry), 126)

### 算子参数设置
- ts_backfill默认窗口：60-126
- ts_decay_linear常用窗口：10-20
- signed_power指数：1.3-2.0

---
*更新时间：2026年4月23日*

## 参数优化结论（2026-04-23）

### truncation + decay 组合效果
- truncation=0.25 + decay=1 可将Sharpe从1.0提升到1.02
- truncation≥0.25后Sharpe稳定在1.02

### 重要参数规律
- decay必须是整数
- truncation与decay配合使用才能有效
- 单独使用decay会报错

---
*更新时间：2026年4月23日*

## 测试结果汇总（2026-04-23）

### 参数优化
| 参数 | Sharpe | 提升 |
|------|--------|------|
| 基准 (t=0, d=0) | 1.00 | - |
| t=0.25, d=1 | 1.02 | +2% |
| t=0.3-0.4, d=1 | 1.02 | +2% |

### 表达式优化（均未能提升Sharpe）
- signed_power: 0.79 (↓)
- ts_decay_linear: 0.99 (≈)
- ts_backfill_60: 0.99 (≈)
- group_rank: 0.71 (↓)

### 字段组合（均未能提升Sharpe）
- eps+div: 0.83 (↓)
- eps*div: 0.54 (↓↓)

### 关键结论
1. 参数微调(truncation+decay)最多提升2%
2. 复杂表达式变换反而降低Sharpe
3. Sharpe从1.0到1.58需要更大突破

---
*更新时间：2026年4月23日*

## 待测试字段（API超时未能验证）

- actual_cashflow_per_share_value_quarterly
- actual_sales_value_annual  
- actual_net_income_value_quarterly
- actual_book_value_per_share_quarterly

---
*更新时间：2026年4月23日*

## 字段测试结果（2026-04-23）

### analyst4 字段
| 字段 | Sharpe | Fitness |
|------|--------|---------|
| actual_eps_value_quarterly | 1.02 | 1.43 |
| actual_dividend_value_quarterly | 0.82 | - |
| actual_cashflow_per_share_value_quarterly | 0.74 | 1.07 |
| actual_sales_value_annual | 0.74 | 1.05 |

### 其他analyst数据集
| 数据集 | Sharpe | Fitness |
|--------|--------|---------|
| analyst4 | 1.02 | 1.43 |
| analyst10 | 1.02 | 1.43 |
| analyst49 | 1.02 | 1.43 |

### 结论
- eps字段在所有analyst数据集表现一致（Sharpe 1.02）
- dividend/cashflow/sales显著低于eps

---
*更新时间：2026年4月23日*

## Alpha优化方向总结（2026-04-24）

### 已验证有效的模式
1. **winsorize + ts_mean** 是稳定的预处理组合
2. **窗口25** 在analyst4数据集表现最佳
3. **truncation=0.25 + decay=1** 是有效的参数组合
4. **actual_eps_value_quarterly** 是表现最好的字段

### 已验证无效的模式
1. **rank()** 降低Sharpe（1.02→0.71）
2. **signed_power** 导致超时
3. **长窗口**（30+）导致超时
4. **pv87字段** 表现不如analyst4

### 关键教训
- API超时严重限制了复杂因子的测试
- 简单baseline反而更稳定
- 突破1.58需要完全不同的策略

---
