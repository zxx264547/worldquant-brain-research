# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展
> 最后更新：2026-06-13 17:10

## 研究进度

- 当前阶段：API模拟引擎卡10%/35%，提交功能正常但限流严格
- 最佳成绩：**Sharpe 2.69** - INDUSTRY中性化+ts_mean smoothing
- **已确认提交成功** (HTTP 201):
  - QPQ63JLg (Sharpe 2.55) - `ts_mean(zscore(-ts_max(vec_max(min_loan_rate), 66)), 22)`
  - omYZLz2k (Sharpe 2.51) - `zscore(-ts_max(vec_max(mean_loan_rate), 66))`

## 关键发现

### CONCENTRATED_WEIGHT解决方案
- **ts_mean() smoothing** on zscore output reduces concentration - PASSES check!
- Single window expressions with INDUSTRY neutralization work better than dual-window zscore combos
- **min_66_mean22_ind**: ts_mean(zscore(-ts_max(vec_max(min_loan_rate), 66)), 22) → Sharpe 2.55, SUBMITTED
- **mean_66_single_ind**: zscore(-ts_max(vec_max(mean_loan_rate), 66)) → Sharpe 2.51, SUBMITTED

### Failed patterns (CONCENTRATED_WEIGHT FAIL)
- min_5_66_ind: dual window too concentrated (value=0.14, limit=0.1)
- mean_22_66_ind: dual window too concentrated (value=0.136, limit=0.1)
- max_22_66_ind: dual window + LOW_SUB_UNIVERSE_SHARPE FAIL

## 关键发现

### CONCENTRATED_WEIGHT是主要阻塞原因
- qMgEkAbj (Sharpe 2.53): CONCENTRATED_WEIGHT FAIL
- VkOdOMLb (Sharpe 2.49): CONCENTRATED_WEIGHT FAIL
- A1nqO7mQ (Sharpe 2.46): LOW_SUB_UNIVERSE_SHARPE FAIL
- **通过的Alpha**（O0oJvZn1等）：只有WARNING级别问题

### API问题
- 模拟引擎：从完全卡死变为卡10%/35%循环，仍无法完成新模拟
- 429限流：连续提交6个Alpha后触发
- blvPL7Yp等：303重定向后400错误（服务器bug）

### 成功提交模式
`zscore(-ts_max(vec_max(field), window1)) + zscore(-ts_max(vec_max(field), window2))`
- 两个不同window的组合可降低集中度

## 已确认提交成功的Alpha

| Alpha ID | Sharpe | 表达式 |
|----------|--------|--------|
| O0oJvZn1 | 2.50 | zscore(-ts_max(vec_max(min_loan_rate), 22)) + zscore(-ts_max(vec_max(min_loan_rate), 66)) |
| blNzWNQR | 2.36 | zscore(-ts_max(vec_max(mean_loan_rate), 66)) |

## 待确认提交（返回201但状态仍为UNSUBMITTED）

| Alpha ID | Sharpe | 状态 |
|----------|--------|------|
| GrkeA5eZ | 2.44 | UNSUBMITTED (提交返回201) |
| QPEYPVJX | 2.42 | UNSUBMITTED (提交返回201) |
| xAeGmO8m | 2.48 | UNSUBMITTED (提交返回201) |
| e7L6w5NO | 2.47 | UNSUBMITTED (提交返回201) |

## 候选方向

1. **多窗口组合** - 参考O0oJvZn1模式，创建更多多窗口表达式
2. **signed_power降相关性** - 模拟引擎恢复后可尝试
3. **analyst47** - 评级★的数据集，尚未充分探索

## 最佳Alpha (按类别)

### 纯s3 (s3_sector_decay — 16条)
| Alpha ID | 表达式 | Sharpe | 配置 |
|----------|--------|--------|------|
| N1nk8wLe | min_loan_rate w22 | **2.45** | truncation=0.05 |
| N1nkL69E | min_loan_rate w22 | 2.23 | SECTOR中性化 |
| akNXwAW9 | min_loan_rate w22 | 2.18 | decay=2 |
| A1nqeQWW | mean_loan_rate w22 | 2.07 | SECTOR中性化 |
| N1nW00Pe | max_loan_rate w5 | 1.98 | decay=8 |

