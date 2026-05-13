# vec_min/vec_max 同向极值匹配 — 突破性方法论

> 来源：论坛帖子 #1896 + 2026-05-13 实战验证
> 状态：已验证可提交 (Sharpe 2.36 → 提交版 2.02)

## 核心原则

**外层极值算子 → 内层必须用同向向量算子**

| 外层算子 | 内层算子 | 效果 |
|----------|----------|------|
| ts_min / ts_arg_min / group_min | vec_min | 捕捉向下极值信号 |
| ts_max / ts_arg_max / group_max | vec_max | 捕捉向上极值信号 |

论坛验证数据：
- `ts_min(vec_avg(...))` → Sharpe 1.71, Fitness 0.96
- `ts_min(vec_sum(...))` → Sharpe 1.73, Fitness 0.98
- `ts_min(vec_min(...))` → **Sharpe 1.81, Fitness 1.05**

## 实战验证：risk60 突破

### 最佳表达式
```
zscore(-ts_max(vec_max(rsk60_offer), 22))
```
- Sharpe: 2.36 (基础) / 2.02 (SECTOR neut, 提交版)
- Fitness: 5.17 / 3.37
- PPC: 0.07
- Turnover: 2.86%

### 关键发现

1. **zscore 是最佳外层包装**
   - 基础信号 `-ts_max(vec_max(rsk60_offer), 22)`: Sharpe 1.13
   - 加 zscore: Sharpe 2.36 (**翻倍**)
   - rank 反而有害: Sharpe 0.68

2. **窗口选择**：22天最优，5天(1.11) < 22天(1.13) > 66天(1.01) > 120天(0.85)

3. **中性化选择**：
   - NONE: Sharpe 2.36, Sub-Sharpe 1.0 (未通过)
   - SECTOR: Sharpe 2.02, Sub-Sharpe 1.07 (通过)
   - INDUSTRY: Sharpe 2.48, Sub-Sharpe 0.97 (更差)
   - MARKET: 破坏信号

4. **方向选择**：
   - max+max (rsk60_offer): Sharpe 1.13
   - min+min (rsk60_offer): Sharpe 0.83
   - vec_avg: Sharpe 1.15 (接近但略优于vec_max)

## 可用 VECTOR 数据集

| 数据集 | VECTOR 字段 | 最佳 Sharpe | 状态 |
|--------|-------------|-------------|------|
| risk60 | rsk60_offer, rsk60_last, rsk60_crowding | 2.36 | 已提交 |
| fundamental6 | fnd6_capxs, fnd6_caxts | 0.94 | 已测试，天花板低 |
| analyst10 | accumulation_distribution_line_* | 未测试 | 待探索 |
| analyst14 | 4个VECTOR字段 | 未测试 | 待探索 |
| analyst27 | 4个VECTOR字段 | 未测试 | 待探索 |

## 经济学逻辑

### risk60 借贷费率信号
```
借贷费率高 → 做空成本高 → 空头被挤出 → 卖压减少 → 股价上涨
```
- 取日内最大值 (vec_max): 关心"最贵的时候有多贵"
- 取22天最大值 (ts_max): 捕捉近期极端借贷事件
- 负号翻转: 高费用 = 正信号
- zscore 标准化: 消除行业/市值偏差，天然做多-做空

## 教训总结

### 为什么之前错过了
1. VECTOR 字段被忽略——大家都在用 MATRIX 字段
2. vec_min/vec_max 是"被忽视的宝藏算子"（帖子作者原话）
3. 之前尝试 fundamental6 的 VECTOR 字段只得到 0.94，放弃了这条路
4. risk60 (Securities Lending) 数据完全没被测试过

### 方法论推广
1. 对任何新的 VECTOR 数据集，先试 vec_min + ts_min 和 vec_max + ts_max
2. zscore 外层包装是通用利器
3. 始终尝试 SECTOR 中性化（不是 INDUSTRY）
4. 低 truncation (0.01) 改善 sub-universe 覆盖

## 已提交 Alpha

| Alpha ID | 表达式 | Sharpe | 日期 |
|----------|--------|--------|------|
| vR50553z | zscore(-ts_max(vec_max(rsk60_offer), 22)) | 2.02 | 2026-05-13 |
