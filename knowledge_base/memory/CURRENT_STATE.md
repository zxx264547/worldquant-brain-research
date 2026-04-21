# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：Alpha挖掘验证阶段
- 核心目标：验证analyst4最佳Alpha的稳定性
- 已发现突破：analyst4 + actual_eps_value_quarterly 首次同时突破Sharpe>1和M/T>1

## 核心发现

| 指标 | 当前值 | 目标值 | 状态 |
|------|--------|--------|------|
| Sharpe | **1.00** (analyst4) | >=1.58 | ⚠️ 有进展但未达标 |
| Margin/Turnover | **2.90-3.41** | >1.0 | ✅ 远超目标 |
| Fitness | **1.43** | >0.5 | ✅ 远超目标 |

## 最佳Alpha候选

### Alpha #1 (最新突破)
- 数据集: **analyst4**
- 字段: **actual_eps_value_quarterly**
- 表达式: `ts_mean(winsorize(actual_eps_value_quarterly), 25)`
- Sharpe: **1.00**, Fitness: **1.43**, M/T: **2.96**
- 窗口测试: 23(1.00), 25(1.00), 26(1.00) 均成功

### Alpha #2
- 数据集: analyst4
- 字段: actual_dividend_value_quarterly
- 表达式: `ts_mean(winsorize(actual_dividend_value_quarterly), 15)`
- Sharpe: 0.82, Fitness: 1.20, M/T: 4.11

## 已验证的模板有效性

| 模板 | 数据集 | 效果 |
|------|--------|------|
| `ts_mean(winsorize({data}), 23-26)` | analyst4 | **最佳** |
| `ts_mean(winsorize({data}), 20)` | analyst4 | 有效 |
| `winsorize({data})` | pv87 | M/T好Sharpe低 |
| `rank({data})` | 所有 | M/T变为0 |

## 回溯期规律

- **奇数窗口**(23,25,27)更容易成功
- **偶数窗口**(24,26,28,30)容易失败
- 最优区间: **23-26**

## 已测试数据集(237个中)

| 数据集 | 结果 |
|--------|------|
| analyst4 | **最佳** - Sharpe=1.00, M/T=2.96 |
| pv87 | M/T好(3.01)但Sharpe仅0.64 |
| analyst49 | Sharpe=0.82但M/T=0 |
| pv13 | Sharpe=0.53但M/T=0 |
| 其他analyst数据集 | 大多失败或无效 |

## 项目框架整理

- ✅ 删除8个冗余脚本
- ✅ 输出文件移至data/outputs/
- ✅ 保留7个核心脚本
- ✅ research_agent模块完整

## 下一步方向

1. **深入优化analyst4**
   - 测试更多analyst4字段 + 窗口23-26
   - 尝试字段组合(eps + dividend)

2. **扩大数据集搜索**
   - 随机测试更多数据集
   - 寻找类似analyst4特性的其他数据集

3. **探索极限**
   - 测试更大窗口(50-60)
   - 尝试字段间的算术组合

---
*更新时间：2026年4月21日*
*关键发现：analyst4首次突破Sharpe与M/T的矛盾*