# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展
> 最后更新：2026-06-13 18:40

## 研究进度

- 当前阶段：API模拟引擎卡35%，提交功能正常但限流严格
- 最佳成绩：**Sharpe 2.53** - qMgEkAbj (未提交，CONCENTRATED_WEIGHT FAIL)
- **已确认提交成功** (HTTP 201): 11个Alpha

## 已确认提交成功的Alpha (11个)

| Alpha ID | Sharpe | 表达式 |
|----------|--------|--------|
| XgkA6oeX | 2.49 | ts_mean(zscore(-ts_max(vec_max(min_loan_rate), 22)), 22) |
| O0oJvZn1 | 2.50 | zscore(-ts_max(vec_max(min_loan_rate), 22)) + zscore(-ts_max(vec_max(min_loan_rate), 66)) |
| GrkeA5eZ | 2.44 | zscore(-ts_max(vec_max(mean_loan_rate), 22)) |
| xAeGmO8m | 2.48 | zscore(-ts_max(vec_max(min_loan_rate), 66)) |
| N1Aeja6q | 2.29 | zscore(-ts_max(vec_max(min_loan_rate), 22)) + zscore(-ts_max(vec_max(mean_loan_rate), 22)) |
| GrnE3oko | 2.34 | zscore(-ts_max(vec_max(mean_loan_rate), 22)) |
| blNzWNQR | 2.36 | zscore(-ts_max(vec_max(mean_loan_rate), 66)) |
| omVWk5am | 2.24 | zscore(-ts_max(vec_max(mean_loan_rate), 22) + -ts_max(vec_max(shrt3_bar), 22)) |
| 3qzpa3mX | 2.20 | zscore(-ts_max(vec_max(mean_loan_rate), 66)) |
| MPk0mNM8 | 2.18 | zscore(-ts_max(vec_max(min_loan_rate), 120)) |
| 0mAL5Mkk | 2.10 | zscore(-ts_max(vec_max(loan_rate_volatility), 22)) |
| O0oGpkkg | 2.07 | zscore(-ts_max(vec_max(mean_loan_rate), 66)) |
| YPQMRaPw | 1.60 | zscore(-ts_max(vec_max(mean_loan_rate), 22)) + zscore(-ts_max(vec_max(shrt3_bar), 22)) |

## 关键发现

### CONCENTRATED_WEIGHT是主要阻塞原因
- **window 5 导致CONCENTRATED_WEIGHT FAIL**：任何包含window 5的表达式都会失败
- **window 22+66 组合成功**：O0oJvZn1通过，但qMgEkAbj/VkOdOMLb失败（都是22+66，奇怪）

### API问题
- 模拟引擎：持续卡在35%，无法完成新模拟
- 429限流：连续提交后触发，需等待2-3分钟

### 成功模式
- **ts_mean smoothing**: `ts_mean(zscore(-ts_max(vec_max(field), window)), smoothing)` 可通过CONCENTRATED_WEIGHT
- **单窗口表达式**: `zscore(-ts_max(vec_max(field), 66))` 容易提交
- **多窗口组合**: `zscore(...22) + zscore(...66)` 分散权重

## 候选方向

1. **ts_mean smoothing variations** - 继续探索不同field和window组合
2. **cross-dataset组合** - mean_loan_rate + shrt3_bar 等
3. **等待模拟引擎恢复** - 当前无法进行新的回测

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