### 跨数据集 (s3x — 9条)
| Alpha ID | 表达式 | Sharpe |
|----------|--------|--------|
| MPb9zdMo | min22 + close22 | 2.26 |
| 78xg2pa2 | mean22 + close22 | 2.11 |
| 0mAn6v7r | min22 + vol22 | 1.99 |
| XgkXMXp0 | max5 + close22 | 1.89 |

### 产品相关性测试 (spc — 多条)
| Alpha ID | 表达式 | Sharpe | 备注 |
|----------|--------|--------|------|
| e7neMpoN | signed_power(zscore(min22), 10) | 1.61 | fitness=6.89, ppc=0.016, turnover=0.125, **Concentrated Weight待修复** |
| P0njKg2J | min22 + CROWDING | 2.19 | |
| 1YoVY9WW | min22 + vec_avg(min) | 1.91 | turnover 0.23过高 |

## 提交检查状态

**已有成功提交的 Alpha** ✅

| Alpha ID | Sharpe | Prod Corr | Self Corr | CW | 状态 |
|----------|--------|-----------|-----------|-----|------|
| e7neMpoN | 1.61 | **0.682** ✅ | 0.347 | 0.99 ❌ | ⚠️ 待修复CW |

> 表达式: `signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 10)`
> 通过检查: Sharpe、Fitness、Turnover、Prod Corr、Self Corr、Sub-Universe、2Y Sharpe、Pyramid

## 已确认的结论

### 有效策略
- **truncation=0.05** → 比SECTOR中性化更有效提升Sharpe
- **close/volume 加法组合** → 保留信号 (EPS/lowvol无效)
- **CROWDING中性化** → 可行，min_loan_rate达2.19
- **decay=2~8** → 小幅提升，最佳值因字段而异

### 无效策略
- `rank()`包裹 → Sharpe暴跌 (2.18→0.65)
- `ts_rank()` → Sharpe 0.58 (全灭)
- `signed_power×0.3` → 破坏信号 (2.18→0.89)
- `ts_min+vec_min` → 方向反了 (Sharpe负)
- EPS作为附加信号 → 始终<1.0
- 外层zscore → 零增益

## 数据集状态

### shortinterest3 — ⚠️ 不提交（自相关性太高）
- 26个Alpha Sharpe≥1.58，但**自相关性(Self Corr)过高**
- 决定：不提交shortinterest3衍生Alpha，换方向探索新数据集

### 数据集探索结果
| 数据集 | 测试数 | 最佳Sharpe | 状态 |
|--------|--------|------------|------|
| **shortinterest3** | 26个可提交 | **2.53** | ⚠️ 不提交（自相关性高） |
| **earnings27** | 2个 | 0.24 | ❌ DEAD |
| **ai_equity_alpha** | 8个 | 运行中 | ⏳ |

## 最佳Alpha Top 5
1. **qMgEkAbj** — Sharpe 2.53 (shortinterest3) — 不提交
2. **O0oJvZn1** — Sharpe 2.50 (shortinterest3) — 不提交
3. **VkOdOMLb** — Sharpe 2.49 (shortinterest3) — 不提交
4. **xAeGmO8m** — Sharpe 2.48 (shortinterest3) — 不提交
5. **e7L6w5NO** — Sharpe 2.47 (shortinterest3) — 不提交

## 下一步任务

1. **等待 ai_equity_alpha 结果** — 探索新的VECTOR数据集
2. **探索其他数据集** — analyst4/10/14, mdl136, pv48 等

## API状态

- TOP3000 Universe正常
- VECTOR字段需 vec_min/vec_max 包裹
- 429限流存在，模拟轮询需要轮询等待
