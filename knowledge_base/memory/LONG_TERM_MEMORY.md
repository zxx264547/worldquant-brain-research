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