# Alpha挖掘研究总结

## 基准Alpha

**表达式**: `ts_mean(winsorize(actual_eps_value_quarterly), 25)`

**参数**:
- dataset: analyst4/10/49
- region: USA
- universe: TOP3000
- delay: 1
- decay: 1
- truncation: 0.25

**结果**: Sharpe=1.02, Fitness=1.43, PPC<0.5

---

## 测试结果汇总

### 窗口测试
| 窗口 | Sharpe | Fitness |
|-----|--------|---------|
| 10 | 1.01 | 1.40 |
| 15 | 1.01 | 1.40 |
| 20 | 1.01 | 1.41 |
| 25 | 1.02 | 1.43 |
| 30 | 超时 | - |

### 算子变换
| 算子 | Sharpe | 效果 |
|------|--------|------|
| rank() | 0.71 | ↓ |
| ts_zscore | 超时 | - |
| signed_power | 超时 | - |
| ts_backfill | 超时 | - |

### 不同数据集
| 数据集 | Sharpe | 备注 |
|--------|--------|------|
| analyst4 | 1.02 | 最佳 |
| analyst10 | 1.02 | 相同 |
| pv87 | 0.64 | 低于基准 |

### 参数调整
| 参数 | 值 | 结果 |
|------|-----|------|
| truncation=0.3 | 1.02 | ≈ |
| truncation=0.4 | 超时 | - |

---

## 发现

1. **基准Alpha已接近优化极限**：窗口25优于其他窗口
2. **rank降低Sharpe**：从1.02降至0.71
3. **长窗口或复杂算子导致超时**
4. **analyst4数据集表现最佳**

---

## 论坛经验（OB53521工作流 2026年1月）

### 核心法则
1. **增量复杂度**: 0-op(rank/zscore) -> 1-op(ts类) -> 2-op+嵌套
2. **时间窗口**: 仅用5,22,66,120,252,504（禁止10,14,30等）
3. **归一化**: Fundamental/Volume必须rank()包裹
4. **批量**: 每次8个Alpha
5. **Fitness<1.0**: Decay=2, Neut=Industry, Trunc=0.01

### 其他技巧
- signed_power(x,1.3): +0.02 robs
- scale: +0.02
- crowding中性化: 快速有效

---

## API状态

- 2026-04-24 13:00+ - SSL错误，API不可用
- 持续监控中（每5秒）

---

## 待测试方向（API恢复后）

### 高优先级（基于论坛经验）

1. **signed_power_1.3** - signed_power(x, 1.3)
2. **scale** - 需确认API支持
3. **crowding中性化** - neutralization='crowding'
4. **group_rank组合** - group_rank(ts_mean(eps, 25), sector)

### 中优先级

5. **ts_sum替代ts_mean**
6. **truncation=0.35**
7. **多窗口组合**

### 低优先级

8. **不同数据集** (analyst49, mdl136)
9. **region=EUROPE/INDIA测试**

---
*生成时间：2026年4月24日 16:35*
*最后更新：2026年4月24日 16:35*